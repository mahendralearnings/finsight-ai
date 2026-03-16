variable "project"            { description = "Project name" }
variable "private_subnet_ids" { description = "Private subnet IDs" }
variable "rds_sg_id"          { description = "RDS security group ID" }
# variable "db_password"        { 
#   description = "DB password"
#   sensitive   = true
# }

variable "db_password" {
  description = "RDS pgvector master password"
  sensitive   = true
  default = "Finsight2026Secure"
}