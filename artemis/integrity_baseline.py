"""
Artemis Integrity Baseline - Cryptographic Record of System State

Records SHA256 hashes of critical system directories at first secure boot.
Used to detect tampering with code and audit logs.

Artemis integrity violation
Evidence preserved
Escalation irreversible without restart
"""

import hashlib
import json
import os
from pathlib import Path
from typing import Dict, Optional


class IntegrityBaseline:
    """
    Records and verifies cryptographic baseline of critical directories.
    
    Baseline includes:
    - core/ (kernel and bootstrap)
    - artemis/ (security infrastructure)
    - stage4/ (execution orchestration)
    - domains/ (domain adapters)
    
    Created ONLY at first secure boot.
    Never modified after creation.
    """
    
    CRITICAL_DIRECTORIES = [
        "core/",
        "artemis/",
        "stage4/",
        "domains/",
    ]
    
    def __init__(self, baseline_path: Optional[Path] = None):
        """
        Initialize integrity baseline.
        
        Args:
            baseline_path: Path to store/load baseline (optional)
        """
        self._baseline_path = baseline_path or Path("./.artemis_baseline")
        self._baseline: Dict[str, str] = {}
        self._loaded = False
    
    def create_baseline(self, root_dir: Path) -> Dict[str, str]:
        """
        Create integrity baseline by hashing all Python files in critical directories.
        
        Called ONLY at first secure boot.
        Never called again without explicit restart.
        
        Args:
            root_dir: Root directory to scan from
        
        Returns:
            Dict mapping file paths to SHA256 hashes
        """
        if self._loaded and self._baseline:
            # Baseline already exists - don't overwrite
            raise RuntimeError(
                "Integrity baseline already exists. "
                "Cannot recreate without system restart."
            )
        
        baseline = {}
        
        for dir_pattern in self.CRITICAL_DIRECTORIES:
            dir_path = root_dir / dir_pattern
            if not dir_path.exists():
                continue
            
            # Walk all Python files in directory
            for py_file in sorted(dir_path.rglob("*.py")):
                # Skip __pycache__
                if "__pycache__" in py_file.parts:
                    continue
                
                try:
                    file_hash = self._compute_hash(py_file)
                    rel_path = str(py_file.relative_to(root_dir))
                    baseline[rel_path] = file_hash
                except Exception as e:
                    # Skip unreadable files
                    continue
        
        self._baseline = baseline
        return baseline
    
    def save_baseline(self) -> None:
        """
        Save baseline to disk (plaintext for now, can be encrypted later).

        Artemis attack-surface reduction
        Fail closed
        No recovery without restart

        Writes allowed ONLY during first secure boot.
        
        Artemis integrity violation
        Evidence preserved
        Escalation irreversible without restart
        """
        if not self._baseline:
            raise ValueError("No baseline to save")
        
        try:
            with open(self._baseline_path, "w") as f:
                json.dump(self._baseline, f, indent=2)
            try:
                os.chmod(self._baseline_path, 0o444)
            except Exception as e:
                raise RuntimeError(f"Failed to set baseline read-only: {e}")
        except Exception as e:
            raise RuntimeError(f"Failed to save integrity baseline: {e}")
    
    def load_baseline(self) -> Dict[str, str]:
        """
        Load baseline from disk.
        
        Returns:
            Dict mapping file paths to SHA256 hashes
        
        Raises:
            FileNotFoundError: If baseline doesn't exist
        """
        if self._loaded and self._baseline:
            return self._baseline
        
        if not self._baseline_path.exists():
            raise FileNotFoundError(f"Integrity baseline not found: {self._baseline_path}")
        
        try:
            with open(self._baseline_path, "r") as f:
                self._baseline = json.load(f)
            self._loaded = True
            return self._baseline
        except Exception as e:
            raise RuntimeError(f"Failed to load integrity baseline: {e}")
    
    def verify_files(self, root_dir: Path) -> tuple[bool, list]:
        """
        Verify all files against baseline.
        
        Artemis integrity violation
        Evidence preserved
        Escalation irreversible without restart
        
        Args:
            root_dir: Root directory to verify from
        
        Returns:
            Tuple of (all_valid, list_of_mismatches)
            
            Mismatch format:
            {
                "file": "<relative_path>",
                "baseline": "<expected_hash>",
                "current": "<actual_hash>",
                "status": "modified|missing|added"
            }
        """
        if not self._baseline:
            raise RuntimeError("No baseline loaded")
        
        mismatches = []
        verified = set()
        
        # Check each file in baseline
        for rel_path, expected_hash in self._baseline.items():
            verified.add(rel_path)
            file_path = root_dir / rel_path
            
            if not file_path.exists():
                mismatches.append({
                    "file": rel_path,
                    "baseline": expected_hash,
                    "current": None,
                    "status": "missing"
                })
                continue
            
            try:
                current_hash = self._compute_hash(file_path)
                if current_hash != expected_hash:
                    mismatches.append({
                        "file": rel_path,
                        "baseline": expected_hash[:16],  # Truncate for display
                        "current": current_hash[:16],
                        "status": "modified"
                    })
            except Exception as e:
                mismatches.append({
                    "file": rel_path,
                    "baseline": expected_hash[:16],
                    "current": None,
                    "status": "error"
                })
        
        # Check for new files not in baseline
        for dir_pattern in self.CRITICAL_DIRECTORIES:
            dir_path = root_dir / dir_pattern
            if not dir_path.exists():
                continue
            
            for py_file in dir_path.rglob("*.py"):
                if "__pycache__" in py_file.parts:
                    continue
                
                rel_path = str(py_file.relative_to(root_dir))
                if rel_path not in verified:
                    try:
                        current_hash = self._compute_hash(py_file)
                        mismatches.append({
                            "file": rel_path,
                            "baseline": None,
                            "current": current_hash[:16],
                            "status": "added"
                        })
                    except Exception:
                        pass
        
        is_valid = len(mismatches) == 0
        return is_valid, mismatches
    
    def _compute_hash(self, file_path: Path) -> str:
        """
        Compute SHA256 hash of a file.
        
        Args:
            file_path: Path to file
        
        Returns:
            Hex-encoded SHA256 hash
        """
        hasher = hashlib.sha256()
        
        with open(file_path, "rb") as f:
            while chunk := f.read(8192):
                hasher.update(chunk)
        
        return hasher.hexdigest()
    
    def has_baseline(self) -> bool:
        """Check if baseline exists on disk."""
        return self._baseline_path.exists()
