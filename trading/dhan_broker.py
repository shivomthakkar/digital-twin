from dhanhq import dhanhq
from dotenv import load_dotenv
import os

load_dotenv()
broker = dhanhq(os.getenv("DHAN_CLIENT_ID"), os.getenv("DHAN_ACCESS_TOKEN"))

if __name__ == "__main__":
    print(broker.get_holdings())