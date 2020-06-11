# IAM
# Optional IAM role that tasks can use to make API requests to authorized AWS services.
resource "aws_iam_role" "metoffice_task_role" {
  name = "metoffice_ec2_task_role"

  assume_role_policy = <<POLICY
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Action": "sts:AssumeRole",
      "Principal": {
        "Service": "ecs-tasks.amazonaws.com"
      },
      "Effect": "Allow",
      "Sid": ""
    }
  ]
}
POLICY

    tags = local.common_tags
}

resource "aws_iam_policy" "metoffice_task_policy" {
  name = "metoffice_ec2_task_role_policy"
  description = "Allows access to SQS and S3"

  policy = <<POLICY
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "sqs",
            "Effect": "Allow",
            "Action": [
                "sqs:DeleteMessage",
                "sqs:GetQueueUrl",
                "sqs:ReceiveMessage",
                "sqs:GetQueueAttributes",
                "sqs:ListQueueTags",
                "sqs:ListDeadLetterSourceQueues",
                "sqs:DeleteMessageBatch"
            ],
            "Resource": [
              "${aws_sqs_queue.metqueue.arn}"
            ]
        },
        {
            "Sid": "s3bucket",
            "Effect": "Allow",
            "Action": [
                "s3:ListBucket"
            ],
            "Resource": [
                "${aws_s3_bucket.output.arn}"
            ]
        },
        {
            "Sid": "s3files",
            "Effect": "Allow",
            "Action": [
                "s3:PutObject",
                "s3:GetObject"
            ],
            "Resource": [
                "${aws_s3_bucket.output.arn}/*"
            ]
        }
    ]
}
POLICY
}

resource "aws_iam_role_policy_attachment" "metoffice_task_role_policy_attachment" {
  role = aws_iam_role.metoffice_task_role.name
  policy_arn = aws_iam_policy.metoffice_task_policy.arn
}

resource "aws_iam_policy" "metoffice_task_policy_read_metoffice" {
  name = "metoffice_ec2_task_role_policy_read_metoffice"
  description = "Allows read access to external MetOffice S3 bucket"

  policy = <<POLICY
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "ListObjectsInBucket",
            "Effect": "Allow",
            "Action": ["s3:ListBucket"],
            "Resource": [
              "arn:aws:s3:::aws-earth-mo-atmospheric-ukv-prd",
              "arn:aws:s3:::aws-earth-mo-atmospheric-mogreps-uk-prd"
            ]
        },
        {
            "Sid": "AllObjectActions",
            "Effect": "Allow",
            "Action": "s3:*Object",
            "Resource": [
              "arn:aws:s3:::aws-earth-mo-atmospheric-ukv-prd/*",
              "arn:aws:s3:::aws-earth-mo-atmospheric-mogreps-uk-prd/*"
            ]
        }
    ]
}
POLICY
}

resource "aws_iam_role_policy_attachment" "metoffice_task_role_policy_attachment_2" {
  role = aws_iam_role.metoffice_task_role.name
  policy_arn = aws_iam_policy.metoffice_task_policy_read_metoffice.arn
}

# Execution role, required by tasks to pull container images and publish container logs to Amazon CloudWatch
resource "aws_iam_role" "metoffice_execution_role" {
  name = "metoffice_ec2_execution_role"
  
  assume_role_policy = <<POLICY
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Action": "sts:AssumeRole",
      "Principal": {
        "Service": "ecs-tasks.amazonaws.com"
      },
      "Effect": "Allow",
      "Sid": ""
    }
  ]
}
POLICY
}

resource "aws_iam_role_policy_attachment" "metoffice_execution_role_policy_attachment" {
  role = aws_iam_role.metoffice_execution_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}


# 1. Task Definition
resource "aws_ecs_task_definition" "metoffice_task" {
  family = "metoffice_ec2"
  container_definitions = <<JSON
[{
    "name": "main",
    "image": "openclimatefix/metoffice_ec2:${var.docker_image_version}",
    "essential": true,
    "logConfiguration": {
      "logDriver": "awslogs",
      "options": {
        "awslogs-group": "metoffice_ec2",
        "awslogs-region": "eu-west-1",
        "awslogs-stream-prefix": "main"
      }
    },
    "environment": [{
        "name": "DEST_BUCKET",
        "value": "${aws_s3_bucket.output.bucket}"
      },
      {
        "name": "SQS_URL",
        "value": "${aws_sqs_queue.metqueue.id}"
      }
    ]
}]
JSON
  requires_compatibilities = ["FARGATE"]
  network_mode = "awsvpc"
  task_role_arn = aws_iam_role.metoffice_task_role.arn
  execution_role_arn = aws_iam_role.metoffice_execution_role.arn

  cpu = var.ecs_vcpu
  memory = var.ecs_memory
  
  tags = local.common_tags
}

