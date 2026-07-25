from backend.monitor import check_endpoint


def test_online_endpoint():
    result = check_endpoint("https://example.com")

    assert result["status"] == "online"
    assert result["status_code"] == 200
    assert result["response_time_ms"] is not None


def test_invalid_endpoint():
    result = check_endpoint("https://this-domain-should-not-exist.invalid")

    assert result["status"] == "offline"
    assert result["status_code"] is None
    assert result["response_time_ms"] is None