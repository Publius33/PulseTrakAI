© PUBLIUS33™ — PulseTrakAI™. All Rights Reserved.

output "vpc_id" {
  description = "VPC ID"
  value       = aws_vpc.pulsetrak.id
  sensitive   = false
}

output "eks_cluster_name" {
  description = "EKS cluster name"
  value       = aws_eks_cluster.pulsetrak_cluster.name
}
// Terraform outputs (placeholder)
output "vpc_id" {
  value = "<vpc-id>"
}

output "eks_cluster_name" {
  value = "pulsetrak-eks"
}

// © PUBLIUS33™ — PulseTrakAI™. All Rights Reserved.
