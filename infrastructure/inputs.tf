variable "ecs_vcpu" {
  type    = number
  default = 256
}

variable "ecs_memory" {
  type    = number
  default = 512
}

variable "ecs_desired_count" {
  type    = number
  default = 1
}

variable "sqs_message_retention_seconds" {
  type    = number
  default = 5400 # 90 Minutes
}

variable "sns_filter_policy" {
  type = object({
    name = list(string)
  })
  default = {
    name = [
      "wind_speed",
      "wind_speed_of_gust",
      "wind_from_direction"
    ]
  }
}
