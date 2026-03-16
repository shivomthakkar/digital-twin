data "aws_caller_identity" "current" {}

locals {
  name_prefix = "${var.project_name}-${var.environment}"

  aliases = var.use_custom_domain && var.root_domain != "" ? [
    var.root_domain,
    "www.${var.root_domain}"
  ] : []

  common_tags = {
    Project     = var.project_name
    Environment = var.environment
    ManagedBy   = "terraform"
  }

  # Active services: those with a non-empty gateway_url and verify_secret.
  active_services = { for k, v in var.api_services : k => v if v.gateway_url != "" && v.verify_secret != "" }

  # Flat map: path_prefix => { svc_name, path_pattern }
  # Creates one CloudFront cache behavior per path prefix, routed to the owning service's origin.
  cache_behaviors = merge([
    for svc_name, svc in local.active_services : {
      for p in svc.path_prefixes : p => {
        svc_name     = svc_name
        path_pattern = "${p}/*"
      }
    }
  ]...)
}

# ---------------------------------------------------------------------------
# Frontend S3 bucket
# ---------------------------------------------------------------------------

resource "aws_s3_bucket" "frontend" {
  bucket = "${local.name_prefix}-frontend-${data.aws_caller_identity.current.account_id}"
  tags   = local.common_tags
}

resource "aws_s3_bucket_public_access_block" "frontend" {
  bucket = aws_s3_bucket.frontend.id

  block_public_acls       = false
  block_public_policy     = false
  ignore_public_acls      = false
  restrict_public_buckets = false
}

resource "aws_s3_bucket_website_configuration" "frontend" {
  bucket = aws_s3_bucket.frontend.id

  index_document { suffix = "index.html" }
  error_document { key = "404.html" }
}

resource "aws_s3_bucket_policy" "frontend" {
  bucket = aws_s3_bucket.frontend.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Sid       = "PublicReadGetObject"
      Effect    = "Allow"
      Principal = "*"
      Action    = "s3:GetObject"
      Resource  = "${aws_s3_bucket.frontend.arn}/*"
    }]
  })

  depends_on = [aws_s3_bucket_public_access_block.frontend]
}

# ---------------------------------------------------------------------------
# CloudFront Functions — one per service, each stripping only its own prefix(es)
# ---------------------------------------------------------------------------

resource "aws_cloudfront_function" "path_rewrite" {
  for_each = local.active_services

  name    = "${local.name_prefix}-${each.key}-rewrite"
  runtime = "cloudfront-js-2.0"
  comment = "Strip path prefix(es) for ${each.key} before forwarding to API Gateway"
  publish = true

  code = <<-EOF
    var PREFIXES = ${jsonencode(each.value.path_prefixes)};
    function handler(event) {
      var req = event.request;
      for (var i = 0; i < PREFIXES.length; i++) {
        var p = PREFIXES[i];
        if (req.uri === p) { req.uri = '/'; return req; }
        if (req.uri.startsWith(p + '/')) { req.uri = req.uri.slice(p.length); return req; }
      }
      return req;
    }
  EOF
}

# ---------------------------------------------------------------------------
# CloudFront distribution
# ---------------------------------------------------------------------------

resource "aws_cloudfront_distribution" "main" {
  aliases = local.aliases

  viewer_certificate {
    acm_certificate_arn            = var.use_custom_domain ? aws_acm_certificate.site[0].arn : null
    cloudfront_default_certificate = var.use_custom_domain ? false : true
    ssl_support_method             = var.use_custom_domain ? "sni-only" : null
    minimum_protocol_version       = "TLSv1.2_2021"
  }

  origin {
    domain_name = aws_s3_bucket_website_configuration.frontend.website_endpoint
    origin_id   = "S3-${aws_s3_bucket.frontend.id}"

    custom_origin_config {
      http_port              = 80
      https_port             = 443
      origin_protocol_policy = "http-only"
      origin_ssl_protocols   = ["TLSv1.2"]
    }
  }

  # API Gateway origins — one per wired service, each with its own x-origin-verify secret
  dynamic "origin" {
    for_each = local.active_services
    content {
      domain_name = replace(replace(origin.value.gateway_url, "https://", ""), "http://", "")
      origin_id   = "APIG-${origin.key}"

      # CloudFront adds this header; WAF on the APIG stage blocks requests missing it
      custom_header {
        name  = "x-origin-verify"
        value = origin.value.verify_secret
      }

      custom_origin_config {
        http_port              = 80
        https_port             = 443
        origin_protocol_policy = "https-only"
        origin_ssl_protocols   = ["TLSv1.2"]
      }
    }
  }

  enabled             = true
  is_ipv6_enabled     = true
  default_root_object = "index.html"
  tags                = local.common_tags

  # One cache behavior per configured path prefix, routed to the owning service's origin
  dynamic "ordered_cache_behavior" {
    for_each = local.cache_behaviors
    content {
      path_pattern     = ordered_cache_behavior.value.path_pattern
      allowed_methods  = ["DELETE", "GET", "HEAD", "OPTIONS", "PATCH", "POST", "PUT"]
      cached_methods   = ["GET", "HEAD"]
      target_origin_id = "APIG-${ordered_cache_behavior.value.svc_name}"

      # Forward auth + content headers; pass all query strings; no cookie forwarding
      forwarded_values {
        query_string = true
        headers      = ["Authorization", "Content-Type", "Accept", "Origin"]
        cookies { forward = "none" }
      }

      viewer_protocol_policy = "redirect-to-https"
      min_ttl                = 0
      default_ttl            = 0
      max_ttl                = 0

      # Strip the matched prefix so FastAPI receives clean paths
      function_association {
        event_type   = "viewer-request"
        function_arn = aws_cloudfront_function.path_rewrite[ordered_cache_behavior.value.svc_name].arn
      }
    }
  }

  default_cache_behavior {
    allowed_methods  = ["DELETE", "GET", "HEAD", "OPTIONS", "PATCH", "POST", "PUT"]
    cached_methods   = ["GET", "HEAD"]
    target_origin_id = "S3-${aws_s3_bucket.frontend.id}"

    forwarded_values {
      query_string = false
      cookies { forward = "none" }
    }

    viewer_protocol_policy = "redirect-to-https"
    min_ttl                = 0
    default_ttl            = 3600
    max_ttl                = 86400
  }

  restrictions {
    geo_restriction { restriction_type = "none" }
  }

  custom_error_response {
    error_code         = 404
    response_code      = 200
    response_page_path = "/index.html"
  }
}

