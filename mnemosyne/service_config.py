"""
Mnemosyne service configuration for Hearth integration.

Minimal, explicit configuration. No auto-loading, no background services.
"""
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass
class MnemosyneConfig:
    """
    Configuration for Mnemosyne service integration.
    
    All features are disabled by default.
    Only write() and read() are exposed to Hestia.
    """
    
    # Activation
    enabled: bool = False
    
    # Storage paths
    db_path: Path = None  # Will use default if None
    
    def __post_init__(self):
        """Validate configuration."""
        if self.db_path is None:
            self.db_path = Path("./data/memory.db")
        else:
            self.db_path = Path(self.db_path)
        
        # Create directory if needed
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
    
    @property
    def is_valid(self) -> bool:
        """Check if configuration is usable."""
        return (
            self.db_path is not None
            and self.db_path.parent.is_dir()
        )
