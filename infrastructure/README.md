# metoffice_ec2 Infrastructure

This folder specifies all relevant components to run this project on AWS.
All resources are specified in Terraform. By using Terraform anybody can run this script themselves.

![image info](./infra.png)

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
