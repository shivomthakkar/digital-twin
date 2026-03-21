data "aws_caller_identity" "current" {}

# Read foundation outputs — cors_origins, user_profiles table name/policy, etc.
data "terraform_remote_state" "foundation" {
  backend = "s3"
  config = {
    bucket = "twin-terraform-state-${data.aws_caller_identity.current.account_id}"
    key    = "foundation/${var.environment}/terraform.tfstate"
    region = "ap-south-1"
  }
}

locals {
  service_name = "trading-api"
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

# Grants GetItem/PutItem/UpdateItem on the shared user-profiles table
resource "aws_iam_role_policy_attachment" "user_profiles" {
  policy_arn = data.terraform_remote_state.foundation.outputs.user_profiles_access_policy_arn
  role       = aws_iam_role.lambda_role.name
}

# ---------------------------------------------------------------------------
# Lambda package — uploaded to S3 to avoid the 70 MB direct-upload limit
# ---------------------------------------------------------------------------

resource "aws_s3_object" "lambda_zip" {
  bucket = "twin-terraform-state-${data.aws_caller_identity.current.account_id}"
  key    = "lambda-packages/${local.service_name}/${var.environment}/lambda-deployment.zip"
  source = "${path.module}/../../../trading/lambda-deployment.zip"
  etag   = filemd5("${path.module}/../../../trading/lambda-deployment.zip")
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
  source_code_hash = filebase64sha256("${path.module}/../../../trading/lambda-deployment.zip")
  runtime          = "python3.12"
  architectures    = ["x86_64"]
  timeout          = 30
  tags             = local.common_tags

  environment {
    variables = {
      CORS_ORIGINS         = data.terraform_remote_state.foundation.outputs.cors_origins
      USER_PROFILES_TABLE  = data.terraform_remote_state.foundation.outputs.user_profiles_table_name
      ORIGIN_VERIFY_SECRET = random_password.origin_secret.result
      DHAN_MODE            = var.dhan_mode
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
    throttling_burst_limit = 10
    throttling_rate_limit  = 5
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
# Routes — all routes are open when Cognito is off, JWT-protected when it is on.
# ---------------------------------------------------------------------------

resource "aws_apigatewayv2_route" "get_health_open" {
  count     = var.enable_cognito_auth ? 0 : 1
  api_id    = aws_apigatewayv2_api.main.id
  route_key = "GET /health"
  target    = "integrations/${aws_apigatewayv2_integration.lambda.id}"
}

resource "aws_apigatewayv2_route" "get_health_protected" {
  count              = var.enable_cognito_auth ? 1 : 0
  api_id             = aws_apigatewayv2_api.main.id
  route_key          = "GET /health"
  target             = "integrations/${aws_apigatewayv2_integration.lambda.id}"
  authorization_type = "JWT"
  authorizer_id      = aws_apigatewayv2_authorizer.cognito[0].id
}

resource "aws_apigatewayv2_route" "post_auth_generate_open" {
  count     = var.enable_cognito_auth ? 0 : 1
  api_id    = aws_apigatewayv2_api.main.id
  route_key = "POST /auth/generate-token"
  target    = "integrations/${aws_apigatewayv2_integration.lambda.id}"
}

resource "aws_apigatewayv2_route" "post_auth_generate_protected" {
  count              = var.enable_cognito_auth ? 1 : 0
  api_id             = aws_apigatewayv2_api.main.id
  route_key          = "POST /auth/generate-token"
  target             = "integrations/${aws_apigatewayv2_integration.lambda.id}"
  authorization_type = "JWT"
  authorizer_id      = aws_apigatewayv2_authorizer.cognito[0].id
}

resource "aws_apigatewayv2_route" "post_auth_renew_open" {
  count     = var.enable_cognito_auth ? 0 : 1
  api_id    = aws_apigatewayv2_api.main.id
  route_key = "POST /auth/renew-token"
  target    = "integrations/${aws_apigatewayv2_integration.lambda.id}"
}

resource "aws_apigatewayv2_route" "post_auth_renew_protected" {
  count              = var.enable_cognito_auth ? 1 : 0
  api_id             = aws_apigatewayv2_api.main.id
  route_key          = "POST /auth/renew-token"
  target             = "integrations/${aws_apigatewayv2_integration.lambda.id}"
  authorization_type = "JWT"
  authorizer_id      = aws_apigatewayv2_authorizer.cognito[0].id
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


