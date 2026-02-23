# AWS MSK (Managed Streaming for Apache Kafka) Configuration
# This file creates a fully managed Kafka cluster for failover event streaming

# Variables for MSK configuration
variable "msk_cluster_name" {
  description = "Name of the MSK cluster"
  type        = string
  default     = "failover-events-cluster"
}

variable "msk_kafka_version" {
  description = "Kafka version for MSK cluster"
  type        = string
  default     = "3.5.1"
}

variable "msk_instance_type" {
  description = "Instance type for MSK brokers"
  type        = string
  default     = "kafka.t3.small"  # Smallest instance for dev/test
}

variable "msk_number_of_broker_nodes" {
  description = "Number of broker nodes (must be multiple of availability zones)"
  type        = number
  default     = 2  # Minimum for production
}

variable "msk_ebs_volume_size" {
  description = "EBS volume size per broker in GB"
  type        = number
  default     = 100
}

variable "create_msk_cluster" {
  description = "Whether to create MSK cluster (set to false to skip MSK creation)"
  type        = bool
  default     = true
}

# Data source for availability zones
data "aws_availability_zones" "available" {
  state = "available"
}

# VPC for MSK cluster
resource "aws_vpc" "msk_vpc" {
  count = var.create_msk_cluster ? 1 : 0

  cidr_block           = "10.0.0.0/16"
  enable_dns_hostnames = true
  enable_dns_support   = true

  tags = {
    Name        = "${var.msk_cluster_name}-vpc"
    Purpose     = "MSK-Kafka"
    Environment = "production"
    ManagedBy   = "terraform"
  }
}

# Internet Gateway for VPC
resource "aws_internet_gateway" "msk_igw" {
  count = var.create_msk_cluster ? 1 : 0

  vpc_id = aws_vpc.msk_vpc[0].id

  tags = {
    Name        = "${var.msk_cluster_name}-igw"
    Purpose     = "MSK-Kafka"
    Environment = "production"
    ManagedBy   = "terraform"
  }
}

# Private subnets for MSK brokers (one per AZ)
resource "aws_subnet" "msk_private_subnet" {
  count = var.create_msk_cluster ? var.msk_number_of_broker_nodes : 0

  vpc_id            = aws_vpc.msk_vpc[0].id
  cidr_block        = "10.0.${count.index + 1}.0/24"
  availability_zone = data.aws_availability_zones.available.names[count.index]

  tags = {
    Name        = "${var.msk_cluster_name}-private-subnet-${count.index + 1}"
    Purpose     = "MSK-Kafka"
    Environment = "production"
    ManagedBy   = "terraform"
  }
}

# Route table for private subnets
resource "aws_route_table" "msk_private_rt" {
  count = var.create_msk_cluster ? 1 : 0

  vpc_id = aws_vpc.msk_vpc[0].id

  tags = {
    Name        = "${var.msk_cluster_name}-private-rt"
    Purpose     = "MSK-Kafka"
    Environment = "production"
    ManagedBy   = "terraform"
  }
}

# Associate route table with private subnets
resource "aws_route_table_association" "msk_private_rta" {
  count = var.create_msk_cluster ? var.msk_number_of_broker_nodes : 0

  subnet_id      = aws_subnet.msk_private_subnet[count.index].id
  route_table_id = aws_route_table.msk_private_rt[0].id
}

# Security group for MSK cluster
resource "aws_security_group" "msk_sg" {
  count = var.create_msk_cluster ? 1 : 0

  name        = "${var.msk_cluster_name}-sg"
  description = "Security group for MSK cluster"
  vpc_id      = aws_vpc.msk_vpc[0].id

  # Allow inbound Kafka traffic from Lambda
  ingress {
    description = "Kafka plaintext"
    from_port   = 9092
    to_port     = 9092
    protocol    = "tcp"
    cidr_blocks = ["10.0.0.0/16"]
  }

  ingress {
    description = "Kafka TLS"
    from_port   = 9094
    to_port     = 9094
    protocol    = "tcp"
    cidr_blocks = ["10.0.0.0/16"]
  }

  ingress {
    description = "Zookeeper"
    from_port   = 2181
    to_port     = 2181
    protocol    = "tcp"
    cidr_blocks = ["10.0.0.0/16"]
  }

  # Allow all outbound traffic
  egress {
    description = "Allow all outbound"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name        = "${var.msk_cluster_name}-sg"
    Purpose     = "MSK-Kafka"
    Environment = "production"
    ManagedBy   = "terraform"
  }
}

