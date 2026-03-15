output "state_bucket_name" {
  description = "S3 bucket name used for all terraform remote state"
  value       = aws_s3_bucket.terraform_state.id
}

output "dynamodb_table_name" {
  description = "DynamoDB table name used for state locking"
  value       = aws_dynamodb_table.terraform_locks.name
}
