#!/usr/bin/env python3
"""
stock_scraper — CLI entry point

Scrapes financial data for any stock from Screener.in and inserts it into DynamoDB.

Usage:
    python scraper.py <symbol_or_name> [--dry-run] [--output {text,json}]

Examples:
    python scraper.py TCS
    python scraper.py "Tata Consultancy" --output json
    python scraper.py INFY --dry-run
"""

import argparse
import json
import sys
from datetime import datetime, timezone

from dotenv import load_dotenv

import db
from screener_utility import ScreenerFetcher

load_dotenv()


# ---------------------------------------------------------------------------
# Argument parsing
# ---------------------------------------------------------------------------

def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Scrape financial data for a stock from Screener.in and insert into DynamoDB",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "query",
        help="Stock symbol (e.g. TCS) or company name (e.g. 'Tata Consultancy')",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Scrape and print data without writing to the database",
    )
    parser.add_argument(
        "--output",
        choices=["text", "json"],
        default="text",
        help="Output format (default: text)",
    )
    return parser.parse_args()


# ---------------------------------------------------------------------------
# Text formatting
# ---------------------------------------------------------------------------

_RATIO_MAP = [
    # (data_key,            display_label,          prefix, suffix)
    ("market_cap",          "Market Cap",            "₹",    " Cr"),
    ("current_price",       "Current Price",         "₹",    ""),
    ("52_week_high",        "52-Week High",          "₹",    ""),
    ("52_week_low",         "52-Week Low",           "₹",    ""),
    ("stock_pe",            "Stock P/E",             "",     ""),
    ("pe_ratio",            "P/E Ratio",             "",     ""),
    ("pb_ratio",            "P/B Ratio",             "",     ""),
    ("roe",                 "ROE",                   "",     "%"),
    ("roce",                "ROCE",                  "",     "%"),
    ("opm",                 "Operating Margin",      "",     "%"),
    ("npm",                 "Net Profit Margin",     "",     "%"),
    ("debt_to_equity",      "Debt/Equity",           "",     ""),
    ("sales_growth_3yr",    "Sales Growth (3Y)",     "",     "%"),
    ("profit_growth_3yr",   "Profit Growth (3Y)",    "",     "%"),
    ("promoter_holding",    "Promoter Holding",      "",     "%"),
    ("eps",                 "EPS",                   "₹",    ""),
    ("book_value",          "Book Value",            "₹",    ""),
    ("dividend_yield",      "Dividend Yield",        "",     "%"),
    ("sector",              "Sector",                "",     ""),
    ("bse_code",            "BSE Code",              "",     ""),
    ("nse_code",            "NSE Code",              "",     ""),
]

_DOC_LABELS = {
    "annual_reports":         "Annual Reports",
    "quarterly_results":      "Quarterly Results",
    "concall_transcripts":    "Concall Transcripts",
    "investor_presentations": "Investor Presentations",
    "shareholding_patterns":  "Shareholding Patterns",
    "corporate_announcements":"Corporate Announcements",
    "credit_ratings":         "Credit Ratings",
    "board_meetings":         "Board Meetings",
    "other_documents":        "Other Documents",
}


def _format_text(
    query: str,
    company_url: str,
    financial_data: dict,
    profile: dict,
    sections: dict,
    documents: dict,
    fetcher: ScreenerFetcher,
) -> str:
    lines = []
    name = financial_data.get("company_name") or query

    lines.append(f"\n{'='*62}")
    lines.append(f"  {name}")
    lines.append(f"  {fetcher.BASE_URL}{company_url}")
    lines.append(f"{'='*62}\n")

    # Core ratios
    lines.append("── Core Financials " + "─" * 44)
    found = False
    for key, label, prefix, suffix in _RATIO_MAP:
        if financial_data.get(key):
            lines.append(f"  {label:<26} {prefix}{financial_data[key]}{suffix}")
            found = True
    if not found:
        lines.append("  (no ratio data extracted)")

    # Company profile
    if profile:
        lines.append("\n── Company Profile " + "─" * 44)
        for k, v in profile.items():
            if k == "description":
                excerpt = v[:500] + ("…" if len(v) > 500 else "")
                lines.append(f"\n  About: {excerpt}")
            else:
                lines.append(f"  {k:<26} {v}")

    # Section tables summary
    if sections:
        lines.append("\n── Financial Sections " + "─" * 41)
        for section_id, tables in sections.items():
            label = section_id.replace("-", " ").title()
            row_count = sum(len(t.get("rows", [])) for t in tables)
            lines.append(f"  {label:<26} {len(tables)} table(s), {row_count} data rows")

    # Documents summary
    if documents:
        lines.append("\n── Documents " + "─" * 49)
        for key, label in _DOC_LABELS.items():
            docs = documents.get(key, [])
            if not docs:
                continue
            lines.append(f"  {label:<28} {len(docs)} file(s)")
            for doc in docs[:3]:
                lines.append(f"    • {doc['title'][:60]}")
                lines.append(f"      {doc['url']}")

    lines.append("")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    args = _parse_args()
    fetcher = ScreenerFetcher()

    # 1. Resolve symbol / company name via Screener search API
    print(f"Searching Screener.in for: {args.query!r}", file=sys.stderr)
    company_url = fetcher.search_company(args.query)
    if not company_url:
        print(f"Error: '{args.query}' not found on Screener.in", file=sys.stderr)
        sys.exit(1)

    print(f"Found: {fetcher.BASE_URL}{company_url}", file=sys.stderr)

    # 2. Fetch and parse page
    soup = fetcher.get_company_page(company_url)
    if not soup:
        print(f"Error: Could not fetch page for {company_url}", file=sys.stderr)
        sys.exit(1)

    # 3. Extract all data layers
    print("Extracting financial ratios…", file=sys.stderr)
    financial_data = fetcher.extract_financial_data(soup)

    print("Extracting company profile…", file=sys.stderr)
    profile = fetcher.extract_company_profile(soup)

    print("Extracting section tables (P&L, balance sheet, cash flow)…", file=sys.stderr)
    sections = fetcher.extract_section_tables(soup)

    print("Extracting document links…", file=sys.stderr)
    documents = fetcher.extract_file_links(company_url)

    scraped_at = datetime.now(timezone.utc).isoformat()

    # Prefer the exchange symbol as the DB partition key; fall back to the query input
    symbol = (
        financial_data.get("nse_code")
        or financial_data.get("bse_code")
        or args.query.upper()
    )

    # 4. Print output
    if args.output == "json":
        output = {
            "symbol": symbol,
            "scraped_at": scraped_at,
            "company_url": f"{fetcher.BASE_URL}{company_url}",
            "financial_data": financial_data,
            "profile": profile,
            "sections": sections,
            "documents": documents,
        }
        print(json.dumps(output, indent=2, ensure_ascii=False))
    else:
        print(_format_text(args.query, company_url, financial_data, profile, sections, documents, fetcher))

    # 5. Write to database (skipped when --dry-run)
    if args.dry_run:
        print("\n[dry-run] Skipping database writes.", file=sys.stderr)
    else:
        print("Inserting into database…", file=sys.stderr)
        db.insert_financial_data(symbol, financial_data, scraped_at)
        db.insert_section_tables(symbol, sections, scraped_at)
        db.insert_documents(symbol, documents, scraped_at)
        print("Done.", file=sys.stderr)


if __name__ == "__main__":
    main()
