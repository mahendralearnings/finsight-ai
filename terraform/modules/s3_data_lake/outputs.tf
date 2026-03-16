output "bucket_names" {
  value = { for k, v in aws_s3_bucket.zone : k => v.id }
}

output "bucket_arns" {
  value = { for k, v in aws_s3_bucket.zone : k => v.arn }
}