output "db_endpoint" { value = aws_db_instance.pgvector.endpoint }
output "db_name"     { value = aws_db_instance.pgvector.db_name }