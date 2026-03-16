# Dhan Trading Operations FastAPI Server

This server exposes trading operations (holdings, positions, P&L, funds) as RESTful FastAPI endpoints.

## Endpoints

- `GET /holdings` — List all holdings in the portfolio
- `GET /positions` — List all open positions
- `GET /pnl?period=week` — Get P&L for a specified period (`week`, `2weeks`, or `month`)
- `GET /funds` — Get account fund details and margins

## Prerequisites

1. Dhan trading account
2. Dhan API credentials (Client ID and Access Token)
  - Get them from: https://dhanhq.co/

## Installation

```bash
pip install -r requirements.txt
```

## Configuration

1. Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```

2. Add your Dhan API credentials to `.env`:
```
DHAN_CLIENT_ID=your_client_id
DHAN_ACCESS_TOKEN=your_access_token
```

## Running the Server

```bash
uvicorn server:app --reload
```

## API Documentation

Once running, access the interactive API docs at [http://localhost:8000/docs](http://localhost:8000/docs)

## Notes
- This server no longer uses MCP, Lambda, or Terraform. All such code and dependencies have been removed.
- For authentication, integrate Cognito or another method as needed.
{
  "mcpServers": {
    "minimal-server": {
      "command": "python3",
      "args": ["/path/to/server.py"]
    }
  }
}
```

### Example Tool Calls

1. List all holdings:
```json
{
  "tool": "list_holdings",
  "arguments": {}
}
```

2. Get open positions:
```json
{
  "tool": "get_open_positions",
  "arguments": {}
}
```

3. Get P&L for different periods:
```json
{
  "tool": "get_pnl",
  "arguments": {
    "period": "week"  // Options: "week", "2weeks", "month"
  }
}
```

4. Check fund details:
```json
{
  "tool": "get_fund_details",
  "arguments": {}
}
```

## Server Structure

- `server.py` - Main server implementation
- `requirements.txt` - Python dependencies
- `package.json` - MCP client integration metadata
- `pyproject.toml` - Python project configuration

## Development

The server uses:
- Python 3.8+
- MCP SDK for Python
- AsyncIO for asynchronous operations
- JSON-RPC for communication via stdio