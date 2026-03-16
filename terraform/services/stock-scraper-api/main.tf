data "aws_caller_identity" "current" {}

# Read foundation outputs (cors_origins, cloudfront_url, etc.) from its S3 state.
data "terraform_remote_state" "foundation" {
  backend = "s3"
  config = {
    bucket = "twin-terraform-state-${data.aws_caller_identity.current.account_id}"
    key    = "foundation/${var.environment}/terraform.tfstate"
    region = "ap-south-1"
  }
}

locals {
  service_name = "stock-scraper-api"
  name_prefix  = "${var.project_name}-${var.environment}"

  common_tags = {
    Project     = var.project_name
    Environment = var.environment
    ManagedBy   = "terraform"
    Service     = local.service_name
  }
}

# ---------------------------------------------------------------------------
# Origin verification secret — shared with CloudFront via deploy-service.sh
# ---------------------------------------------------------------------------

resource "random_password" "origin_secret" {
  length  = 32
  special = false
}

# ---------------------------------------------------------------------------
# DynamoDB tables (provisioned per db.py contract)
# ---------------------------------------------------------------------------

resource "aws_dynamodb_table" "stock_financials" {
  name         = "${local.name_prefix}-StockFinancials"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "symbol"
  range_key    = "scraped_at"
  tags         = local.common_tags

  attribute {
    name = "symbol"
    type = "S"
  }
  attribute {
    name = "scraped_at"
    type = "S"
  }
}

resource "aws_dynamodb_table" "stock_documents" {
  name         = "${local.name_prefix}-StockDocuments"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "symbol"
  range_key    = "scraped_at"
  tags         = local.common_tags

  attribute {
    name = "symbol"
    type = "S"
  }
  attribute {
    name = "scraped_at"
    type = "S"
  }
}

resource "aws_dynamodb_table" "stock_sections" {
  name         = "${local.name_prefix}-StockSections"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "symbol"
  range_key    = "scraped_at"
  tags         = local.common_tags

  attribute {
    name = "symbol"
    type = "S"
  }
  attribute {
    name = "scraped_at"
    type = "S"
  }
}

# ---------------------------------------------------------------------------
# IAM role for Lambda
# ---------------------------------------------------------------------------

resource "aws_iam_role" "lambda_role" {
  name = "${local.name_prefix}-${local.service_name}-role"
  tags = local.common_tags

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action    = "sts:AssumeRole"
      Effect    = "Allow"
      Principal = { Service = "lambda.amazonaws.com" }
    }]
  })
}

resource "aws_iam_role_policy_attachment" "lambda_basic" {
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
  role       = aws_iam_role.lambda_role.name
}

resource "aws_iam_role_policy_attachment" "user_profiles" {
  policy_arn = data.terraform_remote_state.foundation.outputs.user_profiles_access_policy_arn
  role       = aws_iam_role.lambda_role.name
}

resource "aws_iam_role_policy" "dynamodb_access" {
  name = "${local.name_prefix}-${local.service_name}-dynamodb"
  role = aws_iam_role.lambda_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Action = [
        "dynamodb:PutItem",
        "dynamodb:GetItem",
        "dynamodb:Query",
        "dynamodb:Scan",
      ]
      Resource = [
        aws_dynamodb_table.stock_financials.arn,
        aws_dynamodb_table.stock_documents.arn,
        aws_dynamodb_table.stock_sections.arn,
      ]
    }]
  })
}

# ---------------------------------------------------------------------------
# Lambda package — uploaded to S3 to avoid the 70 MB direct-upload limit
# ---------------------------------------------------------------------------

resource "aws_s3_object" "lambda_zip" {
  bucket = "twin-terraform-state-${data.aws_caller_identity.current.account_id}"
  key    = "lambda-packages/${local.service_name}/${var.environment}/lambda-deployment.zip"
  source = "${path.module}/../../../stock_scraper/lambda-deployment.zip"
  etag   = filemd5("${path.module}/../../../stock_scraper/lambda-deployment.zip")
}

# ---------------------------------------------------------------------------
# Lambda function
# ---------------------------------------------------------------------------

resource "aws_lambda_function" "api" {
  s3_bucket        = aws_s3_object.lambda_zip.bucket
  s3_key           = aws_s3_object.lambda_zip.key
  function_name    = "${local.name_prefix}-${local.service_name}"
  role             = aws_iam_role.lambda_role.arn
  handler          = "lambda_handler.handler"
  source_code_hash = filebase64sha256("${path.module}/../../../stock_scraper/lambda-deployment.zip")
  runtime          = "python3.12"
  architectures    = ["x86_64"]
  timeout          = var.lambda_timeout
  tags             = local.common_tags

  environment {
    variables = {
      CORS_ORIGINS          = data.terraform_remote_state.foundation.outputs.cors_origins
      ORIGIN_VERIFY_SECRET  = random_password.origin_secret.result
      DYNAMODB_TABLE_PREFIX = "${local.name_prefix}-"
      USER_PROFILES_TABLE   = data.terraform_remote_state.foundation.outputs.user_profiles_table_name
    }
  }
}

