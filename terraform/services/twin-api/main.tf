data "aws_caller_identity" "current" {}

# Read foundation outputs (cors_origins, etc.) directly from its S3 state file.
# No script-level variable passing needed — works identically locally and in CI.
data "terraform_remote_state" "foundation" {
  backend = "s3"
  config = {
    bucket = "twin-terraform-state-${data.aws_caller_identity.current.account_id}"
    key    = "foundation/${var.environment}/terraform.tfstate"
    region = "ap-south-1"
  }
}

# Read trading-api outputs so the twin Lambda can invoke it directly.
data "terraform_remote_state" "trading" {
  backend = "s3"
  config = {
    bucket = "twin-terraform-state-${data.aws_caller_identity.current.account_id}"
    key    = "services/trading-api/${var.environment}/terraform.tfstate"
    region = "ap-south-1"
  }
}

locals {
  name_prefix = "${var.project_name}-${var.environment}"

  common_tags = {
    Project     = var.project_name
    Environment = var.environment
    ManagedBy   = "terraform"
    Service     = "twin-api"
  }
}

# ---------------------------------------------------------------------------
# Origin verification secret — shared with CloudFront via deploy-service.sh
# ---------------------------------------------------------------------------

# Generated once; only regenerated if the resource is tainted.
resource "random_password" "origin_secret" {
  length  = 32
  special = false
}

# ---------------------------------------------------------------------------
# S3 bucket for conversation memory
# ---------------------------------------------------------------------------

resource "aws_s3_bucket" "memory" {
  bucket = "${local.name_prefix}-memory-${data.aws_caller_identity.current.account_id}"
  tags   = local.common_tags
}

resource "aws_s3_bucket_public_access_block" "memory" {
  bucket = aws_s3_bucket.memory.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_ownership_controls" "memory" {
  bucket = aws_s3_bucket.memory.id

  rule {
    object_ownership = "BucketOwnerEnforced"
  }
}

# ---------------------------------------------------------------------------
# IAM role for Lambda
# ---------------------------------------------------------------------------

resource "aws_iam_role" "lambda_role" {
  name = "${local.name_prefix}-twin-api-role"
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

resource "aws_iam_role_policy_attachment" "lambda_bedrock" {
  policy_arn = "arn:aws:iam::aws:policy/AmazonBedrockFullAccess"
  role       = aws_iam_role.lambda_role.name
}

resource "aws_iam_role_policy_attachment" "lambda_s3" {
  policy_arn = "arn:aws:iam::aws:policy/AmazonS3FullAccess"
  role       = aws_iam_role.lambda_role.name
}

# Inline policy — grants permission to invoke the trading Lambda and send SES emails.
resource "aws_iam_role_policy" "lambda_tools" {
  name = "${local.name_prefix}-twin-api-tools"
  role = aws_iam_role.lambda_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "InvokeTrading"
        Effect = "Allow"
        Action = ["lambda:InvokeFunction"]
        Resource = data.terraform_remote_state.trading.outputs.lambda_function_arn
      },
      {
        Sid    = "SendSESEmail"
        Effect = "Allow"
        Action = ["ses:SendEmail", "ses:SendRawEmail"]
        Resource = [
          "arn:aws:ses:*:${data.aws_caller_identity.current.account_id}:identity/${var.ses_sender_email}",
          "arn:aws:ses:*:${data.aws_caller_identity.current.account_id}:identity/${var.notification_email}",
        ]
      },
    ]
  })
}

# ---------------------------------------------------------------------------
# Lambda package — uploaded to S3 to avoid the 70 MB direct-upload limit
# ---------------------------------------------------------------------------

resource "aws_s3_object" "lambda_zip" {
  bucket = "twin-terraform-state-${data.aws_caller_identity.current.account_id}"
  key    = "lambda-packages/twin-api/${var.environment}/lambda-deployment.zip"
  source = "${path.module}/../../../backend/lambda-deployment.zip"
  etag   = filemd5("${path.module}/../../../backend/lambda-deployment.zip")
}

# ---------------------------------------------------------------------------
# Lambda function
# ---------------------------------------------------------------------------

