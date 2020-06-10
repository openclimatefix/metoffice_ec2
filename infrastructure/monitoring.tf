resource "aws_cloudwatch_log_group" "main" {
  name = "metoffice_ec2"
  retention_in_days = 5

  tags = local.common_tags
}


resource "aws_cloudwatch_dashboard" "dash" {
  dashboard_name = "metoffice_ec2_dashboard"

  dashboard_body = <<EOF
{
    "widgets": [
        {
            "type": "metric",
            "x": 0,
            "y": 1,
            "width": 6,
            "height": 6,
            "properties": {
                "metrics": [
                    [ "AWS/SQS", "NumberOfMessagesReceived", "QueueName", "metoffice_ec2_receiver", { "label": "# Messages Received" } ],
                    [ ".", "NumberOfMessagesDeleted", ".", ".", { "label": "# Messages Deleted" } ]
                ],
                "view": "timeSeries",
                "stacked": false,
                "region": "eu-west-1",
                "stat": "Sum",
                "period": 300
            }
        },
        {
            "type": "metric",
            "x": 6,
            "y": 1,
            "width": 6,
            "height": 6,
            "properties": {
                "metrics": [
                    [ "AWS/SQS", "ApproximateAgeOfOldestMessage", "QueueName", "metoffice_ec2_receiver", { "label": "Age of oldest Message in sec" } ]
                ],
                "view": "timeSeries",
                "stacked": false,
                "region": "eu-west-1",
                "annotations": {
                    "horizontal": [
                        {
                            "label": "Message Retention Deadline",
                            "value": ${var.sqs_message_retention_seconds}
                        }
                    ]
                },
                "title": "Age of Messages",
                "stat": "Average",
                "period": 300,
                "yAxis": {
                    "left": {
                        "min": 0
                    }
                }
            }
        },
        {
            "type": "metric",
            "x": 12,
            "y": 1,
            "width": 6,
            "height": 6,
            "properties": {
                "metrics": [
                    [ "AWS/SQS", "NumberOfEmptyReceives", "QueueName", "metoffice_ec2_receiver" ]
                ],
                "view": "timeSeries",
                "stacked": false,
                "region": "eu-west-1",
                "stat": "Sum",
                "period": 300,
                "title": "Empty Receives"
            }
        },
        {
            "type": "metric",
            "x": 0,
            "y": 8,
            "width": 6,
            "height": 6,
            "properties": {
                "metrics": [
                    [ "ECS/ContainerInsights", "CpuUtilized", "ServiceName", "metoffice_ec2_service", "ClusterName", "metoffice_ec2_cluster" ]
                ],
                "view": "timeSeries",
                "stacked": false,
                "region": "eu-west-1",
                "stat": "Average",
                "period": 300,
                "annotations": {
                    "horizontal": [
                        {
                            "label": "Hard Limit",
                            "value": ${var.ecs_vcpu}
                        }
                    ]
                },
                "title": "ECS CPU",
                "yAxis": {
                    "left": {
                        "min": 0
                    }
                }
            }
        },
        {
            "type": "metric",
            "x": 6,
            "y": 8,
            "width": 6,
            "height": 6,
            "properties": {
                "view": "timeSeries",
                "stacked": false,
                "metrics": [
                    [ "ECS/ContainerInsights", "MemoryUtilized", "ServiceName", "metoffice_ec2_service", "ClusterName", "metoffice_ec2_cluster" ]
                ],
                "region": "eu-west-1",
                "annotations": {
                    "horizontal": [
                        {
                            "label": "Hard Limit",
                            "value": ${var.ecs_memory}
                        }
                    ]
                },
                "title": "ECS Memory",
                "yAxis": {
                    "left": {
                        "min": 0
                    }
                }
            }
        },
        {
            "type": "text",
            "x": 0,
            "y": 0,
            "width": 18,
            "height": 1,
            "properties": {
                "markdown": "\n# SQS (metoffice-receiver)\n"
            }
        },
        {
            "type": "text",
            "x": 0,
            "y": 7,
            "width": 18,
            "height": 1,
            "properties": {
                "markdown": "\n# ECS\n"
            }
        },
        {
            "type": "metric",
            "x": 18,
            "y": 7,
            "width": 6,
            "height": 6,
            "properties": {
                "metrics": [
                    [ "AWS/S3", "BucketSizeBytes", "StorageType", "StandardStorage", "BucketName", "ocf-uk-metoffice-nwp", { "label": "Bucket Size" } ]
                ],
                "view": "timeSeries",
                "stacked": false,
                "region": "eu-west-1",
                "stat": "Sum",
                "period": 86400,
                "title": "Bucket Size"
            }
        },
        {
            "type": "metric",
            "x": 18,
            "y": 1,
            "width": 6,
            "height": 6,
            "properties": {
                "metrics": [
                    [ "AWS/S3", "NumberOfObjects", "StorageType", "AllStorageTypes", "BucketName", "ocf-uk-metoffice-nwp", { "label": "Number Of Objects" } ]
                ],
                "view": "timeSeries",
                "stacked": false,
                "region": "eu-west-1",
                "stat": "Average",
                "period": 86400,
                "title": "Number of Objects"
            }
        },
        {
            "type": "text",
            "x": 18,
            "y": 0,
            "width": 6,
            "height": 1,
            "properties": {
                "markdown": "# S3 Output Bucket"
            }
        }
    ]
}
EOF
}
