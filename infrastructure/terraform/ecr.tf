© PUBLIUS33™ — PulseTrakAI™. All Rights Reserved.

resource "aws_ecr_repository" "backend" {
  name = "pulsetrak-backend"
}

resource "aws_ecr_repository" "ml_engine" {
  name = "pulsetrak-ml-engine"
}

resource "aws_ecr_repository" "frontend" {
  name = "pulsetrak-frontend"
}
// ECR repositories for images (placeholder)
resource "aws_ecr_repository" "backend" {
  name = "pulsetrak-backend"
}
resource "aws_ecr_repository" "ml_engine" {
  name = "pulsetrak-ml-engine"
}
resource "aws_ecr_repository" "frontend" {
  name = "pulsetrak-frontend"
}

// © PUBLIUS33™ — PulseTrakAI™. All Rights Reserved.
