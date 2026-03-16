"""
FastAPI server for stock_scraper.

Endpoints:
  GET    /health              — liveness check
  GET    /scrape/{query}      — scrape a stock, insert into DB, return all data
                               ?dry=true  → skip database writes (preview mode)
  GET    /watchlist           — scrape & summarise all stocks in the user's watchlist
  POST   /watchlist           — add symbols to the user's watchlist (bulk)
  DELETE /watchlist           — remove symbols from the user's watchlist (bulk)
"""

import os
from datetime import datetime, timezone
from typing import List

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, field_validator

import db
from auth import get_current_user
from screener_utility import ScreenerFetcher

load_dotenv()

app = FastAPI(
    title="Stock Scraper API",
    description="Scrapes financial data from Screener.in and stores it in DynamoDB",
    version="0.1.0",
)

origins = os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=False,
    allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

_fetcher = ScreenerFetcher()


def _scrape(query: str) -> dict:
    """Core scrape logic shared by all endpoints."""
    company_url = _fetcher.search_company(query)
    if not company_url:
        raise HTTPException(status_code=404, detail=f"'{query}' not found on Screener.in")

    soup = _fetcher.get_company_page(company_url)
    if not soup:
        raise HTTPException(
            status_code=502, detail=f"Could not fetch Screener.in page for {company_url}"
        )

    financial_data = _fetcher.extract_financial_data(soup)
    profile = _fetcher.extract_company_profile(soup)
    sections = _fetcher.extract_section_tables(soup)
    documents = _fetcher.extract_file_links(company_url)

    scraped_at = datetime.now(timezone.utc).isoformat()
    symbol = (
        financial_data.get("nse_code")
        or financial_data.get("bse_code")
        or query.upper()
    )

    return {
        "symbol": symbol,
        "scraped_at": scraped_at,
        "company_url": f"{_fetcher.BASE_URL}{company_url}",
        "financial_data": financial_data,
        "profile": profile,
        "sections": sections,
        "documents": documents,
    }


# Keys from financial_data surfaced in the watchlist summary.
_WATCHLIST_FINANCIAL_KEYS = [
    "company_name",
    "nse_code",
    "bse_code",
    "sector",
    "current_price",
    "market_cap",
    "stock_pe",
    "pe_ratio",
    "52_week_high",
    "52_week_low",
    "roe",
    "roce",
    "opm",
    "npm",
    "debt_to_equity",
    "dividend_yield",
    "eps",
    "book_value",
    "promoter_holding",
]


def _summarise(payload: dict) -> dict:
    """Return a compact watchlist summary from a full scrape payload."""
    fd = payload["financial_data"]
    return {
        "symbol": payload["symbol"],
        "scraped_at": payload["scraped_at"],
        "company_url": payload["company_url"],
        **fd
        # **{k: fd[k] for k in _WATCHLIST_FINANCIAL_KEYS if k in fd},
    }


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/scrape/{query}")
def scrape(
    query: str,
    dry_run: bool = Query(False, alias="dry", description="Skip database writes"),
):
    """
    Scrape financial data for a stock symbol or company name.

    - **query**: NSE/BSE symbol (e.g. `TCS`) or company name (e.g. `Tata Consultancy`)
    - **dry**: set `?dry=true` to preview without writing to DynamoDB
    """
    payload = _scrape(query)

    if not dry_run:
        db.insert_financial_data(payload["symbol"], payload["financial_data"], payload["scraped_at"])
        db.insert_section_tables(payload["symbol"], payload["sections"], payload["scraped_at"])
        db.insert_documents(payload["symbol"], payload["documents"], payload["scraped_at"])

    return payload


@app.get("/watchlist")
def get_watchlist(user_id: str = Depends(get_current_user)):
    """
    Scrape and return a compact summary for every stock in the authenticated
    user's watchlist.

    The watchlist is read from the `watchlist` attribute (List[str] of NSE/BSE
    symbols) on the user's record in the shared UserProfiles DynamoDB table.
    Each symbol is scraped sequentially; failures are collected in `errors`
    rather than aborting the entire request.

    Response shape:
        {
            "user_id": "...",
            "symbols": ["TCS", "INFY"],
            "results": [ { symbol, scraped_at, company_url, current_price, ... } ],
            "errors":  [ { "symbol": "X", "detail": "..." } ]
        }
    """
    symbols: list[str] = db.get_watchlist(user_id)

    results = []
    errors = []

    for symbol in symbols:
        try:
            payload = _scrape(symbol)
            results.append(_summarise(payload))
        except HTTPException as exc:
            errors.append({"symbol": symbol, "detail": exc.detail})
        except Exception as exc:
            errors.append({"symbol": symbol, "detail": str(exc)})

    return {
        "user_id": user_id,
        "symbols": symbols,
        "results": results,
        "errors": errors,
    }


class WatchlistRequest(BaseModel):
    symbols: List[str]

    @field_validator("symbols")
    @classmethod
    def symbols_non_empty(cls, v: List[str]) -> List[str]:
        cleaned = [s.strip().upper() for s in v if s.strip()]
        if not cleaned:
            raise ValueError("symbols must contain at least one non-empty value")
        return cleaned


@app.post("/watchlist", status_code=200)
def add_to_watchlist(
    body: WatchlistRequest,
    user_id: str = Depends(get_current_user),
):
    """
    Add one or more symbols to the authenticated user's watchlist.

    Duplicate symbols are ignored. Symbols are stored uppercase.

    Request body: `{ "symbols": ["TCS", "INFY"] }`

    Returns the full updated watchlist.
    """
    try:
        updated = db.add_to_watchlist(user_id, body.symbols)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    return {"user_id": user_id, "watchlist": updated}


@app.delete("/watchlist", status_code=200)
def remove_from_watchlist(
    body: WatchlistRequest,
    user_id: str = Depends(get_current_user),
):
    """
    Remove one or more symbols from the authenticated user's watchlist.

    Symbols not present in the watchlist are silently ignored. Each symbol
    is removed individually.

    Request body: `{ "symbols": ["TCS", "INFY"] }`

    Returns the full updated watchlist.
    """
    try:
        # Remove each symbol individually
        for symbol in body.symbols:
            db.remove_from_watchlist(user_id, [symbol])
        # Fetch and return the full updated watchlist
        updated = db.get_watchlist(user_id)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    return {"user_id": user_id, "watchlist": updated}
