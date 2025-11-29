import os
from datetime import datetime
from shutil import copyfile, make_archive
import pyAesCrypt
from hearth.modules.notifications import speak

BASE_PATH = os.path.dirname(__file__)
BACKUP_ROOT = os.path.join(BASE_PATH, "backups")
LOG_FILE = os.path.join(BACKUP_ROOT, "log.txt")
PASSWORD_FILE = os.path.join(BASE_PATH, "backup_password.txt")
BUFFER_SIZE = 64 * 1024

FILES_TO_BACKUP = [
    ("stats.json", "stats.json"),
    ("levels.json", "levels.json"),
    ("decay_config.json", "decay_config.json"),
    ("quests.json", "quests.json"),
    (os.path.join("..", "sentience", "mnemosyne_memory.json"), "mnemosyne_memory.json")
]

def ensure_backup_dir():
    if not os.path.exists(BACKUP_ROOT):
        os.makedirs(BACKUP_ROOT)

def log_event(message):
    ensure_backup_dir()
    timestamp = datetime.now().strftime("[%Y-%m-%d %H:%M]")
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(f"{timestamp} {message}\n")

def read_password():
    try:
        with open(PASSWORD_FILE, "r", encoding="utf-8") as f:
            return f.read().strip()
    except:
        return None

def run_backup(tag=None, encrypted=False):
    ensure_backup_dir()
    date = datetime.now().strftime("%Y-%m-%d")
    suffix = f"_{tag.replace(' ', '_')}" if tag else ""
    folder_name = date + suffix
    folder_path = os.path.join(BACKUP_ROOT, folder_name)
    os.makedirs(folder_path, exist_ok=True)

    results = []

    for src_filename, dst_filename in FILES_TO_BACKUP:
        src = os.path.abspath(os.path.join(BASE_PATH, src_filename))
        dst = os.path.join(folder_path, dst_filename)

        try:
            if os.path.exists(src):
                copyfile(src, dst)
                result = f"✅ {dst_filename} → {folder_name}/"
            else:
                result = f"⚠️ Missing: {dst_filename}"
        except Exception as e:
            result = f"❌ Error backing up {dst_filename}: {e}"

        log_event(result)
        results.append(result)

    if encrypted:
        zip_path = folder_path + ".zip"
        archive_name = make_archive(folder_path, "zip", folder_path)
        password = read_password()
        if not password:
            return "❌ No password found in backup_password.txt"

        encrypted_path = zip_path + ".aes"
        pyAesCrypt.encryptFile(zip_path, encrypted_path, password, BUFFER_SIZE)
        os.remove(zip_path)

        # Clean up plain folder
        for file in os.listdir(folder_path):
            os.remove(os.path.join(folder_path, file))
        os.rmdir(folder_path)

        result = f"🔐 Encrypted backup created: {os.path.basename(encrypted_path)}"
        log_event(result)
        results.append(result)

    speak("Backup complete. Your scrolls have been sealed.", mode="introspect")
    return "\n".join(results)

def restore_backup(date_str):
    folder_path = os.path.join(BACKUP_ROOT, date_str)
    if not os.path.exists(folder_path):
        return f"⚠️ No backup found for {date_str}"

    restored = []
    for _, dst_filename in FILES_TO_BACKUP:
        src = os.path.join(folder_path, dst_filename)
        dst = os.path.abspath(os.path.join(BASE_PATH, dst_filename))
        try:
            if os.path.exists(src):
                copyfile(src, dst)
                restored.append(f"🕊️ Restored {dst_filename}")
            else:
                restored.append(f"⚠️ {dst_filename} missing in backup")
        except Exception as e:
            restored.append(f"❌ Failed to restore {dst_filename}: {e}")
    speak("Restoration complete. The past has returned.", mode="introspect")
    return "\n".join(restored)

def restore_latest():
    ensure_backup_dir()
    folders = sorted([
        name for name in os.listdir(BACKUP_ROOT)
        if os.path.isdir(os.path.join(BACKUP_ROOT, name))
    ], reverse=True)
    if not folders:
        return "📭 No backups available."
    return restore_backup(folders[0])

def describe_backup(date_str):
    folder_path = os.path.join(BACKUP_ROOT, date_str)
    if not os.path.exists(folder_path):
        return f"⚠️ No backup found for {date_str}"

    files = os.listdir(folder_path)
    if not files:
        return f"📂 {date_str} is empty."
    return f"📜 Contents of {date_str}:\n" + "\n".join(f"• {f}" for f in files)

def purge_backups_keep(n):
    ensure_backup_dir()
    folders = sorted([
        name for name in os.listdir(BACKUP_ROOT)
        if os.path.isdir(os.path.join(BACKUP_ROOT, name)) or name.endswith(".aes")
    ])
    if len(folders) <= n:
        return f"ℹ️ Nothing to purge. You only have {len(folders)} backup(s)."

    to_delete = folders[:-n]
    for folder in to_delete:
        path = os.path.join(BACKUP_ROOT, folder)
        try:
            if os.path.isdir(path):
                for file in os.listdir(path):
                    os.remove(os.path.join(path, file))
                os.rmdir(path)
            else:
                os.remove(path)
        except Exception as e:
            return f"❌ Failed to delete {folder}: {e}"
    return f"🧹 Purged {len(to_delete)} old backup(s)."

def list_backups():
    ensure_backup_dir()
    items = sorted(os.listdir(BACKUP_ROOT), reverse=True)
    if not items:
        return "📭 No backups found yet."
    return "📦 Available backups:\n" + "\n".join(f"• {f}" for f in items)
