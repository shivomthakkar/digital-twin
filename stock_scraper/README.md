# stock_scraper

CLI script that scrapes financial data for any Indian stock from [Screener.in](https://www.screener.in) and inserts it into DynamoDB.

## What it collects

| Layer | Details |
|---|---|
| **Core ratios** | Market cap, P/E, P/B, ROE, ROCE, margins, debt/equity, growth metrics, shareholding, EPS, book value, sector, exchange codes |
| **Company profile** | Key-value metadata and descriptive text |
| **Section tables** | Profit & Loss, Balance Sheet, Cash Flow, Ratios, Shareholding Pattern (full tabular data) |
| **Document links** | Annual reports, quarterly results, concall transcripts, investor presentations, shareholding patterns, credit ratings, board meeting outcomes |

## Setup

```bash
cd stock_scraper

# Create venv and install dependencies with uv
uv venv && uv pip install -r requirements.txt
```

Copy `.env.example` to `.env` and fill in your AWS credentials / region:

```bash
cp .env.example .env
```

## Usage

```bash
# By symbol
uv run python scraper.py TCS
uv run python scraper.py INFY
uv run python scraper.py RELIANCE

# By company name (Screener resolves it)
uv run python scraper.py "Tata Consultancy"
uv run python scraper.py "Infosys Limited"

# Scrape and print but do NOT write to the database
uv run python scraper.py TCS --dry-run

# Output raw JSON (useful for piping / debugging)
uv run python scraper.py TCS --output json
uv run python scraper.py TCS --output json > tcs.json

# Unknown symbol — exits with a clear error
uv run python scraper.py UNKNOWN_XYZ
# Error: 'UNKNOWN_XYZ' not found on Screener.in
```

## Environment variables

| Variable | Default | Description |
|---|---|---|
| `AWS_REGION` | `ap-south-1` | AWS region for DynamoDB |
| `DYNAMODB_TABLE_PREFIX` | _(empty)_ | Optional prefix prepended to all table names |

### `.env.example`

```ini
AWS_REGION=ap-south-1
DYNAMODB_TABLE_PREFIX=
# AWS credentials (or use IAM role / AWS CLI profile)
# AWS_ACCESS_KEY_ID=
# AWS_SECRET_ACCESS_KEY=
```

## DynamoDB tables

The script writes to three tables (provisioned separately via Terraform):

| Table | PK | SK | Data |
|---|---|---|---|
| `StockFinancials` | `symbol` (S) | `scraped_at` (S, ISO-8601 UTC) | Financial ratios dict |
| `StockSections` | `symbol` (S) | `scraped_at` (S) | P&L / BS / CF tables |
| `StockDocuments` | `symbol` (S) | `scraped_at` (S) | Document links by category |

> **Note:** The `db.py` write calls are currently **stubbed** — they print what _would_ be inserted without actually calling DynamoDB.  
> Uncomment the `boto3` lines in [db.py](db.py) once the tables are provisioned.

## Project structure

```
stock_scraper/
├── scraper.py            # CLI entry point (run this)
├── screener_utility.py   # ScreenerFetcher class — all scraping logic
├── db.py                 # DynamoDB stub (insert_financial_data, insert_documents, …)
├── pyproject.toml        # Project metadata & dependencies
├── requirements.txt      # pip-compatible dependency list
└── README.md
```
