"""
Dhan authentication module.

Responsibilities:
  1. Extract user_id from the Cognito JWT claims injected by API Gateway
     (event.requestContext.authorizer.claims.sub via Mangum's aws.event).
     Falls back to DEV_USER_ID env var for local development.
  2. Generate / renew Dhan access tokens via the Dhan Auth API.
  3. Persist tokens in the shared user-profiles DynamoDB table using UpdateItem
     so other profile attributes (preferences, etc.) are never clobbered.
  4. Provide a FastAPI dependency that returns a ready-to-use dhanhq broker
     instance for the authenticated user.
"""

from __future__ import annotations

import os
import time
from datetime import datetime, timezone
from typing import Any

import boto3
import httpx
from botocore.exceptions import ClientError
from dhanhq import dhanhq
from dotenv import load_dotenv
from fastapi import Depends, HTTPException, Request, status

load_dotenv()

# ---------------------------------------------------------------------------
# Configuration (all from environment variables)
# ---------------------------------------------------------------------------

DYNAMODB_AUTH_TABLE = os.getenv("DYNAMODB_AUTH_TABLE", "")
USER_PROFILES_TABLE = os.getenv("USER_PROFILES_TABLE", DYNAMODB_AUTH_TABLE)  # fallback for backwards compat
AWS_REGION = os.getenv("AWS_REGION", "ap-south-1")

_DHAN_GENERATE_TOKEN_URL = "https://auth.dhan.co/app/generateAccessToken"
_DHAN_RENEW_TOKEN_URL = "https://api.dhan.co/v2/RenewToken"

# ---------------------------------------------------------------------------
# FastAPI dependency — extracts user_id from the Lambda event JWT claims.
# When running locally (no API Gateway), falls back to DEV_USER_ID env var.
# ---------------------------------------------------------------------------

def get_current_user(request: Request) -> str:
    """
    FastAPI dependency.  In production (via API Gateway + Cognito authorizer),
    reads the Cognito sub claim from the Lambda event injected by Mangum:
        event.requestContext.authorizer.claims.sub

    For local development, set DEV_USER_ID in .env as an explicit fallback.
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


# ---------------------------------------------------------------------------
# DynamoDB persistence
# ---------------------------------------------------------------------------

def _dynamodb_table():
    """Return a boto3 DynamoDB Table resource for the user-profiles table."""
    if not USER_PROFILES_TABLE:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="USER_PROFILES_TABLE is not configured",
        )
    dynamodb = boto3.resource("dynamodb", region_name=AWS_REGION)
    return dynamodb.Table(USER_PROFILES_TABLE)


def store_token(user_id: str, token_data: dict) -> None:
    print(user_id, token_data)
    """
    Persist the Dhan token inside the user's profile record using UpdateItem.
    Stored as a nested `dhan` map so other profile attributes are never clobbered.

    Item shape:
        { user_id, dhan: { client_id, access_token, expiry_time }, ... }
    """
    table = _dynamodb_table()

    expiry_str: str = token_data.get("expiryTime", "")

    dhan_record: dict[str, Any] = {
        "client_id": token_data.get("dhanClientId", ""),
        "access_token": token_data.get("accessToken", ""),
        "expiry_time": expiry_str,
    }

    try:
        table.update_item(
            Key={"user_id": user_id},
            UpdateExpression="SET dhan = :dhan",
            ExpressionAttributeValues={":dhan": dhan_record},
        )
    except ClientError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to store token: {exc.response['Error']['Message']}",
        ) from exc


def get_token(user_id: str) -> dict:
    """
    Retrieve the `dhan` sub-record from the user's profile.

    Raises HTTP 401 if no profile / token is found or if the token has expired.
    """
    table = _dynamodb_table()
    try:
        response = table.get_item(Key={"user_id": user_id})
    except ClientError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve token: {exc.response['Error']['Message']}",
        ) from exc

    item = response.get("Item")
    if not item or "dhan" not in item:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No Dhan token found for this user — call POST /auth/generate-token first",
        )

    dhan = item["dhan"]

    # Belt-and-suspenders expiry check in application code
    expiry_str: str = dhan.get("expiry_time", "")
    if expiry_str:
        try:
            expiry_dt = datetime.fromisoformat(expiry_str.split(".")[0])
            # Dhan expiry is expressed in IST (UTC+5:30)
            expiry_epoch = expiry_dt.replace(tzinfo=timezone.utc).timestamp() - 5.5 * 3600
            if time.time() > expiry_epoch:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Dhan token has expired — call POST /auth/generate-token or POST /auth/renew-token",
                )
        except ValueError:
            pass  # unparseable expiry — let the Dhan API reject it if invalid

    return dhan


# ---------------------------------------------------------------------------
# Dhan Auth API calls
# ---------------------------------------------------------------------------

def generate_dhan_token(dhan_client_id: str, pin: str, totp: str) -> dict:
    """
    Call the Dhan generateAccessToken endpoint and return the full response dict.

    Query params: dhanClientId, pin (6-digit), totp (6-digit TOTP code).
    PIN and TOTP values are never logged.
    """
    params = {
        "dhanClientId": dhan_client_id,
        "pin": pin,
        "totp": totp,
    }
    try:
        response = httpx.post(
            _DHAN_GENERATE_TOKEN_URL,
            params=params,
            timeout=10,
        )
        if response.status_code != 200:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Dhan token generation failed (HTTP {response.status_code}): {response.text}",
            )
        return response.json()
    except HTTPException:
        raise
    except httpx.RequestError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Could not reach Dhan auth service: {exc}",
        ) from exc


def renew_dhan_token(dhan_client_id: str, access_token: str) -> dict:
    """
    Call the Dhan RenewToken endpoint to get a fresh 24-hour token.

    Only works for tokens that are currently active (not expired).
    """
    headers = {
        "access-token": access_token,
        "dhanClientId": dhan_client_id,
    }
    try:
        response = httpx.get(
            _DHAN_RENEW_TOKEN_URL,
            headers=headers,
            timeout=10,
        )
        if response.status_code != 200:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Dhan token renewal failed (HTTP {response.status_code}): {response.text}",
            )
        return response.json()
    except HTTPException:
        raise
    except httpx.RequestError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Could not reach Dhan API: {exc}",
        ) from exc


# ---------------------------------------------------------------------------
# Broker factory dependency
# ---------------------------------------------------------------------------

def get_broker_for_user(user_id: str) -> dhanhq:
    """Return an initialised dhanhq broker instance for the given user_id."""
    dhan = get_token(user_id)
    return dhanhq(dhan["client_id"], dhan["access_token"])


def get_current_broker(user_id: str = Depends(get_current_user)) -> dhanhq:
    """
    FastAPI dependency.  Extracts user_id from JWT claims (or DEV_USER_ID),
    looks up the user's Dhan token from the user-profiles table, and returns
    an initialised dhanhq broker instance.
    """
    return get_broker_for_user(user_id)
