import shutil
import os
import time

def backup():
    src = os.path.expandvars(r"%APPDATA%\.hearth")
    dst = f"{src}_backup_{int(time.time())}.zip"
    shutil.make_archive(dst.replace(".zip", ""), 'zip', src)
    print(f"🗂️ Backup saved as {dst}")

if __name__ == "__main__":
    backup()
