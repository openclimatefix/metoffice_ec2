terraform {
  backend "remote" {
    hostname = "app.terraform.io"
    organization = "openclimatefix"

    workspaces {
      name = "metoffice_ec2"
    }
  }
}


provider "aws" {
  version = "~> 2.0"
  region  = "eu-west-1"
}

# Additional provider configuration for London region
provider "aws" {
  alias   = "london"
  region  = "eu-west-2"
}

locals {
  common_tags = {
    Project     = "forecasting"
    Service     = "metoffice_ec2"
    Environment = "dev"
    Milestone   = "MS1"
    Owner       = "flo"
    Workload    = "research"
  }
}

resource "aws_sqs_queue" "metqueue" {
  name = "metoffice_ec2_receiver"
  message_retention_seconds = var.sqs_message_retention_seconds

  tags = local.common_tags
}

resource "aws_sns_topic_subscription" "queue_subscription_UKV" {
  provider  = aws.london
  topic_arn = "arn:aws:sns:eu-west-2:021908831235:aws-earth-mo-atmospheric-ukv-prd"
  protocol  = "sqs"
  endpoint  = aws_sqs_queue.metqueue.arn
  filter_policy = jsonencode(var.sns_filter_policy)
}

resource "aws_sns_topic_subscription" "queue_subscription_MOGREPS_UK" {
  provider  = aws.london
  topic_arn = "arn:aws:sns:eu-west-2:021908831235:aws-earth-mo-atmospheric-mogreps-uk-prd"
  protocol  = "sqs"
  endpoint  = aws_sqs_queue.metqueue.arn
  filter_policy = jsonencode(var.sns_filter_policy)
}

resource "aws_sqs_queue_policy" "ukv" {
  queue_url = aws_sqs_queue.metqueue.id

  policy = <<POLICY
{
  "Version": "2012-10-17",
  "Id": "sqspolicy",
  "Statement": [
    {
      "Sid": "met-ukv-allow",
      "Effect": "Allow",
      "Principal": "*",
      "Action": "sqs:SendMessage",
      "Resource": "${aws_sqs_queue.metqueue.arn}",
      "Condition": {
        "ArnEquals": {
          "aws:SourceArn": "${aws_sns_topic_subscription.queue_subscription_UKV.topic_arn}"
        }
      }
    },
    {
      "Sid": "met-mogreps-allow",
      "Effect": "Allow",
      "Principal": "*",
      "Action": "sqs:SendMessage",
      "Resource": "${aws_sqs_queue.metqueue.arn}",
      "Condition": {
        "ArnEquals": {
          "aws:SourceArn": "${aws_sns_topic_subscription.queue_subscription_MOGREPS_UK.topic_arn}"
        }
      }
    }
  ]
}
POLICY
}

resource "aws_s3_bucket" "output" {
  bucket = "ocf-uk-metoffice-nwp"

  lifecycle_rule {
    id      = "ia-after-one-week"
    enabled = true

    transition {
      days          = 30
      storage_class = "STANDARD_IA"
    }
  }

  tags = local.common_tags
}

resource "aws_s3_bucket" "forecasting_data" {
  bucket = "ocf-forecasting-data"

  tags = local.common_tags
}