# ---------------------------------------------------------------------------
# Optional: custom domain (ACM + Route53) — only when use_custom_domain=true
# ---------------------------------------------------------------------------

# Creates the hosted zone for the domain. For externally purchased domains,
# take the NS records from the `route53_name_servers` output and set them
# as the nameservers at your domain registrar before running setup-infra.sh
# for the first time (or re-apply after creation to trigger ACM validation).
resource "aws_route53_zone" "root" {
  count = var.use_custom_domain ? 1 : 0
  name  = var.root_domain
  tags  = local.common_tags
}

resource "aws_acm_certificate" "site" {
  count                     = var.use_custom_domain ? 1 : 0
  provider                  = aws.us_east_1
  domain_name               = var.root_domain
  subject_alternative_names = ["www.${var.root_domain}"]
  validation_method         = "DNS"
  lifecycle { create_before_destroy = true }
  tags = local.common_tags
}

resource "aws_route53_record" "site_validation" {
  for_each = var.use_custom_domain ? {
    for dvo in aws_acm_certificate.site[0].domain_validation_options :
    dvo.domain_name => dvo
  } : {}

  zone_id = aws_route53_zone.root[0].zone_id
  name    = each.value.resource_record_name
  type    = each.value.resource_record_type
  ttl     = 300
  records = [each.value.resource_record_value]
}

resource "aws_acm_certificate_validation" "site" {
  count           = var.use_custom_domain ? 1 : 0
  provider        = aws.us_east_1
  certificate_arn = aws_acm_certificate.site[0].arn
  validation_record_fqdns = [
    for r in aws_route53_record.site_validation : r.fqdn
  ]
}

resource "aws_route53_record" "alias_root" {
  count   = var.use_custom_domain ? 1 : 0
  zone_id = aws_route53_zone.root[0].zone_id
  name    = var.root_domain
  type    = "A"

  alias {
    name                   = aws_cloudfront_distribution.main.domain_name
    zone_id                = aws_cloudfront_distribution.main.hosted_zone_id
    evaluate_target_health = false
  }
}

resource "aws_route53_record" "alias_root_ipv6" {
  count   = var.use_custom_domain ? 1 : 0
  zone_id = aws_route53_zone.root[0].zone_id
  name    = var.root_domain
  type    = "AAAA"

  alias {
    name                   = aws_cloudfront_distribution.main.domain_name
    zone_id                = aws_cloudfront_distribution.main.hosted_zone_id
    evaluate_target_health = false
  }
}

resource "aws_route53_record" "alias_www" {
  count   = var.use_custom_domain ? 1 : 0
  zone_id = aws_route53_zone.root[0].zone_id
  name    = "www.${var.root_domain}"
  type    = "A"

  alias {
    name                   = aws_cloudfront_distribution.main.domain_name
    zone_id                = aws_cloudfront_distribution.main.hosted_zone_id
    evaluate_target_health = false
  }
}

resource "aws_route53_record" "alias_www_ipv6" {
  count   = var.use_custom_domain ? 1 : 0
  zone_id = aws_route53_zone.root[0].zone_id
  name    = "www.${var.root_domain}"
  type    = "AAAA"

  alias {
    name                   = aws_cloudfront_distribution.main.domain_name
    zone_id                = aws_cloudfront_distribution.main.hosted_zone_id
    evaluate_target_health = false
  }
}

# ---------------------------------------------------------------------------
# User profiles table — shared across all services.
# Stores per-user data: Dhan auth tokens, preferences, etc.
# Keyed by user_id (Cognito sub claim).
# ---------------------------------------------------------------------------

resource "aws_dynamodb_table" "user_profiles" {
  name         = "${local.name_prefix}-user-profiles"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "user_id"

  attribute {
    name = "user_id"
    type = "S"
  }

  server_side_encryption {
    enabled = true
  }

  tags = local.common_tags
}

resource "aws_iam_policy" "user_profiles_access" {
  name        = "${local.name_prefix}-user-profiles-access"
  description = "Allows services to read and write user profile records"
  tags        = local.common_tags

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "UserProfilesReadWrite"
        Effect = "Allow"
        Action = [
          "dynamodb:GetItem",
          "dynamodb:PutItem",
          "dynamodb:UpdateItem"
        ]
        Resource = aws_dynamodb_table.user_profiles.arn
      }
    ]
  })
}
