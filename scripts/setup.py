#!/usr/bin/env python3
"""
HEARTH Initialization Script
"""
import asyncio
import json
import os
import secrets
import subprocess
import sys
from pathlib import Path

def generate_encryption_key() -> str:
    """Generate secure encryption key."""
    return secrets.token_hex(32)

def check_ollama() -> bool:
    """Check if Ollama is installed and running."""
    try:
        result = subprocess.run(
            ["ollama", "--version"],
            capture_output=True,
            text=True
        )
        return result.returncode == 0
    except FileNotFoundError:
        return False

def pull_default_model() -> bool:
    """Pull default Ollama model."""
    try:
        print("Pulling llama2:7b model (this may take several minutes)...")
        result = subprocess.run(
            ["ollama", "pull", "llama2:7b"],
            capture_output=True,
            text=True
        )
        return result.returncode == 0
    except Exception as e:
        print(f"Error pulling model: {e}")
        return False

async def initialize_hearth() -> None:
    """Initialize HEARTH system."""
    print("🚀 Initializing HEARTH Personal Cognitive OS")
    print("=" * 50)
    
    # Check Python version
    if sys.version_info < (3, 11):
        print("❌ Python 3.11+ required")
        sys.exit(1)
    
    # Create directories
    directories = [
        "./data",
        "./config",
        "./logs",
        "./backups"
    ]
    
    for directory in directories:
        Path(directory).mkdir(parents=True, exist_ok=True)
        print(f"📁 Created directory: {directory}")
    
    # Generate encryption key
    encryption_key = generate_encryption_key()
    env_content = f"""# HEARTH Configuration
HEARTH_ENV=development
HEARTH_DATA_DIR=./data

# Encryption (keep this secret!)
HEARTH_ENCRYPTION_KEY={encryption_key}

# Ollama Configuration
OLLAMA_HOST=http://localhost:11434
OLLAMA_MODEL=llama2:7b

# Security
HEARTH_REQUIRE_AUTH=false  # Set to true in production
HEARTH_SESSION_TIMEOUT=3600
"""
    
    # Write .env file
    with open(".env", "w") as f:
        f.write(env_content)
    print("🔐 Generated encryption key and .env file")
    
    # Check Ollama
    print("\n🔍 Checking Ollama installation...")
    if not check_ollama():
        print("❌ Ollama not found. Please install from https://ollama.ai/")
        print("\nOn macOS/Linux:")
        print("  curl -fsSL https://ollama.ai/install.sh | sh")
        print("\nOn Windows:")
        print("  Download from https://ollama.ai/download")
        sys.exit(1)
    
    print("✅ Ollama is installed")
    
    # Pull default model
    if not pull_default_model():
        print("⚠️  Could not pull default model. You can manually run:")
        print("  ollama pull llama2:7b")
    
    # Create default configuration
    default_config = {
        "kernel": {
            "data_dir": "./data",
            "log_level": "INFO",
            "enable_audit": True,
            "require_permissions": True
        },
        "memory": {
            "vector_store": {
                "type": "chroma",
                "persist_directory": "./data/vectors"
            },
            "promotion_policies": {
                "short_term_to_episodic": {
                    "min_confidence": 0.7,
                    "min_occurrences": 3
                },
                "episodic_to_summarized": {
                    "time_window_days": 7,
                    "max_memories": 100
                }
            }
        },
        "knowledge": {
            "embedding_model": "llama2:7b",
            "chunk_size": 1000,
            "chunk_overlap": 200
        }
    }
    
    config_path = Path("./config/default.yaml")
    import yaml
    with open(config_path, "w") as f:
        yaml.dump(default_config, f, default_flow_style=False)
    
    print(f"📄 Created default configuration: {config_path}")
    
    # Initialize database
    print("\n🗄️  Initializing databases...")
    from mnemosyne.memory_store import MemoryStore
    
    store = MemoryStore("./data/memory.db")
    asyncio.run(store.start())
    asyncio.run(store.stop())
    
    print("✅ Database initialized")
    
    print("\n" + "=" * 50)
    print("🎉 HEARTH initialization complete!")
    print("\nNext steps:")
    print("1. Review .env file for security settings")
    print("2. Run: python main.py --help")
    print("3. Start with: python main.py")
    print("\nFor development:")
    print("  pip install -r requirements.txt")
    print("  pip install -e .[dev]")

if __name__ == "__main__":
    asyncio.run(initialize_hearth())