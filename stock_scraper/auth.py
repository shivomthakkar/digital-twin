"""
Authentication helpers for stock_scraper.

Extracts the authenticated user_id from the Cognito JWT claims injected
by API Gateway into the Lambda event (via Mangum's aws.event scope).

In production:
    API Gateway JWT authorizer validates the Cognito token and injects
    event.requestContext.authorizer.claims.sub into the Lambda payload.

For local development:
    Set DEV_USER_ID in .env — the dependency will use that value when no
    API Gateway event is present.
"""

from __future__ import annotations

import os

from dotenv import load_dotenv
from fastapi import HTTPException, Request, status

load_dotenv()


def get_current_user(request: Request) -> str:
    """
    FastAPI dependency. Reads the Cognito sub claim from the Lambda event
    injected by Mangum:
        event.requestContext.authorizer.claims.sub

    Falls back to DEV_USER_ID env var for local development.
    """
    event: dict = request.scope.get("aws.event", {})
    sub: str | None = (
        event.get("requestContext", {})
             .get("authorizer", {})
             .get("claims", {})
             .get("sub")
    )
    if sub:
        return sub

    dev_user = os.getenv("DEV_USER_ID")
    if dev_user:
        return dev_user

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Unable to determine user identity — no JWT claims and DEV_USER_ID is not set",
    )
