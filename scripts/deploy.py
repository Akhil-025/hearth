#!/usr/bin/env python3
"""
HEARTH Deployment Script
"""
import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path


def check_dependencies():
    """Check system dependencies."""
    print("🔍 Checking dependencies...")
    
    dependencies = [
        ("python3.11", ["python3.11", "--version"]),
        ("ollama", ["ollama", "--version"]),
        ("sqlite3", ["sqlite3", "--version"]),
    ]
    
    missing = []
    
    for name, cmd in dependencies:
        try:
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0:
                print(f"  ✓ {name}: {result.stdout.strip()}")
            else:
                missing.append(name)
                print(f"  ✗ {name}: Not found")
        except FileNotFoundError:
            missing.append(name)
            print(f"  ✗ {name}: Not found")
    
    return missing


def setup_directories(base_dir: Path):
    """Setup directory structure."""
    print(f"📁 Setting up directories in {base_dir}...")
    
    directories = [
        base_dir / "data",
        base_dir / "config",
        base_dir / "logs",
        base_dir / "backups",
        base_dir / "knowledge",
    ]
    
    for directory in directories:
        directory.mkdir(parents=True, exist_ok=True)
        print(f"  ✓ Created {directory.relative_to(base_dir)}")


def create_configuration(base_dir: Path, env: str):
    """Create configuration files."""
    print(f"⚙️  Creating {env} configuration...")
    
    config_dir = base_dir / "config"
    
    # Create default configuration
    default_config = {
        "kernel": {
            "data_dir": str(base_dir / "data"),
            "log_level": "INFO" if env == "production" else "DEBUG",
            "enable_audit": True,
            "require_permissions": env == "production",
            "service_startup_timeout": 30,
            "service_shutdown_timeout": 10
        },
        "memory": {
            "encryption_key": "GENERATE_NEW_KEY",  # Will be replaced
            "vector_store": {
                "type": "chroma",
                "persist_directory": str(base_dir / "data/vectors")
            },
            "promotion_policies": {
                "short_term_to_episodic": {
                    "min_confidence": 0.7,
                    "min_occurrences": 3
                }
            }
        },
        "knowledge": {
            "embedding_model": "llama2:7b",
            "chunk_size": 1000,
            "chunk_overlap": 200,
            "max_concurrent_ingestions": 4
        },
        "finance": {
            "default_currency": "USD",
            "encryption_enabled": True
        },
        "api": {
            "enabled": env == "production",
            "host": "127.0.0.1",
            "port": 8000,
            "api_key": "GENERATE_NEW_KEY"  # Will be replaced
        }
    }
    
    # Environment-specific overrides
    if env == "development":
        default_config["kernel"]["log_level"] = "DEBUG"
        default_config["api"]["enabled"] = True
        default_config["api"]["host"] = "0.0.0.0"
    
    config_path = config_dir / f"{env}.yaml"
    
    import yaml
    with open(config_path, 'w') as f:
        yaml.dump(default_config, f, default_flow_style=False)
    
    print(f"  ✓ Created {config_path.name}")
    
    # Create .env file
    env_content = f"""# HEARTH {env.upper()} Environment
HEARTH_ENV={env}
HEARTH_DATA_DIR={base_dir / 'data'}

# Generate with: openssl rand -hex 32
HEARTH_ENCRYPTION_KEY=your-encryption-key-here

# Ollama Configuration
OLLAMA_HOST=http://localhost:11434
OLLAMA_MODEL=llama2:7b

# API Configuration
HEARTH_API_KEY=your-api-key-here
HEARTH_API_HOST={default_config['api']['host']}
HEARTH_API_PORT={default_config['api']['port']}

# Security
HEARTH_REQUIRE_AUTH={'true' if env == 'production' else 'false'}
HEARTH_SESSION_TIMEOUT=3600
"""
    
    env_path = base_dir / ".env"
    with open(env_path, 'w') as f:
        f.write(env_content)
    
    print(f"  ✓ Created .env file")
    
    # Create .env.example
    example_content = env_content.replace(
        "your-encryption-key-here",
        "generate-with-openssl-rand-hex-32"
    ).replace(
        "your-api-key-here",
        "generate-secure-api-key"
    )
    
    example_path = base_dir / ".env.example"
    with open(example_path, 'w') as f:
        f.write(example_content)


