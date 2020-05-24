# metoffice_ec2 Infrastructure

This folder specifies all relevant components to run this project on AWS.
All resources are specified in Terraform. By using Terraform anybody can run this script themselves.

![Architecture Diagram](./infra.png)

Via the [UK Met Office's UKV and MOGREPS-UK numerical weather predictions from AWS](https://registry.opendata.aws/uk-met-office/) messages are continously published to an SNS topic. Following the [Met Office's instructions](https://github.com/MetOffice/aws-earth-examples/blob/master/examples/2.%20Subscribing%20to%20data.ipynb), we set up an SQS queue to listen to these messages.
Using a SNS topic subscription we listen to and filter the messages published by the Met Office.

To consume the messages from SQS we are running a small ECS Fargate cluster. Inside that cluster we run a small EC2 instance that runs the python script in `scripts/ec2.py`. This script is dockerised, the [image can be found on the Docker Hub](https://hub.docker.com/r/openclimatefix/metoffice_ec2).

The script puts the final files into an S3 Bucket.

## Setup

**Note**: We assume that the [Terraform CLI](https://learn.hashicorp.com/terraform/getting-started/install) is already installed.

```
terraform init
terraform apply
```

## Configuration (optional)
You can easily overwrite the following config variables defined in `inputs.tf`:

| Name                            | Default   | Description |
| ------------------------------- | --------- | ----------- |
| `ecs_vcpu`                      | `256`     | How much CPU we reserve for the script |
| `ecs_memory`                    | `512`     | How much memory we reserve for the script |
| `ecs_desired_count`             | `1`       | How many instances of the script we run in parallel |
| `sqs_message_retention_seconds` | `5400`    | How long SQS messages are kept if unconsumed |
| `sns_filter_policy`             | `["wind_speed", "wind_speed_of_gust", "wind_from_direction"]` | What kinds of messages we are interested in |
