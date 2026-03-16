locals {
  zones = ["raw", "processed", "embeddings"]
}

resource "aws_s3_bucket" "zone" {
  for_each = toset(local.zones)
  bucket   = "${var.project}-${each.key}-${var.account_id}"
}

resource "aws_s3_bucket_versioning" "zone" {
  for_each = aws_s3_bucket.zone
  bucket   = each.value.id
  versioning_configuration { status = "Enabled" }
}

resource "aws_s3_bucket_public_access_block" "zone" {
  for_each                = aws_s3_bucket.zone
  bucket                  = each.value.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_lifecycle_configuration" "processed" {
  bucket = aws_s3_bucket.zone["processed"].id
  rule {
    id     = "move-to-ia"
    status = "Enabled"
    filter { prefix = "" }
    transition {
      days          = 30
      storage_class = "STANDARD_IA"
    }
  }
}