# CloudWatch Log Group for MSK
resource "aws_cloudwatch_log_group" "msk_logs" {
  count = var.create_msk_cluster ? 1 : 0

  name              = "/aws/msk/${var.msk_cluster_name}"
  retention_in_days = 14

  tags = {
    Name        = "${var.msk_cluster_name}-logs"
    Purpose     = "MSK-Kafka"
    Environment = "production"
    ManagedBy   = "terraform"
  }
}

# MSK Configuration
resource "aws_msk_configuration" "msk_config" {
  count = var.create_msk_cluster ? 1 : 0

  name              = "${var.msk_cluster_name}-config"
  kafka_versions    = [var.msk_kafka_version]
  server_properties = <<PROPERTIES
auto.create.topics.enable=true
default.replication.factor=2
min.insync.replicas=1
num.io.threads=8
num.network.threads=5
num.partitions=3
num.replica.fetchers=2
replica.lag.time.max.ms=30000
socket.receive.buffer.bytes=102400
socket.request.max.bytes=104857600
socket.send.buffer.bytes=102400
unclean.leader.election.enable=true
zookeeper.session.timeout.ms=18000
log.retention.hours=168
log.retention.bytes=1073741824
PROPERTIES

  description = "Configuration for ${var.msk_cluster_name}"
}

# MSK Cluster
resource "aws_msk_cluster" "kafka_cluster" {
  count = var.create_msk_cluster ? 1 : 0

  cluster_name           = var.msk_cluster_name
  kafka_version          = var.msk_kafka_version
  number_of_broker_nodes = var.msk_number_of_broker_nodes

  broker_node_group_info {
    instance_type   = var.msk_instance_type
    client_subnets  = aws_subnet.msk_private_subnet[*].id
    security_groups = [aws_security_group.msk_sg[0].id]

    storage_info {
      ebs_storage_info {
        volume_size = var.msk_ebs_volume_size
      }
    }

    connectivity_info {
      public_access {
        type = "DISABLED"
      }
    }
  }

  configuration_info {
    arn      = aws_msk_configuration.msk_config[0].arn
    revision = aws_msk_configuration.msk_config[0].latest_revision
  }

  encryption_info {
    encryption_in_transit {
      client_broker = "TLS_PLAINTEXT"
      in_cluster    = true
    }

    encryption_at_rest_kms_key_arn = aws_kms_key.msk_kms[0].arn
  }

  logging_info {
    broker_logs {
      cloudwatch_logs {
        enabled   = true
        log_group = aws_cloudwatch_log_group.msk_logs[0].name
      }
    }
  }

  tags = {
    Name        = var.msk_cluster_name
    Purpose     = "FailoverEventStreaming"
    Environment = "production"
    ManagedBy   = "terraform"
  }
}

# KMS key for MSK encryption
resource "aws_kms_key" "msk_kms" {
  count = var.create_msk_cluster ? 1 : 0

  description             = "KMS key for MSK cluster encryption"
  deletion_window_in_days = 10
  enable_key_rotation     = true

  tags = {
    Name        = "${var.msk_cluster_name}-kms"
    Purpose     = "MSK-Kafka"
    Environment = "production"
    ManagedBy   = "terraform"
  }
}

# KMS key alias
resource "aws_kms_alias" "msk_kms_alias" {
  count = var.create_msk_cluster ? 1 : 0

  name          = "alias/${var.msk_cluster_name}"
  target_key_id = aws_kms_key.msk_kms[0].key_id
}

