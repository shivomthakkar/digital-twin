
# FastAPI refactor
from fastapi import Depends, FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from dhanhq import dhanhq
from dotenv import load_dotenv
from datetime import datetime, timedelta
from pydantic import BaseModel
import os

from auth import (
    generate_dhan_token,
    get_current_broker,
    get_current_user,
    get_token,
    renew_dhan_token,
    store_token,
)

load_dotenv()

app = FastAPI(title="Dhan Trading Operations API")

# Configure CORS
origins = os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Auth endpoints
# ---------------------------------------------------------------------------

class GenerateTokenRequest(BaseModel):
    dhan_client_id: str
    pin: str
    totp: str


@app.post("/auth/generate-token")
def auth_generate_token(
    body: GenerateTokenRequest,
    user_id: str = Depends(get_current_user),
):
    """Generate a new Dhan access token using PIN + TOTP and store it in DynamoDB."""
    token_data = generate_dhan_token(body.dhan_client_id, body.pin, body.totp)
    store_token(user_id, token_data)
    return {
        "message": "Token generated and stored successfully",
        "dhan_client_id": token_data.get("dhanClientId"),
        "expiry_time": token_data.get("expiryTime"),
    }


@app.post("/auth/renew-token")
def auth_renew_token(user_id: str = Depends(get_current_user)):
    """Renew the existing Dhan access token and update it in DynamoDB."""
    record = get_token(user_id)
    token_data = renew_dhan_token(record["client_id"], record["access_token"])
    store_token(user_id, token_data)
    return {
        "message": "Token renewed successfully",
        "dhan_client_id": token_data.get("dhanClientId"),
        "expiry_time": token_data.get("expiryTime"),
    }


# ---------------------------------------------------------------------------
# Trading endpoints
# ---------------------------------------------------------------------------

@app.get("/holdings")
def get_holdings(broker: dhanhq = Depends(get_current_broker)):
    """Get current holdings from Dhan account"""
    try:
        holdings = broker.get_holdings()
        if not holdings or holdings.get('status') == 'failure':
            remarks = holdings.get('remarks', {}) if holdings else {}
            return JSONResponse({"error": remarks.get('error_message', 'Failed to fetch holdings.')}, status_code=401 if remarks.get('error_code') == 'DH-901' else 502)
        if 'data' not in holdings:
            return JSONResponse({"error": "No holdings found in the portfolio."}, status_code=404)
        
        print("holdings:", holdings)
        holdings_list = []
        total_value = 0
        total_pnl = 0
        for holding in holdings.get('data', []):
            stock_info = {
                "symbol": holding.get('tradingSymbol', 'N/A'),
                "exchange": holding.get('exchangeSegment', 'N/A'),
                "quantity": holding.get('totalQty', 0),
                "avg_cost": holding.get('avgCostPrice', 0),
                "current_price": holding.get('lastTradedPrice', 0),
                "pnl": holding.get('realizedProfit', 0) + holding.get('unrealizedProfit', 0),
                "day_change": holding.get('dayChange', 0),
                "day_change_percent": holding.get('dayChangePerc', 0)
            }
            holdings_list.append(stock_info)
            total_value += stock_info['quantity'] * stock_info['current_price']
            total_pnl += stock_info['pnl']
        result = {
            "holdings": holdings_list,
            "summary": {
                "total_holdings": len(holdings_list),
                "total_value": round(total_value, 2),
                "total_pnl": round(total_pnl, 2),
                "last_updated": datetime.now().isoformat()
            }
        }
        return result
    except Exception as e:
        return JSONResponse({"error": f"Error fetching holdings: {str(e)}"}, status_code=500)

@app.get("/positions")
def get_positions(broker: dhanhq = Depends(get_current_broker)):
    """Get current open positions from Dhan account"""
    try:
        positions = broker.get_positions()
        if not positions or positions.get('status') == 'failure':
            remarks = positions.get('remarks', {}) if positions else {}
            return JSONResponse({"error": remarks.get('error_message', 'Failed to fetch positions.')}, status_code=401 if remarks.get('error_code') == 'DH-901' else 502)
        if 'data' not in positions:
            return JSONResponse({"error": "No open positions found."}, status_code=404)
        positions_list = []
        total_unrealized_pnl = 0
        for position in positions.get('data', []):
            pos_info = {
                "symbol": position.get('tradingSymbol', 'N/A'),
                "exchange": position.get('exchangeSegment', 'N/A'),
                "product_type": position.get('productType', 'N/A'),
                "position_type": position.get('positionType', 'N/A'),
                "quantity": position.get('netQty', 0),
                "buy_qty": position.get('buyQty', 0),
                "sell_qty": position.get('sellQty', 0),
                "buy_avg": position.get('buyAvg', 0),
                "sell_avg": position.get('sellAvg', 0),
                "realized_profit": position.get('realizedProfit', 0),
                "unrealized_profit": position.get('unrealizedProfit', 0),
                "day_pnl": position.get('dayProfit', 0)
            }
            positions_list.append(pos_info)
            total_unrealized_pnl += pos_info['unrealized_profit']
        result = {
            "positions": positions_list,
            "summary": {
                "total_positions": len(positions_list),
                "total_unrealized_pnl": round(total_unrealized_pnl, 2),
                "last_updated": datetime.now().isoformat()
            }
        }
        return result
    except Exception as e:
        return JSONResponse({"error": f"Error fetching positions: {str(e)}"}, status_code=500)

