import time
import datetime
import requests
from hearth.modules.alerts import check_price_alerts
from hearth.gamify.tracker import add_xp, decay_stats
from hearth.gamify.quests import list_quests
from hearth.gamify.backup import run_backup
from hearth.gamify.backup import purge_backups_keep

# After run_backup()
print(purge_backups_keep(5))


last_backup_date = None


def log_wealth(amount):
    if amount <= 0:
        return "⚠️ Invalid amount."
    xp = int(amount / 10)
    return add_xp("Fortuna", xp) + f" 💰 Logged ₹{amount} to Plutus."

def daily_ritual():
    decay_result = decay_stats()
    quest_board = list_quests()
    summary = f"🛡️ Daily Sync\n{decay_result}\n\n{quest_board}"
    return summary

def main():
    print("💰 Plutus Daemon running…")
    while True:
        check_price_alerts()
        today = datetime.date.today()
        global last_backup_date
        if last_backup_date is None or (today - last_backup_date).days >= 7:
            print("📦 Weekly backup starting...")
            print(run_backup())
            last_backup_date = today
        time.sleep(300)  # 5 minutes

if __name__ == "__main__":
    main()