# ---------------------------------------------------------------------------
# API Gateway HTTP API
# ---------------------------------------------------------------------------

resource "aws_apigatewayv2_api" "main" {
  name          = "${local.name_prefix}-${local.service_name}-gateway"
  protocol_type = "HTTP"
  tags          = local.common_tags

  cors_configuration {
    allow_credentials = false
    allow_headers     = ["*"]
    allow_methods     = ["GET", "POST", "DELETE", "OPTIONS"]
    allow_origins     = split(",", data.terraform_remote_state.foundation.outputs.cors_origins)
    max_age           = 300
  }
}

resource "aws_apigatewayv2_stage" "default" {
  api_id      = aws_apigatewayv2_api.main.id
  name        = "$default"
  auto_deploy = true
  tags        = local.common_tags

  default_route_settings {
    throttling_burst_limit = var.api_throttle_burst_limit
    throttling_rate_limit  = var.api_throttle_rate_limit
  }
}

resource "aws_apigatewayv2_integration" "lambda" {
  api_id           = aws_apigatewayv2_api.main.id
  integration_type = "AWS_PROXY"
  integration_uri  = aws_lambda_function.api.invoke_arn
}

# ---------------------------------------------------------------------------
# Cognito JWT authorizer — active only when enable_cognito_auth=true
# ---------------------------------------------------------------------------

resource "aws_apigatewayv2_authorizer" "cognito" {
  count            = var.enable_cognito_auth ? 1 : 0
  api_id           = aws_apigatewayv2_api.main.id
  authorizer_type  = "JWT"
  identity_sources = ["$request.header.Authorization"]
  name             = "${local.name_prefix}-${local.service_name}-cognito-auth"

  jwt_configuration {
    audience = [var.cognito_app_client_id]
    issuer   = "https://cognito-idp.${var.cognito_region}.amazonaws.com/${var.cognito_user_pool_id}"
  }
}

# ---------------------------------------------------------------------------
# Routes — GET /health is always open; $default is protected when Cognito is on
# ---------------------------------------------------------------------------

resource "aws_apigatewayv2_route" "get_health" {
  api_id    = aws_apigatewayv2_api.main.id
  route_key = "GET /health"
  target    = "integrations/${aws_apigatewayv2_integration.lambda.id}"
}

# OPTIONS preflights must never hit the JWT authorizer — always open regardless of auth mode.
resource "aws_apigatewayv2_route" "options_preflight" {
  api_id    = aws_apigatewayv2_api.main.id
  route_key = "OPTIONS /{proxy+}"
  target    = "integrations/${aws_apigatewayv2_integration.lambda.id}"
}

resource "aws_apigatewayv2_route" "catch_all_open" {
  count     = var.enable_cognito_auth ? 0 : 1
  api_id    = aws_apigatewayv2_api.main.id
  route_key = "$default"
  target    = "integrations/${aws_apigatewayv2_integration.lambda.id}"
}

resource "aws_apigatewayv2_route" "catch_all_protected" {
  count              = var.enable_cognito_auth ? 1 : 0
  api_id             = aws_apigatewayv2_api.main.id
  route_key          = "$default"
  target             = "integrations/${aws_apigatewayv2_integration.lambda.id}"
  authorization_type = "JWT"
  authorizer_id      = aws_apigatewayv2_authorizer.cognito[0].id
}

resource "aws_lambda_permission" "api_gw" {
  statement_id  = "AllowExecutionFromAPIGateway"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.api.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.main.execution_arn}/*/*"
}

# ---------------------------------------------------------------------------
# Origin protection — WAF WebACL blocks direct API Gateway access
# ---------------------------------------------------------------------------

resource "aws_wafv2_web_acl" "api_protection" {
  count = var.enable_origin_protection ? 1 : 0

  name  = "${local.name_prefix}-${local.service_name}-protection"
  scope = "REGIONAL"
  tags  = local.common_tags

  default_action {
    block {}
  }

  rule {
    name     = "AllowCloudFrontOrigin"
    priority = 1

    action {
      allow {}
    }

    statement {
      byte_match_statement {
        field_to_match {
          single_header { name = "x-origin-verify" }
        }
        positional_constraint = "EXACTLY"
        search_string         = random_password.origin_secret.result
        text_transformation {
          priority = 0
          type     = "NONE"
        }
      }
    }

    visibility_config {
      cloudwatch_metrics_enabled = false
      metric_name                = "${local.name_prefix}-${local.service_name}-allow-cloudfront"
      sampled_requests_enabled   = false
    }
  }

  visibility_config {
    cloudwatch_metrics_enabled = false
    metric_name                = "${local.name_prefix}-${local.service_name}-api-protection"
    sampled_requests_enabled   = false
  }
}

resource "aws_wafv2_web_acl_association" "api" {
  count        = var.enable_origin_protection ? 1 : 0
  resource_arn = aws_apigatewayv2_stage.default.arn
  web_acl_arn  = aws_wafv2_web_acl.api_protection[0].arn
}
