© PUBLIUS33™ — PulseTrakAI™. All Rights Reserved.

# Architecture — CDN and API Gateway

Key components:
- CDN: CloudFront (or Fastly) serving static frontend assets with TLS and caching.
- DNS: Route53 records for `api.pulsetrak.ai`, `app.pulsetrak.ai`, `www.pulsetrak.ai`.
- API Gateway: front-facing API Gateway that forwards to an NGINX Ingress on EKS for rate limiting and WAF integration.
- WAF: Web Application Firewall (AWS WAF or Cloudflare) to protect against SQLi/XSS and bot traffic.
- DDoS protection: enable AWS Shield Advanced or CDN DDoS protections.

Flow:
1. Users hit `app.pulsetrak.ai` (CloudFront) which serves the static SPA.
2. API calls to `api.pulsetrak.ai` are routed through API Gateway which performs edge validation, WAF filtering, and forwards to the internal NGINX ingress.
3. Ingress handles routing to `backend`, `ml-engine`, and other services. mTLS is used for internal service-to-service traffic.
