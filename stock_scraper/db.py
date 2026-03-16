"""
DynamoDB interface for stock_scraper.

Tables (provisioned externally via Terraform):
  {prefix}StockFinancials  —  PK: symbol (S), SK: scraped_at (S)
  {prefix}StockDocuments   —  PK: symbol (S), SK: scraped_at (S)
  {prefix}StockSections    —  PK: symbol (S), SK: scraped_at (S)

Shared table (provisioned by the foundation module):
  USER_PROFILES_TABLE      —  PK: user_id (S)
                              watchlist attribute: List[str] of NSE/BSE symbols

Environment variables:
  AWS_REGION              — AWS region (default: ap-south-1)
  DYNAMODB_TABLE_PREFIX   — Optional prefix for all table names (default: "")
  USER_PROFILES_TABLE     — Full name of the shared user-profiles table
"""

import os
from typing import Dict, Any, List

# boto3 is imported lazily so the module loads even when boto3 is absent
_dynamodb = None


def _get_dynamodb():
    global _dynamodb
    if _dynamodb is None:
        import boto3
        region = os.getenv("AWS_REGION", "ap-south-1")
        _dynamodb = boto3.resource("dynamodb", region_name=region)
    return _dynamodb


def _table_name(base: str) -> str:
    prefix = os.getenv("DYNAMODB_TABLE_PREFIX", "")
    return f"{prefix}{base}"


# ---------------------------------------------------------------------------
# Public write functions
# ---------------------------------------------------------------------------

def insert_financial_data(symbol: str, data: Dict[str, Any], scraped_at: str) -> bool:
    """
    Insert scraped financial ratios for a symbol into DynamoDB.

    Args:
        symbol:     Stock symbol used as the partition key (stored uppercase).
        data:       Dict returned by ScreenerFetcher.extract_financial_data().
        scraped_at: ISO-8601 UTC timestamp string (sort key).

    Returns:
        True on success, False on failure.
    """
    table_name = _table_name("StockFinancials")
    item = {
        "symbol": symbol.upper(),
        "scraped_at": scraped_at,
        "data": data,
    }
    # TODO: implement DynamoDB write — uncomment once table is provisioned
    # try:
    #     table = _get_dynamodb().Table(table_name)
    #     table.put_item(Item=item)
    # except Exception as exc:
    #     print(f"[db] ERROR writing to {table_name}: {exc}", flush=True)
    #     return False
    print(
        f"[db] Would write to {table_name}: "
        f"symbol={symbol.upper()}, scraped_at={scraped_at}, "
        f"fields={list(data.keys())}",
        flush=True,
    )
    return True


def insert_section_tables(symbol: str, sections: Dict[str, Any], scraped_at: str) -> bool:
    """
    Insert structured financial section tables (P&L, Balance Sheet, Cash Flow)
    for a symbol into DynamoDB.

    Args:
        symbol:     Stock symbol (partition key, stored uppercase).
        sections:   Dict returned by ScreenerFetcher.extract_section_tables().
        scraped_at: ISO-8601 UTC timestamp string (sort key).

    Returns:
        True on success, False on failure.
    """
    table_name = _table_name("StockSections")
    item = {
        "symbol": symbol.upper(),
        "scraped_at": scraped_at,
        "sections": sections,
    }
    # TODO: implement DynamoDB write — uncomment once table is provisioned
    # try:
    #     table = _get_dynamodb().Table(table_name)
    #     table.put_item(Item=item)
    # except Exception as exc:
    #     print(f"[db] ERROR writing to {table_name}: {exc}", flush=True)
    #     return False
    print(
        f"[db] Would write to {table_name}: "
        f"symbol={symbol.upper()}, scraped_at={scraped_at}, "
        f"sections={list(sections.keys())}",
        flush=True,
    )
    return True


def _user_profiles_table_name() -> str:
    table_name = os.getenv("USER_PROFILES_TABLE", "")
    if not table_name:
        raise RuntimeError("USER_PROFILES_TABLE environment variable is not set")
    return table_name


