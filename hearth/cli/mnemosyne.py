import time
from apscheduler.schedulers.blocking import BlockingScheduler
from hearth.modules.logger import notify

def reminder():
    notify("⏰ Stretch! Time for a gaming break or a quick walk.")

def main():
    scheduler = BlockingScheduler()
    scheduler.add_job(reminder, 'interval', minutes=60)
    print("🎮 Mnemosyne running…")
    scheduler.start()

if __name__ == "__main__":
    main()
