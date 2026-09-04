output "cloudpulse_url" {
  description = "Public CloudPulse dashboard URL."
  value       = "https://${aws_cloudfront_distribution.app.domain_name}"
}

output "api_url" {
  description = "Direct API Gateway URL for diagnostics."
  value       = aws_apigatewayv2_api.api.api_endpoint
}

output "cloudfront_distribution_id" {
  description = "Distribution ID used for cache invalidations."
  value       = aws_cloudfront_distribution.app.id
}

output "sns_topic_arn" {
  description = "SNS topic used for alerts."
  value       = aws_sns_topic.alerts.arn
}
