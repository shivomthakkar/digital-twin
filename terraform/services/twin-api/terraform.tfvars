# Static service configuration — does not change per environment.
# Pass environment and cors_origins at apply time via the script.

project_name             = "twin"
bedrock_model_id         = "amazon.nova-micro-v1:0"
lambda_timeout           = 60
api_throttle_burst_limit = 10
api_throttle_rate_limit  = 5

# Agentic tool configuration — set before deploying.
ses_sender_email   = "messaging@shivomthakkar.in"   # replace with your verified SES domain
notification_email = "shivomthakkar15@gmail.com"