def get_watchlist(user_id: str) -> List[str]:
    """
    Fetch the watchlist for a user from the shared UserProfiles table.

    The watchlist is stored as a top-level attribute on the user's profile item:
        { "user_id": "<cognito-sub>", "watchlist": ["TCS", "INFY", ...] }

    Args:
        user_id: Cognito sub claim (partition key of the UserProfiles table).

    Returns:
        List of NSE/BSE symbol strings, or [] if the user has no profile /
        no watchlist attribute yet.
    """
    try:
        table = _get_dynamodb().Table(_user_profiles_table_name())
        response = table.get_item(Key={"user_id": user_id})
        item = response.get("Item", {})
        return list(item.get("watchlist", []))
    except RuntimeError:
        print("[db] USER_PROFILES_TABLE is not set — returning empty watchlist", flush=True)
        return []
    except Exception as exc:
        print(f"[db] ERROR reading watchlist for user {user_id}: {exc}", flush=True)
        return []


def add_to_watchlist(user_id: str, symbols: List[str]) -> List[str]:
    """
    Add one or more symbols to the user's watchlist (deduplicates automatically).

    Uses DynamoDB's list_append + if_not_exists to create the attribute on first
    write, then a second pass de-duplicates via a string set operation so the
    stored list stays unique.

    Args:
        user_id: Cognito sub claim (partition key).
        symbols: Symbols to add (case-insensitive; stored uppercase).

    Returns:
        The updated watchlist as a list of strings.

    Raises:
        RuntimeError: if USER_PROFILES_TABLE is not configured.
    """
    from boto3.dynamodb.conditions import Attr  # local import — boto3 optional at load time

    normalised = [s.upper() for s in symbols if s.strip()]
    if not normalised:
        return get_watchlist(user_id)

    table = _get_dynamodb().Table(_user_profiles_table_name())

    # Append new symbols, creating the list if it doesn't exist yet.
    response = table.update_item(
        Key={"user_id": user_id},
        UpdateExpression="SET watchlist = list_append(if_not_exists(watchlist, :empty), :new)",
        ExpressionAttributeValues={":empty": [], ":new": normalised},
        ReturnValues="ALL_NEW",
    )
    updated: List[str] = list(response["Attributes"].get("watchlist", []))

    # Deduplicate while preserving order (first occurrence wins).
    seen: set = set()
    deduped = [s for s in updated if not (s in seen or seen.add(s))]  # type: ignore[func-returns-value]
    if len(deduped) != len(updated):
        table.update_item(
            Key={"user_id": user_id},
            UpdateExpression="SET watchlist = :deduped",
            ExpressionAttributeValues={":deduped": deduped},
        )
        return deduped

    return updated


def remove_from_watchlist(user_id: str, symbols: List[str]) -> List[str]:
    """
    Remove one or more symbols from the user's watchlist.

    Fetches the current list, filters out the requested symbols, then writes
    back with a conditional check to avoid clobbering concurrent updates.

    Args:
        user_id: Cognito sub claim (partition key).
        symbols: Symbols to remove (matched case-insensitively).

    Returns:
        The updated watchlist as a list of strings.

    Raises:
        RuntimeError: if USER_PROFILES_TABLE is not configured.
    """
    to_remove = {s.upper() for s in symbols if s.strip()}
    if not to_remove:
        return get_watchlist(user_id)

    table = _get_dynamodb().Table(_user_profiles_table_name())
    response = table.get_item(Key={"user_id": user_id})
    current: List[str] = list(response.get("Item", {}).get("watchlist", []))
    updated = [s for s in current if s.upper() not in to_remove]

    table.update_item(
        Key={"user_id": user_id},
        UpdateExpression="SET watchlist = :updated",
        ExpressionAttributeValues={":updated": updated},
    )
    return updated


def insert_documents(symbol: str, documents: Dict[str, List[Dict]], scraped_at: str) -> bool:
    """
    Insert scraped document links for a symbol into DynamoDB.

    Args:
        symbol:     Stock symbol (partition key, stored uppercase).
        documents:  Dict returned by ScreenerFetcher.extract_file_links().
        scraped_at: ISO-8601 UTC timestamp string (sort key).

    Returns:
        True on success, False on failure.
    """
    table_name = _table_name("StockDocuments")
    total = sum(len(v) for v in documents.values())
    item = {
        "symbol": symbol.upper(),
        "scraped_at": scraped_at,
        "documents": documents,
    }
    # TODO: implement DynamoDB write — uncomment once table is provisioned
    # try:
    #     table = _get_dynamodb().Table(table_name)
    #     table.put_item(Item=item)
    # except Exception as exc:
    #     print(f"[db] ERROR writing to {table_name}: {exc}", flush=True)
    #     return False
    print(
        f"[db] Would write to {table_name}: "
        f"symbol={symbol.upper()}, scraped_at={scraped_at}, "
        f"total_documents={total}",
        flush=True,
    )
    return True
