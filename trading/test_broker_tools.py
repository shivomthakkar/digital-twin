#!/usr/bin/env python3
"""
Test script to demonstrate Dhan Broker MCP Server capabilities
"""

import json

print("=" * 60)
print("🏦 Dhan Broker MCP Server - Tool Examples")
print("=" * 60)

print("\n📊 Available Tools:\n")

tools = [
    {
        "name": "list_holdings",
        "description": "Get all current holdings with P&L",
        "example_output": {
            "holdings": [
                {
                    "symbol": "RELIANCE",
                    "quantity": 10,
                    "avg_cost": 2500.00,
                    "current_price": 2650.00,
                    "pnl": 1500.00
                }
            ],
            "summary": {
                "total_holdings": 1,
                "total_value": 26500.00,
                "total_pnl": 1500.00
            }
        }
    },
    {
        "name": "get_open_positions",
        "description": "View all open trading positions",
        "example_output": {
            "positions": [
                {
                    "symbol": "NIFTY24DEC24500CE",
                    "product_type": "INTRADAY",
                    "quantity": 50,
                    "unrealized_profit": 2500.00
                }
            ],
            "summary": {
                "total_positions": 1,
                "total_unrealized_pnl": 2500.00
            }
        }
    },
    {
        "name": "get_pnl",
        "description": "Calculate P&L for specified period",
        "parameters": {"period": "week | 2weeks | month"},
        "example_output": {
            "period": "1 Week",
            "realized_pnl": {
                "gross_pnl": 5000.00,
                "total_charges": 150.00,
                "net_pnl": 4850.00
            },
            "unrealized_pnl": 2500.00,
            "total_pnl": 7350.00
        }
    },
    {
        "name": "get_fund_details",
        "description": "Check account balances and margins",
        "example_output": {
            "balances": {
                "available_balance": 100000.00,
                "blocked_amount": 5000.00
            },
            "margins": {
                "total_margin": 200000.00,
                "utilized_margin": 50000.00,
                "available_margin": 150000.00,
                "margin_utilization_percent": 25.0
            }
        }
    }
]

for i, tool in enumerate(tools, 1):
    print(f"{i}. {tool['name']}")
    print(f"   📝 {tool['description']}")
    if 'parameters' in tool:
        print(f"   ⚙️  Parameters: {tool['parameters']}")
    print(f"   📊 Example Output:")
    print(f"   {json.dumps(tool['example_output'], indent=6)[:200]}...")
    print()

print("=" * 60)
print("\n⚡ How to Use:\n")
print("1. Set up your Dhan API credentials in .env file")
print("2. Run the server: python3 server.py")
print("3. Connect via MCP client (Claude Desktop, etc.)")
print("4. Use the tools to interact with your Dhan account")

print("\n🔐 Security Notes:")
print("• Keep your API credentials secure")
print("• Never commit .env file to version control")
print("• Use read-only API access if available for viewing data")

print("\n=" * 60)