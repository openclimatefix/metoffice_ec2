output "s3_dest_bucket" {
  value = aws_s3_bucket.output.bucket
}

output "sqs_url" {
  value = aws_sqs_queue.metqueue.id
}