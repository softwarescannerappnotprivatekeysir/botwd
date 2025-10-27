import os, asyncio, random, string, time
import httpx
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")  # ví dụ: 123456:ABC...
CHAT_ID   = os.getenv("TELEGRAM_CHAT_ID")    # ví dụ: @your_channel hoặc -1001234567890

# Map Symbol -> CoinGecko ID
TOKEN_MAP = {
    "BTC": "bitcoin",
    "ETH": "ethereum",
    "LTC": "litecoin",
    "BNB": "binancecoin",
    "SOL": "solana",
    "TRX": "tron",
    "USDT": "tether",
    "USDC": "usd-coin",
}
TOKEN_LIST = list(TOKEN_MAP.keys())

TG_API = f"https://api.telegram.org/bot{BOT_TOKEN}"
CG_SIMPLE_PRICE = "https://api.coingecko.com/api/v3/simple/price"

def rand_user_id() -> str:
    return f"#{random.randint(10_000_000, 99_999_999)}"

def rand_tx_hash(n: int = 16) -> str:
    # 16 ký tự hex in hoa
    return ''.join(random.choices("0123456789ABCDEF", k=n))

async def fetch_price_usd(client: httpx.AsyncClient, cg_id: str) -> float:
    # Lấy giá USD cho 1 token
    params = {"ids": cg_id, "vs_currencies": "usd"}
    r = await client.get(CG_SIMPLE_PRICE, params=params, timeout=20)
    r.raise_for_status()
    data = r.json()
    price = data.get(cg_id, {}).get("usd")
    if not price:
        raise RuntimeError(f"Price not found for {cg_id}")
    return float(price)

def format_amount_token(usd_amount: float, price_usd: float, symbol: str) -> str:
    # Số lượng token = USD / price
    qty = usd_amount / price_usd if price_usd > 0 else 0.0
    # Quy tắc hiển thị: coin lớn 8 chữ số thập phân, stable 2–4
    if symbol in ("USDT", "USDC"):
        return f"{qty:.2f} {symbol}"
    if symbol in ("BTC", "ETH", "SOL"):
        return f"{qty:.8f} {symbol}"
    return f"{qty:.6f} {symbol}"

def build_message(user_id: str, usd_amount: float, token_str: str, txh: str) -> str:
    return (
        "WITHDRAW SUCCESSFULLY✔️\n"
        f"👤ID: {user_id}\n"
        f"💰Amount: ${usd_amount:,.2f}\n"
        f"📤Convert: {token_str}\n"
        f"#️⃣Transaction Hash: {txh}"
    )

async def send_message(client: httpx.AsyncClient, text: str):
    url = f"{TG_API}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": text,
        "disable_web_page_preview": True,
        "parse_mode": "HTML",  # text thường, không cần markdown đặc biệt
    }
    r = await client.post(url, json=payload, timeout=20)
    r.raise_for_status()
    return r.json()

async def main_loop():
    if not BOT_TOKEN or not CHAT_ID:
        raise SystemExit("Missing TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID in environment.")

    async with httpx.AsyncClient() as client:
        while True:
            try:
                # 1) Random USD 10–5000
                usd_amount = float(random.randint(10, 5000))

                # 2) Chọn token ngẫu nhiên + lấy giá
                symbol = random.choice(TOKEN_LIST)
                cg_id = TOKEN_MAP[symbol]
                price_usd = await fetch_price_usd(client, cg_id)

                token_str = format_amount_token(usd_amount, price_usd, symbol)

                # 3) Build message
                user_id = rand_user_id()
                txh = rand_tx_hash(16)
                msg = build_message(user_id, usd_amount, token_str, txh)

                # 4) Gửi
                await send_message(client, msg)

            except Exception as e:
                # Ghi log lỗi (Railway logs)
                print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Error: {e}", flush=True)

            # 5) Đợi 1–2 phút
            delay = random.randint(60, 120)
            await asyncio.sleep(delay)

if __name__ == "__main__":
    try:
        asyncio.run(main_loop())
    except KeyboardInterrupt:
        pass
