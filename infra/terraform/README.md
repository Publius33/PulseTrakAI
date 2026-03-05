PulseTrakAI Terraform skeleton

This folder contains a minimal Terraform skeleton for PulseTrakAI to
bootstrap cloud resources (S3, etc.).

Customize providers, state backend, and modules before applying in production.

Commands:

- `terraform init`
- `terraform plan -var='env=dev'`
- `terraform apply -var='env=dev'`

Note: This is intentionally minimal; expand modules for VPC, ECS, RDS, and CI.
