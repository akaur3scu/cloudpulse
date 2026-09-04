"""AWS Lambda API and scheduled checker for CloudPulse."""

from __future__ import annotations

import json
import os
import time
import uuid
from decimal import Decimal

import boto3
from boto3.dynamodb.conditions import Key
from botocore.exceptions import ClientError

from monitor import check_endpoint, utc_now, validate_url

ENDPOINTS_TABLE = os.environ["ENDPOINTS_TABLE"]
CHECKS_TABLE = os.environ["CHECKS_TABLE"]
SNS_TOPIC_ARN = os.environ.get("SNS_TOPIC_ARN", "")
HISTORY_DAYS = int(os.environ.get("HISTORY_DAYS", "30"))

dynamodb = boto3.resource("dynamodb")
endpoints_table = dynamodb.Table(ENDPOINTS_TABLE)
checks_table = dynamodb.Table(CHECKS_TABLE)
sns = boto3.client("sns")


def json_default(value):
    if isinstance(value, Decimal):
        return float(value)
    raise TypeError(f"Cannot serialize {type(value)}")


def api_response(status_code: int, payload: dict) -> dict:
    return {
        "statusCode": status_code,
        "headers": {"content-type": "application/json", "cache-control": "no-store"},
        "body": json.dumps(payload, default=json_default),
    }


def all_endpoints() -> list[dict]:
    items = []
    response = endpoints_table.scan()
    items.extend(response.get("Items", []))
    while response.get("LastEvaluatedKey"):
        response = endpoints_table.scan(ExclusiveStartKey=response["LastEvaluatedKey"])
        items.extend(response.get("Items", []))
    return sorted(items, key=lambda item: item["created_at"])


def history(endpoint_id: str, limit: int = 20) -> list[dict]:
    response = checks_table.query(
        KeyConditionExpression=Key("endpoint_id").eq(endpoint_id),
        ScanIndexForward=False,
        Limit=limit,
    )
    return list(reversed(response.get("Items", [])))


def services_payload() -> list[dict]:
    services = all_endpoints()
    for service in services:
        service["history"] = history(service["id"])
    return services


def create_endpoint(payload: dict) -> dict:
    name = str(payload.get("name", "")).strip()
    if not name or len(name) > 80:
        raise ValueError("Service name must be between 1 and 80 characters.")
    if len(all_endpoints()) >= 20:
        raise ValueError("CloudPulse supports up to 20 monitors in this demo.")
    url = validate_url(str(payload.get("url", "")).strip())

    existing = endpoints_table.scan(
        FilterExpression="#url = :url",
        ExpressionAttributeNames={"#url": "url"},
        ExpressionAttributeValues={":url": url},
    ).get("Items", [])
    if existing:
        raise FileExistsError("That URL is already being monitored.")

    endpoint = {"id": str(uuid.uuid4()), "name": name, "url": url, "created_at": utc_now()}
    endpoints_table.put_item(Item=endpoint, ConditionExpression="attribute_not_exists(id)")
    store_check(endpoint, check_endpoint(url))
    endpoint["history"] = history(endpoint["id"])
    return endpoint


def store_check(endpoint: dict, result: dict) -> None:
    prior = history(endpoint["id"], limit=2)
    item = {
        "endpoint_id": endpoint["id"],
        "checked_at": result["checked_at"],
        "status": result["status"],
        "status_code": result.get("status_code"),
        "response_time_ms": (
            Decimal(str(result["response_time_ms"]))
            if result.get("response_time_ms") is not None
            else None
        ),
        "error": result.get("error"),
        "expires_at": int(time.time()) + HISTORY_DAYS * 86400,
    }
    checks_table.put_item(Item={key: value for key, value in item.items() if value is not None})

    if not SNS_TOPIC_ARN or not prior:
        return
    previous = prior[-1]["status"]
    before_previous = prior[-2]["status"] if len(prior) > 1 else None
    if result["status"] == "offline" and previous == "offline" and before_previous != "offline":
        publish_alert(endpoint, "DOWN", f"Two consecutive checks failed. {result.get('error', '')}")
    elif result["status"] == "online" and previous == "offline":
        publish_alert(endpoint, "RECOVERED", "The endpoint is responding again.")


def publish_alert(endpoint: dict, state: str, detail: str) -> None:
    sns.publish(
        TopicArn=SNS_TOPIC_ARN,
        Subject=f"CloudPulse: {endpoint['name']} {state}",
        Message=f"{endpoint['name']} ({endpoint['url']}) is {state}.\n\n{detail}",
    )


def run_all_checks() -> list[dict]:
    for endpoint in all_endpoints():
        store_check(endpoint, check_endpoint(endpoint["url"]))
    return services_payload()


def delete_endpoint(endpoint_id: str) -> bool:
    if "Item" not in endpoints_table.get_item(Key={"id": endpoint_id}):
        return False
    with checks_table.batch_writer() as batch:
        for item in history(endpoint_id, limit=1000):
            batch.delete_item(Key={"endpoint_id": endpoint_id, "checked_at": item["checked_at"]})
    endpoints_table.delete_item(Key={"id": endpoint_id})
    return True


def parse_body(event: dict) -> dict:
    try:
        return json.loads(event.get("body") or "{}")
    except json.JSONDecodeError as error:
        raise ValueError("Request body must be valid JSON.") from error


def lambda_handler(event, _context):
    if "requestContext" not in event:
        return {"checked": len(run_all_checks())}

    method = event["requestContext"]["http"]["method"]
    path = event.get("rawPath", "/")
    try:
        if method == "GET" and path == "/api/health":
            return api_response(200, {"status": "ok"})
        if method == "GET" and path == "/api/endpoints":
            return api_response(200, {"services": services_payload()})
        if method == "POST" and path == "/api/endpoints":
            return api_response(201, {"service": create_endpoint(parse_body(event))})
        if method == "POST" and path == "/api/checks/run":
            return api_response(200, {"services": run_all_checks()})
        if method == "DELETE" and path.startswith("/api/endpoints/"):
            endpoint_id = path.removeprefix("/api/endpoints/")
            if delete_endpoint(endpoint_id):
                return api_response(200, {"deleted": endpoint_id})
            return api_response(404, {"error": "Monitor not found."})
        return api_response(404, {"error": "Not found."})
    except FileExistsError as error:
        return api_response(409, {"error": str(error)})
    except ValueError as error:
        return api_response(400, {"error": str(error)})
    except ClientError:
        return api_response(500, {"error": "The AWS service could not complete the request."})
