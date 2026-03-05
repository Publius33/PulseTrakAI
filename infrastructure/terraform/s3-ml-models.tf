© PUBLIUS33™ — PulseTrakAI™. All Rights Reserved.

resource "aws_s3_bucket" "ml_models" {
  bucket = "pulsetrak-ml-models-${var.environment}"
  versioning { enabled = true }
  server_side_encryption_configuration {
    rule {
      apply_server_side_encryption_by_default { sse_algorithm = "aws:kms" }
    }
  }
}
// S3 bucket for ML models and logs (placeholder)
resource "aws_s3_bucket" "ml_models" {
  bucket = "pulsetrak-ml-models-${var.env}-${var.aws_region}"
  versioning { enabled = true }
  server_side_encryption_configuration {
    rule { apply_server_side_encryption_by_default { sse_algorithm = "aws:kms" } }
  }
}

// © PUBLIUS33™ — PulseTrakAI™. All Rights Reserved.
