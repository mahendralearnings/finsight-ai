resource "aws_db_subnet_group" "main" {
  name       = "${var.project}-db-subnet"
  subnet_ids = var.private_subnet_ids
}

resource "aws_db_instance" "pgvector" {
  identifier        = "${var.project}-pgvector"
  engine            = "postgres"
  engine_version    = "16.4"
  instance_class    = "db.t3.micro"    # FREE tier
  allocated_storage = 20

  db_name  = "finsight"
  username = "mahendra"
  password = var.db_password

  db_subnet_group_name   = aws_db_subnet_group.main.name
  vpc_security_group_ids = [var.rds_sg_id]
  publicly_accessible    = false        # NEVER public

  backup_retention_period = 7
  skip_final_snapshot     = true
  deletion_protection     = false

  tags = { Name = "${var.project}-pgvector" }

  lifecycle {
    ignore_changes = [password]
  }
}