@app.get("/pnl")
def get_pnl(
    period: str = Query("week", description="Time period: week, 2weeks, or month"),
    broker: dhanhq = Depends(get_current_broker),
):
    """Get profit and loss for a specified period"""
    try:
        end_date = datetime.now()
        if period.lower() == "week":
            start_date = end_date - timedelta(days=7)
            period_label = "1 Week"
        elif period.lower() == "2weeks":
            start_date = end_date - timedelta(days=14)
            period_label = "2 Weeks"
        elif period.lower() == "month":
            start_date = end_date - timedelta(days=30)
            period_label = "1 Month"
        else:
            return JSONResponse({"error": f"Invalid period '{period}'. Please use 'week', '2weeks', or 'month'"}, status_code=400)
        from_date = start_date.strftime("%Y-%m-%d")
        to_date = end_date.strftime("%Y-%m-%d")
        trade_history = broker.get_trade_history(
            from_date=from_date,
            to_date=to_date,
            page_number=0
        )
        if not trade_history or trade_history.get('status') == 'failure':
            remarks = trade_history.get('remarks', {}) if trade_history else {}
            return JSONResponse({"error": remarks.get('error_message', 'Failed to fetch trade history.')}, status_code=401 if remarks.get('error_code') == 'DH-901' else 502)
        if 'data' not in trade_history:
            return JSONResponse({"error": f"No trades found for the period: {period_label}"}, status_code=404)
        total_buy_value = 0
        total_sell_value = 0
        total_charges = 0
        trades_count = 0
        for trade in trade_history.get('data', []):
            trade_info = {
                "date": trade.get('tradingDate', 'N/A'),
                "symbol": trade.get('tradingSymbol', 'N/A'),
                "type": trade.get('transactionType', 'N/A'),
                "quantity": trade.get('quantity', 0),
                "price": trade.get('tradedPrice', 0),
                "value": trade.get('tradedValue', 0),
                "charges": trade.get('brokerage', 0) + trade.get('exchangeCharges', 0) +
                          trade.get('otherCharges', 0) + trade.get('stampDuty', 0) +
                          trade.get('sebiTurnoverFee', 0) + trade.get('serviceTax', 0)
            }
            trades_count += 1
            if trade_info['type'].upper() == 'BUY':
                total_buy_value += trade_info['value']
            else:
                total_sell_value += trade_info['value']
            total_charges += trade_info['charges']
        gross_pnl = total_sell_value - total_buy_value
        net_pnl = gross_pnl - total_charges
        positions = broker.get_positions()
        unrealized_pnl = 0
        if positions and positions.get('status') != 'failure' and 'data' in positions:
            for position in positions.get('data', []):
                unrealized_pnl += position.get('unrealizedProfit', 0)
        result = {
            "period": period_label,
            "date_range": {
                "from": from_date,
                "to": to_date
            },
            "realized_pnl": {
                "gross_pnl": round(gross_pnl, 2),
                "total_charges": round(total_charges, 2),
                "net_pnl": round(net_pnl, 2)
            },
            "unrealized_pnl": round(unrealized_pnl, 2),
            "total_pnl": round(net_pnl + unrealized_pnl, 2),
            "statistics": {
                "total_trades": trades_count,
                "total_buy_value": round(total_buy_value, 2),
                "total_sell_value": round(total_sell_value, 2)
            },
            "last_updated": datetime.now().isoformat()
        }
        return result
    except Exception as e:
        return JSONResponse({"error": f"Error calculating P&L: {str(e)}"}, status_code=500)

@app.get("/funds")
def get_funds(broker: dhanhq = Depends(get_current_broker)):
    """Get current fund details and margins from Dhan account"""
    try:
        fund_limits = broker.get_fund_limits()
        if not fund_limits or fund_limits.get('status') == 'failure':
            remarks = fund_limits.get('remarks', {}) if fund_limits else {}
            return JSONResponse({"error": remarks.get('error_message', 'Failed to fetch fund details.')}, status_code=401 if remarks.get('error_code') == 'DH-901' else 502)
        if 'data' not in fund_limits:
            return JSONResponse({"error": "Unable to fetch fund details."}, status_code=404)
        data = fund_limits.get('data', {})
        result = {
            "balances": {
                "available_balance": data.get('availabelBalance', 0),
                "blocked_amount": data.get('blockedPayoutAmount', 0),
                "collateral_amount": data.get('collateralAmount', 0),
                "unsettled_credits": data.get('unsettledTradingAmount', 0)
            },
            "margins": {
                "total_margin": data.get('sodLimit', 0),
                "utilized_margin": data.get('marginUtilized', 0),
                "available_margin": data.get('marginAvailable', 0),
                "margin_utilization_percent": round(
                    (data.get('marginUtilized', 0) / data.get('sodLimit', 1)) * 100, 2
                ) if data.get('sodLimit', 0) > 0 else 0
            },
            "last_updated": datetime.now().isoformat()
        }
        return result
    except Exception as e:
        return JSONResponse({"error": f"Error fetching fund details: {str(e)}"}, status_code=500)

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)