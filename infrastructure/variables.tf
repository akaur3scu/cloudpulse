variable "project_name" {
  description = "Prefix used for CloudPulse resources."
  type        = string
  default     = "cloudpulse"
}

variable "aws_region" {
  description = "AWS region for the deployment."
  type        = string
  default     = "us-west-2"
}

variable "alert_email" {
  description = "Optional email address for outage and recovery alerts."
  type        = string
  default     = ""
  sensitive   = true
}

variable "check_schedule" {
  description = "EventBridge schedule expression."
  type        = string
  default     = "rate(5 minutes)"
}