def setup_database(base_dir: Path):
    """Initialize databases."""
    print("🗄️  Initializing databases...")
    
    data_dir = base_dir / "data"
    
    # Initialize memory database
    import sqlite3
    
    memory_db = data_dir / "memory.db"
    if not memory_db.exists():
        conn = sqlite3.connect(memory_db)
        conn.close()
        print("  ✓ Created memory database")
    
    # Initialize ledger database
    ledger_db = data_dir / "ledger.db"
    if not ledger_db.exists():
        conn = sqlite3.connect(ledger_db)
        conn.close()
        print("  ✓ Created ledger database")
    
    # Initialize vector store directory
    vector_dir = data_dir / "vectors"
    vector_dir.mkdir(exist_ok=True)
    print("  ✓ Created vector store directory")


def setup_logging(base_dir: Path):
    """Setup logging configuration."""
    print("📝 Setting up logging...")
    
    logs_dir = base_dir / "logs"
    
    # Create log rotation configuration
    log_config = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "detailed": {
                "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            },
            "simple": {
                "format": "%(levelname)s: %(message)s"
            }
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "level": "INFO",
                "formatter": "simple",
                "stream": "ext://sys.stdout"
            },
            "file": {
                "class": "logging.handlers.RotatingFileHandler",
                "level": "DEBUG",
                "formatter": "detailed",
                "filename": str(logs_dir / "hearth.log"),
                "maxBytes": 10485760,  # 10MB
                "backupCount": 5
            },
            "audit_file": {
                "class": "logging.handlers.RotatingFileHandler",
                "level": "INFO",
                "formatter": "detailed",
                "filename": str(logs_dir / "audit.log"),
                "maxBytes": 10485760,
                "backupCount": 10
            }
        },
        "loggers": {
            "hearth": {
                "level": "DEBUG",
                "handlers": ["console", "file"],
                "propagate": False
            },
            "audit": {
                "level": "INFO",
                "handlers": ["audit_file"],
                "propagate": False
            }
        },
        "root": {
            "level": "WARNING",
            "handlers": ["console"]
        }
    }
    
    log_config_path = base_dir / "config" / "logging.yaml"
    
    import yaml
    with open(log_config_path, 'w') as f:
        yaml.dump(log_config, f, default_flow_style=False)
    
    print(f"  ✓ Created logging configuration")


def create_systemd_service(base_dir: Path, user: str):
    """Create systemd service file for production."""
    print("⚙️  Creating systemd service...")
    
    service_content = f"""[Unit]
Description=HEARTH Personal Cognitive OS
After=network.target ollama.service
Requires=ollama.service

[Service]
Type=simple
User={user}
Group={user}
WorkingDirectory={base_dir}
EnvironmentFile={base_dir}/.env
ExecStart={sys.executable} {base_dir}/main.py --config {base_dir}/config/production.yaml
Restart=on-failure
RestartSec=10
StandardOutput=journal
StandardError=journal
SyslogIdentifier=hearth

# Security
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths={base_dir}/data {base_dir}/logs

[Install]
WantedBy=multi-user.target
"""
    
    service_path = base_dir / "hearth.service"
    with open(service_path, 'w') as f:
        f.write(service_content)
    
    print(f"  ✓ Created systemd service file")
    print(f"\n  To install:")
    print(f"    sudo cp {service_path} /etc/systemd/system/")
    print(f"    sudo systemctl daemon-reload")
    print(f"    sudo systemctl enable hearth")
    print(f"    sudo systemctl start hearth")