# 2. Cluster
resource "aws_ecs_cluster" "metoffice_ec2" {
  name = "metoffice_ec2_cluster"
  capacity_providers = ["FARGATE", "FARGATE_SPOT"]

  default_capacity_provider_strategy {
    capacity_provider = "FARGATE_SPOT"
  }
  
  tags = local.common_tags
}

# 3. Service
resource "aws_ecs_service" "metoffice_service" {
  name            = "metoffice_ec2_service"
  cluster         = aws_ecs_cluster.metoffice_ec2.id
  task_definition = aws_ecs_task_definition.metoffice_task.arn
  launch_type = "FARGATE"
  propagate_tags = "TASK_DEFINITION"
  
  desired_count   = var.ecs_desired_count

  network_configuration {
      subnets = [aws_subnet.main.id]
      security_groups = [aws_security_group.main.id]
      assign_public_ip = true
  }

  tags = local.common_tags
}

# =================================================================================
# VPC Shenanigans
# =================================================================================
# VPC
resource "aws_vpc" "main" {
  cidr_block = "10.0.0.0/16"

  tags = merge(map( 
            "Name", "metoffice_ec2_vpc", 
        ), local.common_tags)
}

# Subnet
resource "aws_subnet" "main" {
  # PUBLIC
  vpc_id     = aws_vpc.main.id
  cidr_block = "10.0.0.0/24"

  tags = merge(map( 
            "Name", "metoffice_ec2_subnet", 
        ), local.common_tags)
}

# Security Group
resource "aws_security_group" "main" {
  name        = "metoffice_ec2_security_group"
  description = "ECS Allowed Ports"
  vpc_id      = aws_vpc.main.id

  ingress {
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = local.common_tags
}

# Route Table
resource "aws_route_table" "r" {
  vpc_id = aws_vpc.main.id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.gw.id
  }

  tags = merge(map( 
            "Name", "metoffice_ec2_route_table", 
        ), local.common_tags)
}

resource "aws_route_table_association" "a" {
  subnet_id      = aws_subnet.main.id
  route_table_id = aws_route_table.r.id
}

# IGW
resource "aws_internet_gateway" "gw" {
  vpc_id = aws_vpc.main.id

  tags = merge(map( 
            "Name", "metoffice_ec2_igw",
        ), local.common_tags)
}

# Autoscaling
resource "aws_appautoscaling_target" "ecs_target" {
  max_capacity       = 5
  min_capacity       = 0
  resource_id        = "service/${aws_ecs_cluster.metoffice_ec2.name}/${aws_ecs_service.metoffice_service.name}"
  scalable_dimension = "ecs:service:DesiredCount"
  service_namespace  = "ecs"
}

resource "aws_appautoscaling_policy" "ecs_policy" {
  name               = "metoffice_ec2_scale-ecs"
  policy_type        = "StepScaling"
  resource_id        = aws_appautoscaling_target.ecs_target.resource_id
  scalable_dimension = aws_appautoscaling_target.ecs_target.scalable_dimension
  service_namespace  = aws_appautoscaling_target.ecs_target.service_namespace

  step_scaling_policy_configuration {
    adjustment_type         = "ExactCapacity"
    cooldown                = 60
    metric_aggregation_type = "Average"

    # Assuming alarm threshold of 1000
    step_adjustment {
      metric_interval_lower_bound = 0
      metric_interval_upper_bound = 999
      scaling_adjustment          = 1
    }

    step_adjustment {
      metric_interval_lower_bound = 1000
      metric_interval_upper_bound = 1999
      scaling_adjustment          = 2
    }

    step_adjustment {
      metric_interval_lower_bound = 2000
      metric_interval_upper_bound = 2999
      scaling_adjustment          = 3
    }

    step_adjustment {
      metric_interval_lower_bound = 3000
      scaling_adjustment          = 5
    }
  }
}

resource "aws_cloudwatch_metric_alarm" "ecs_metric_alarm" {
  alarm_name          = "metoffice_ec2_sqs_average_msg_age"
  comparison_operator = "GreaterThanOrEqualToThreshold"
  evaluation_periods  = "2"
  metric_name         = "ApproximateAgeOfOldestMessage"
  namespace           = "AWS/SQS"
  period              = "120"
  statistic           = "Average"
  threshold           = "1000"

  dimensions = {
    QueueName = aws_sqs_queue.metqueue.name
  }

  alarm_description = "This metric monitors SQS message age"
  alarm_actions     = ["${aws_appautoscaling_policy.ecs_policy.arn}"]
  tags              = local.common_tags
}
