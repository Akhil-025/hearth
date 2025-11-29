import json
import os
import requests
from plyer import notification  # pip install plyer
import yfinance as yf


ALERTS_FILE = "hearth/data/price_alerts.json"
DEFAULT_ALERTS = {"crypto": {}, "stocks": {}}

def load_alerts():
    if not os.path.exists(ALERTS_FILE):
        return DEFAULT_ALERTS.copy()
    try:
        with open(ALERTS_FILE, "r") as f:
            return json.load(f)
    except json.JSONDecodeError:
        return DEFAULT_ALERTS.copy()

def save_alerts(alerts):
    os.makedirs(os.path.dirname(ALERTS_FILE), exist_ok=True)
    with open(ALERTS_FILE, "w") as f:
        json.dump(alerts, f, indent=2)

def notify(title, message):
    try:
        notification.notify(title=title, message=message, timeout=5)
    except Exception as e:
        print(f"🔕 Notification error: {e}")

def check_price_alerts():
    alerts = load_alerts()
    triggered = []

    # ✅ Crypto alerts via CoinGecko
    for coin, threshold in alerts["crypto"].items():
        url = f"https://api.coingecko.com/api/v3/simple/price?ids={coin}&vs_currencies=inr"
        try:
            response = requests.get(url)
            price = response.json()[coin]["inr"]
            if price >= threshold:
                msg = f"{coin.title()} hit ₹{price} (≥ ₹{threshold})"
                print(f"🚨 {msg}")
                notify("Crypto Alert", msg)
                triggered.append(("crypto", coin))
            else:
                print(f"💤 {coin.title()} at ₹{price:,} < ₹{threshold:,}")
        except Exception as e:
            print(f"⚠️ Failed to check {coin}: {e}")

    # ✅ Stocks via Yahoo Finance
    try:
        import yfinance as yf
        for stock, threshold in alerts["stocks"].items():
            ticker = yf.Ticker(stock)
            price = ticker.history(period="1d")["Close"].iloc[-1]
            if price >= threshold:
                msg = f"{stock.upper()} hit ₹{price:.2f} (≥ {threshold})"
                print(f"📈 {msg}")
                notify("Stock Alert", msg)
                triggered.append(("stocks", stock))
            else:
                print(f"💤 {stock.upper()} at ₹{price:.2f} < ₹{threshold}")
    except ImportError:
        print("⚠️ Install yfinance for stock support: pip install yfinance")
    except Exception as e:
        print(f"⚠️ Stock check failed: {e}")

    # 🔁 Optional quest hook
    if triggered:
        try:
            from hearth.gamify.quests import trigger_price_alert_quest
            trigger_price_alert_quest(triggered)
        except ImportError:
            print("🎯 Quest integration skipped (not found)")

def add_alert(category, symbol, threshold):
    alerts = load_alerts()
    if category not in alerts:
        print(f"❌ Invalid category. Use 'crypto' or 'stocks'")
        return
    alerts[category][symbol] = threshold
    save_alerts(alerts)
    print(f"✅ Added alert: {category}:{symbol} ≥ ₹{threshold}")

def list_alerts():
    alerts = load_alerts()
    for cat, entries in alerts.items():
        print(f"\n📂 {cat.title()} Alerts:")
        for symbol, threshold in entries.items():
            print(f" - {symbol.upper()}: ≥ ₹{threshold}")

def clear_alerts():
    save_alerts(DEFAULT_ALERTS)
    print("🧹 All alerts cleared.")

def show_prices():
    alerts = load_alerts()
    print("📡 Fetching current prices…\n")

    for category in ["crypto", "stocks"]:
        for symbol, threshold in alerts[category].items():
            try:
                if category == "crypto":
                    url = f"https://api.coingecko.com/api/v3/simple/price?ids={symbol}&vs_currencies=inr"
                    response = requests.get(url, timeout=10)
                    response.raise_for_status()
                    price = response.json()[symbol]["inr"]
                    print(f"🪙 {symbol.title():<15} ₹{price:,}")
                elif category == "stocks":
                    stock = yf.Ticker(symbol)
                    price = stock.history(period="1d")["Close"].iloc[-1]
                    history = stock.history(period="2d")["Close"]
                    if len(history) >= 2:
                        change = (history.iloc[-1] - history.iloc[-2]) / history.iloc[-2] * 100
                        print(f"📈 {symbol.upper():<15} ₹{price:.2f} ({change:+.2f}%)")
                    else:
                        print(f"📈 {symbol.upper():<15} ₹{price:.2f}")
            except Exception as e:
                print(f"⚠️ Failed to fetch price for {symbol} ({category}): {e}")
