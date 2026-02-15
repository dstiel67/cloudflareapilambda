# Dead Letter Queue (DLQ) Infrastructure
# This file contains SQS queues for capturing failed Lambda invocations

# ============================================================================
# SQS Dead Letter Queues
# ============================================================================

# DLQ for Legacy Cloudflare Sync Lambda
resource "aws_sqs_queue" "lambda_dlq" {
  name                      = "${var.lambda_function_name}-dlq"
  message_retention_seconds = 1209600  # 14 days
  visibility_timeout_seconds = 300      # 5 minutes

  tags = {
    Name        = "${var.lambda_function_name}-dlq"
    Purpose     = "CloudflareDataSync-DLQ"
    Environment = "production"
  }
}

# DLQ for Update Lambda
resource "aws_sqs_queue" "update_lambda_dlq" {
  name                      = "${var.update_lambda_function_name}-dlq"
  message_retention_seconds = 1209600  # 14 days
  visibility_timeout_seconds = 30       # Match Lambda timeout

  tags = {
    Name        = "${var.update_lambda_function_name}-dlq"
    Purpose     = "RedirectStatusUpdate-DLQ"
    Environment = "production"
  }
}

# DLQ for Notification Lambda
resource "aws_sqs_queue" "notification_lambda_dlq" {
  name                      = "${var.notification_lambda_function_name}-dlq"
  message_retention_seconds = 1209600  # 14 days
  visibility_timeout_seconds = 60       # Match Lambda timeout

  tags = {
    Name        = "${var.notification_lambda_function_name}-dlq"
    Purpose     = "CloudflareNotification-DLQ"
    Environment = "production"
  }
}

# DLQ for SSE Endpoint Lambda
resource "aws_sqs_queue" "sse_lambda_dlq" {
  name                      = "${var.sse_lambda_function_name}-dlq"
  message_retention_seconds = 1209600  # 14 days
  visibility_timeout_seconds = 30       # Match Lambda timeout

  tags = {
    Name        = "${var.sse_lambda_function_name}-dlq"
    Purpose     = "CloudflareSSE-DLQ"
    Environment = "production"
  }
}

# ============================================================================
# IAM Permissions for Lambda to Send to DLQ
# ============================================================================

# IAM policy for Legacy Lambda to send to DLQ
resource "aws_iam_policy" "lambda_dlq_policy" {
  name        = "${var.lambda_function_name}-dlq-policy"
  description = "Allow Lambda to send messages to DLQ"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "sqs:SendMessage",
          "sqs:GetQueueAttributes"
        ]
        Resource = aws_sqs_queue.lambda_dlq.arn
      }
    ]
  })

  tags = {
    Name        = "${var.lambda_function_name}-dlq-policy"
    Purpose     = "CloudflareDataSync-DLQ"
    Environment = "production"
  }
}

# Attach DLQ policy to Legacy Lambda role
resource "aws_iam_role_policy_attachment" "lambda_dlq_policy_attachment" {
  role       = aws_iam_role.lambda_execution_role.name
  policy_arn = aws_iam_policy.lambda_dlq_policy.arn
}

# IAM policy for Update Lambda to send to DLQ
resource "aws_iam_policy" "update_lambda_dlq_policy" {
  name        = "${var.update_lambda_function_name}-dlq-policy"
  description = "Allow Update Lambda to send messages to DLQ"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "sqs:SendMessage",
          "sqs:GetQueueAttributes"
        ]
        Resource = aws_sqs_queue.update_lambda_dlq.arn
      }
    ]
  })

  tags = {
    Name        = "${var.update_lambda_function_name}-dlq-policy"
    Purpose     = "RedirectStatusUpdate-DLQ"
    Environment = "production"
  }
}

# Attach DLQ policy to Update Lambda role
resource "aws_iam_role_policy_attachment" "update_lambda_dlq_policy_attachment" {
  role       = aws_iam_role.update_lambda_role.name
  policy_arn = aws_iam_policy.update_lambda_dlq_policy.arn
}

# IAM policy for Notification Lambda to send to DLQ
resource "aws_iam_policy" "notification_lambda_dlq_policy" {
  name        = "${var.notification_lambda_function_name}-dlq-policy"
  description = "Allow Notification Lambda to send messages to DLQ"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "sqs:SendMessage",
          "sqs:GetQueueAttributes"
        ]
        Resource = aws_sqs_queue.notification_lambda_dlq.arn
      }
    ]
  })

  tags = {
    Name        = "${var.notification_lambda_function_name}-dlq-policy"
    Purpose     = "CloudflareNotification-DLQ"
    Environment = "production"
  }
}

# Attach DLQ policy to Notification Lambda role
resource "aws_iam_role_policy_attachment" "notification_lambda_dlq_policy_attachment" {
  role       = aws_iam_role.notification_lambda_role.name
  policy_arn = aws_iam_policy.notification_lambda_dlq_policy.arn
}