def create_backup_script(base_dir: Path):
    """Create backup script."""
    print("💾 Creating backup script...")
    
    backup_script = f"""#!/bin/bash
# HEARTH Backup Script
# Usage: ./backup.sh [backup_directory]

set -e

BACKUP_DIR="${{1:-{base_dir / 'backups'}}}"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_NAME="hearth_backup_$TIMESTAMP"
BACKUP_PATH="$BACKUP_DIR/$BACKUP_NAME"

echo "Creating HEARTH backup: $BACKUP_PATH"

# Create backup directory
mkdir -p "$BACKUP_PATH"

# Backup databases
cp "{base_dir / 'data'}/memory.db" "$BACKUP_PATH/" 2>/dev/null || true
cp "{base_dir / 'data'}/ledger.db" "$BACKUP_PATH/" 2>/dev/null || true

# Backup configuration
cp -r "{base_dir / 'config'}" "$BACKUP_PATH/" 2>/dev/null || true

# Backup knowledge
if [ -d "{base_dir / 'knowledge'}" ]; then
    cp -r "{base_dir / 'knowledge'}" "$BACKUP_PATH/" 2>/dev/null || true
fi

# Create manifest
cat > "$BACKUP_PATH/manifest.json" << EOF
{{
    "backup_name": "$BACKUP_NAME",
    "timestamp": "$TIMESTAMP",
    "hearth_version": "0.1.0",
    "files": [
        "memory.db",
        "ledger.db",
        "config/",
        "knowledge/"
    ]
}}
EOF

echo "Backup completed: $BACKUP_PATH"
echo "Size: $(du -sh "$BACKUP_PATH" | cut -f1)"
"""
    
    backup_path = base_dir / "scripts" / "backup.sh"
    backup_path.parent.mkdir(exist_ok=True)
    
    with open(backup_path, 'w') as f:
        f.write(backup_script)
    
    backup_path.chmod(0o755)
    
    print(f"  ✓ Created backup script: {backup_path}")


def main():
    """Main deployment function."""
    parser = argparse.ArgumentParser(description="HEARTH Deployment Script")
    parser.add_argument(
        "--env",
        choices=["development", "production"],
        default="development",
        help="Deployment environment"
    )
    parser.add_argument(
        "--dir",
        type=Path,
        default=Path.cwd(),
        help="Base directory for installation"
    )
    parser.add_argument(
        "--systemd-user",
        type=str,
        help="System user for systemd service (production only)"
    )
    
    args = parser.parse_args()
    
    print(f"🚀 Deploying HEARTH ({args.env}) to {args.dir}")
    print("=" * 60)
    
    # Check dependencies
    missing = check_dependencies()
    if missing:
        print(f"\n❌ Missing dependencies: {', '.join(missing)}")
        print("Please install them before continuing.")
        sys.exit(1)
    
    # Setup directories
    setup_directories(args.dir)
    
    # Create configuration
    create_configuration(args.dir, args.env)
    
    # Setup database
    setup_database(args.dir)
    
    # Setup logging
    setup_logging(args.dir)
    
    # Create backup script
    create_backup_script(args.dir)
    
    # Create systemd service for production
    if args.env == "production" and args.systemd_user:
        create_systemd_service(args.dir, args.systemd_user)
    
    print("\n" + "=" * 60)
    print("🎉 HEARTH deployment completed!")
    print(f"\nNext steps for {args.env}:")
    print(f"1. Edit {args.dir}/.env and replace placeholder values")
    print(f"2. Review configuration in {args.dir}/config/{args.env}.yaml")
    
    if args.env == "development":
        print(f"3. Run: cd {args.dir} && python main.py")
    else:
        print(f"3. Configure systemd service as shown above")
    
    print(f"\nBackup script: {args.dir}/scripts/backup.sh")
    print("=" * 60)


if __name__ == "__main__":
    main()