# IAM policy for Lambda to access MSK
resource "aws_iam_policy" "lambda_msk_policy" {
  count = var.create_msk_cluster ? 1 : 0

  name        = "${var.lambda_function_name}-msk-access"
  description = "IAM policy for Lambda to access MSK cluster"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "kafka:DescribeCluster",
          "kafka:DescribeClusterV2",
          "kafka:GetBootstrapBrokers"
        ]
        Resource = aws_msk_cluster.kafka_cluster[0].arn
      },
      {
        Effect = "Allow"
        Action = [
          "ec2:CreateNetworkInterface",
          "ec2:DescribeNetworkInterfaces",
          "ec2:DescribeVpcs",
          "ec2:DeleteNetworkInterface",
          "ec2:DescribeSubnets",
          "ec2:DescribeSecurityGroups"
        ]
        Resource = "*"
      },
      {
        Effect = "Allow"
        Action = [
          "kafka-cluster:Connect",
          "kafka-cluster:AlterCluster",
          "kafka-cluster:DescribeCluster"
        ]
        Resource = aws_msk_cluster.kafka_cluster[0].arn
      },
      {
        Effect = "Allow"
        Action = [
          "kafka-cluster:*Topic*",
          "kafka-cluster:WriteData",
          "kafka-cluster:ReadData"
        ]
        Resource = "arn:aws:kafka:${var.aws_region}:${data.aws_caller_identity.current.account_id}:topic/${var.msk_cluster_name}/*"
      },
      {
        Effect = "Allow"
        Action = [
          "kafka-cluster:AlterGroup",
          "kafka-cluster:DescribeGroup"
        ]
        Resource = "arn:aws:kafka:${var.aws_region}:${data.aws_caller_identity.current.account_id}:group/${var.msk_cluster_name}/*"
      }
    ]
  })

  tags = {
    Name        = "${var.lambda_function_name}-msk-access"
    Purpose     = "MSK-Kafka"
    Environment = "production"
    ManagedBy   = "terraform"
  }
}

# Attach MSK policy to Lambda role
resource "aws_iam_role_policy_attachment" "lambda_msk_policy_attachment" {
  count = var.create_msk_cluster ? 1 : 0

  role       = aws_iam_role.kafka_consumer_role.name
  policy_arn = aws_iam_policy.lambda_msk_policy[0].arn
}

# Lambda Event Source Mapping for MSK
resource "aws_lambda_event_source_mapping" "kafka_trigger" {
  count = var.create_msk_cluster ? 1 : 0

  event_source_arn  = aws_msk_cluster.kafka_cluster[0].arn
  function_name     = aws_lambda_function.kafka_consumer.arn
  topics            = ["failover-events"]
  starting_position = "LATEST"

  # Batch configuration
  batch_size                         = 100
  maximum_batching_window_in_seconds = 5

  # Error handling
  function_response_types = ["ReportBatchItemFailures"]

  depends_on = [
    aws_iam_role_policy_attachment.lambda_msk_policy_attachment
  ]
}

# Data source for current AWS account
data "aws_caller_identity" "current" {}

# Outputs
output "msk_cluster_arn" {
  description = "ARN of the MSK cluster"
  value       = var.create_msk_cluster ? aws_msk_cluster.kafka_cluster[0].arn : "MSK cluster not created"
}

output "msk_bootstrap_brokers" {
  description = "Bootstrap brokers for the MSK cluster"
  value       = var.create_msk_cluster ? aws_msk_cluster.kafka_cluster[0].bootstrap_brokers : "MSK cluster not created"
}

output "msk_bootstrap_brokers_tls" {
  description = "TLS bootstrap brokers for the MSK cluster"
  value       = var.create_msk_cluster ? aws_msk_cluster.kafka_cluster[0].bootstrap_brokers_tls : "MSK cluster not created"
}

output "msk_zookeeper_connect_string" {
  description = "Zookeeper connection string"
  value       = var.create_msk_cluster ? aws_msk_cluster.kafka_cluster[0].zookeeper_connect_string : "MSK cluster not created"
}

output "msk_vpc_id" {
  description = "VPC ID for MSK cluster"
  value       = var.create_msk_cluster ? aws_vpc.msk_vpc[0].id : "MSK cluster not created"
}

output "msk_security_group_id" {
  description = "Security group ID for MSK cluster"
  value       = var.create_msk_cluster ? aws_security_group.msk_sg[0].id : "MSK cluster not created"
}

output "kafka_topic_name" {
  description = "Kafka topic name for failover events"
  value       = "failover-events"
}

output "msk_cluster_name" {
  description = "Name of the MSK cluster"
  value       = var.msk_cluster_name
}