# IAM policy for SSE Lambda to send to DLQ
resource "aws_iam_policy" "sse_lambda_dlq_policy" {
  name        = "${var.sse_lambda_function_name}-dlq-policy"
  description = "Allow SSE Lambda to send messages to DLQ"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "sqs:SendMessage",
          "sqs:GetQueueAttributes"
        ]
        Resource = aws_sqs_queue.sse_lambda_dlq.arn
      }
    ]
  })

  tags = {
    Name        = "${var.sse_lambda_function_name}-dlq-policy"
    Purpose     = "CloudflareSSE-DLQ"
    Environment = "production"
  }
}

# Attach DLQ policy to SSE Lambda role
resource "aws_iam_role_policy_attachment" "sse_lambda_dlq_policy_attachment" {
  role       = aws_iam_role.sse_lambda_role.name
  policy_arn = aws_iam_policy.sse_lambda_dlq_policy.arn
}

# ============================================================================
# CloudWatch Alarms for DLQ Monitoring
# ============================================================================

# Alarm for messages in Legacy Lambda DLQ
resource "aws_cloudwatch_metric_alarm" "lambda_dlq_messages" {
  count               = var.alert_email != "" ? 1 : 0
  alarm_name          = "${var.lambda_function_name}-dlq-messages"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "1"
  metric_name         = "ApproximateNumberOfMessagesVisible"
  namespace           = "AWS/SQS"
  period              = "300"
  statistic           = "Average"
  threshold           = "0"
  alarm_description   = "Alert when messages appear in DLQ"
  alarm_actions       = [aws_sns_topic.lambda_alerts[0].arn]
  ok_actions          = [aws_sns_topic.lambda_alerts[0].arn]
  treat_missing_data  = "notBreaching"

  dimensions = {
    QueueName = aws_sqs_queue.lambda_dlq.name
  }

  tags = {
    Name        = "${var.lambda_function_name}-dlq-alarm"
    Purpose     = "CloudflareDataSync-DLQ"
    Environment = "production"
  }
}

# Alarm for messages in Update Lambda DLQ
resource "aws_cloudwatch_metric_alarm" "update_lambda_dlq_messages" {
  count               = var.alert_email != "" ? 1 : 0
  alarm_name          = "${var.update_lambda_function_name}-dlq-messages"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "1"
  metric_name         = "ApproximateNumberOfMessagesVisible"
  namespace           = "AWS/SQS"
  period              = "300"
  statistic           = "Average"
  threshold           = "0"
  alarm_description   = "Alert when messages appear in Update Lambda DLQ"
  alarm_actions       = [aws_sns_topic.lambda_alerts[0].arn]
  ok_actions          = [aws_sns_topic.lambda_alerts[0].arn]
  treat_missing_data  = "notBreaching"

  dimensions = {
    QueueName = aws_sqs_queue.update_lambda_dlq.name
  }

  tags = {
    Name        = "${var.update_lambda_function_name}-dlq-alarm"
    Purpose     = "RedirectStatusUpdate-DLQ"
    Environment = "production"
  }
}

# Alarm for messages in Notification Lambda DLQ
resource "aws_cloudwatch_metric_alarm" "notification_lambda_dlq_messages" {
  count               = var.alert_email != "" ? 1 : 0
  alarm_name          = "${var.notification_lambda_function_name}-dlq-messages"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "1"
  metric_name         = "ApproximateNumberOfMessagesVisible"
  namespace           = "AWS/SQS"
  period              = "300"
  statistic           = "Average"
  threshold           = "0"
  alarm_description   = "Alert when messages appear in Notification Lambda DLQ"
  alarm_actions       = [aws_sns_topic.lambda_alerts[0].arn]
  ok_actions          = [aws_sns_topic.lambda_alerts[0].arn]
  treat_missing_data  = "notBreaching"

  dimensions = {
    QueueName = aws_sqs_queue.notification_lambda_dlq.name
  }

  tags = {
    Name        = "${var.notification_lambda_function_name}-dlq-alarm"
    Purpose     = "CloudflareNotification-DLQ"
    Environment = "production"
  }
}

# Alarm for messages in SSE Lambda DLQ
resource "aws_cloudwatch_metric_alarm" "sse_lambda_dlq_messages" {
  count               = var.alert_email != "" ? 1 : 0
  alarm_name          = "${var.sse_lambda_function_name}-dlq-messages"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "1"
  metric_name         = "ApproximateNumberOfMessagesVisible"
  namespace           = "AWS/SQS"
  period              = "300"
  statistic           = "Average"
  threshold           = "0"
  alarm_description   = "Alert when messages appear in SSE Lambda DLQ"
  alarm_actions       = [aws_sns_topic.lambda_alerts[0].arn]
  ok_actions          = [aws_sns_topic.lambda_alerts[0].arn]
  treat_missing_data  = "notBreaching"

  dimensions = {
    QueueName = aws_sqs_queue.sse_lambda_dlq.name
  }

  tags = {
    Name        = "${var.sse_lambda_function_name}-dlq-alarm"
    Purpose     = "CloudflareSSE-DLQ"
    Environment = "production"
  }
}