resource "aws_lambda_function" "api" {
  s3_bucket        = aws_s3_object.lambda_zip.bucket
  s3_key           = aws_s3_object.lambda_zip.key
  function_name    = "${local.name_prefix}-twin-api"
  role             = aws_iam_role.lambda_role.arn
  handler          = "lambda_handler.handler"
  source_code_hash = filebase64sha256("${path.module}/../../../backend/lambda-deployment.zip")
  runtime          = "python3.12"
  architectures    = ["x86_64"]
  timeout          = var.lambda_timeout
  tags             = local.common_tags

  environment {
    variables = {
      CORS_ORIGINS                  = data.terraform_remote_state.foundation.outputs.cors_origins
      S3_BUCKET                     = aws_s3_bucket.memory.id
      USE_S3                        = "true"
      BEDROCK_MODEL_ID              = var.bedrock_model_id
      ORIGIN_VERIFY_SECRET          = random_password.origin_secret.result
      TRADING_LAMBDA_FUNCTION_NAME  = data.terraform_remote_state.trading.outputs.lambda_function_name
      SES_SENDER_EMAIL              = var.ses_sender_email
      NOTIFICATION_EMAIL            = var.notification_email
      SES_REGION                    = var.ses_region
    }
  }
}

# ---------------------------------------------------------------------------
# API Gateway HTTP API
# ---------------------------------------------------------------------------

resource "aws_apigatewayv2_api" "main" {
  name          = "${local.name_prefix}-twin-api-gateway"
  protocol_type = "HTTP"
  tags          = local.common_tags

  cors_configuration {
    allow_credentials = false
    allow_headers     = ["*"]
    allow_methods     = ["GET", "POST", "OPTIONS"]
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

resource "aws_apigatewayv2_route" "get_root" {
  api_id    = aws_apigatewayv2_api.main.id
  route_key = "GET /"
  target    = "integrations/${aws_apigatewayv2_integration.lambda.id}"
}

resource "aws_apigatewayv2_route" "post_chat_open" {
  count     = var.enable_cognito_auth ? 0 : 1
  api_id    = aws_apigatewayv2_api.main.id
  route_key = "POST /chat"
  target    = "integrations/${aws_apigatewayv2_integration.lambda.id}"
}

resource "aws_apigatewayv2_route" "post_chat_protected" {
  count              = var.enable_cognito_auth ? 1 : 0
  api_id             = aws_apigatewayv2_api.main.id
  route_key          = "POST /chat"
  target             = "integrations/${aws_apigatewayv2_integration.lambda.id}"
  authorization_type = "JWT"
  authorizer_id      = aws_apigatewayv2_authorizer.cognito[0].id
}

resource "aws_apigatewayv2_route" "get_health" {
  api_id    = aws_apigatewayv2_api.main.id
  route_key = "GET /health"
  target    = "integrations/${aws_apigatewayv2_integration.lambda.id}"
}

resource "aws_lambda_permission" "api_gw" {
  statement_id  = "AllowExecutionFromAPIGateway"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.api.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.main.execution_arn}/*/*"
}

# ---------------------------------------------------------------------------
# Cognito JWT authorizer — active only when enable_cognito_auth=true
# ---------------------------------------------------------------------------

resource "aws_apigatewayv2_authorizer" "cognito" {
  count            = var.enable_cognito_auth ? 1 : 0
  api_id           = aws_apigatewayv2_api.main.id
  authorizer_type  = "JWT"
  identity_sources = ["$request.header.Authorization"]
  name             = "${local.name_prefix}-twin-api-cognito-auth"

  jwt_configuration {
    audience = [var.cognito_app_client_id]
    issuer   = "https://cognito-idp.${var.cognito_region}.amazonaws.com/${var.cognito_user_pool_id}"
  }
}

# $default catch-all — always open. Only POST /chat requires a JWT when Cognito is enabled.
resource "aws_apigatewayv2_route" "catch_all" {
  api_id    = aws_apigatewayv2_api.main.id
  route_key = "$default"
  target    = "integrations/${aws_apigatewayv2_integration.lambda.id}"
}

# ---------------------------------------------------------------------------
# Origin protection — WAF WebACL blocks direct API Gateway access
# Only requests from CloudFront (carrying x-origin-verify) are allowed.
# ---------------------------------------------------------------------------

resource "aws_wafv2_web_acl" "api_protection" {
  count = var.enable_origin_protection ? 1 : 0

  name  = "${local.name_prefix}-api-protection"
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
      metric_name                = "${local.name_prefix}-allow-cloudfront"
      sampled_requests_enabled   = false
    }
  }

  visibility_config {
    cloudwatch_metrics_enabled = false
    metric_name                = "${local.name_prefix}-api-protection"
    sampled_requests_enabled   = false
  }
}

resource "aws_wafv2_web_acl_association" "api" {
  count        = var.enable_origin_protection ? 1 : 0
  resource_arn = aws_apigatewayv2_stage.default.arn
  web_acl_arn  = aws_wafv2_web_acl.api_protection[0].arn
}
