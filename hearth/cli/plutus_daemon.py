import time
import requests
from hearth.modules.alerts import check_price_alerts

def main():
    print("💰 Plutus Daemon running…")
    while True:
        check_price_alerts()
        time.sleep(300)  # 5 minutes

if __name__ == "__main__":
    main()
