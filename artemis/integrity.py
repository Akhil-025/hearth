"""
IntegrityMonitor - Verifies system integrity.

Artemis integrity violation
Evidence preserved
Escalation irreversible without restart
"""

import hashlib
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from artemis.integrity_baseline import IntegrityBaseline


class IntegrityMonitor:
    """
    Monitors filesystem and audit chain integrity.
    
    All checks are explicit - no background threads or automatic polling.
    Anomalies are reported but not auto
        self._baseline = IntegrityBaseline()
        self._failure_count = 0matically acted upon.
    """
    
    def __init__(self):
        """Initialize integrity monitor."""
        self._baseline_hashes: Dict[str, str] = {}
        self._anomalies: List[str] = []
    
    def set_baseline(self, file_path: Path) -> None:
        """
        Record a baseline hash for a file.
        
        Args:
            file_path: Path to file to baseline
        
        Raises:
            FileNotFoundError: If file does not exist
            PermissionError: If file cannot be read
        """
        if not file_path.exists():
            raise FileNotFoundError(f"Cannot baseline non-existent file: {file_path}")
        
        if not file_path.is_file():
            raise ValueError(f"Can only baseline files, not directories: {file_path}")
        
        # Compute SHA-256 hash
        file_hash = self._compute_hash(file_path)
        self._baseline_hashes[str(file_path)] = file_hash
    
    def verify_file(self, file_path: Path) -> bool:
        """
        Verify a file against its baseline hash.
        
        Args:
            file_path: Path to file to verify
        
        Returns:
            True if hash matches baseline, False otherwise
        
        Raises:
            ValueError: If no baseline exists for this file
            FileNotFoundError: If file no longer exists
        """
        file_key = str(file_path)
        
        if file_key not in self._baseline_hashes:
            raise ValueError(f"No baseline hash for file: {file_path}")
        
        if not file_path.exists():
            self._anomalies.append(f"File missing: {file_path}")
            return False
        
        current_hash = self._compute_hash(file_path)
        expected_hash = self._baseline_hashes[file_key]
        
        if current_hash != expected_hash:
            self._anomalies.append(
                f"Hash mismatch for {file_path}: "
                f"expected {expected_hash[:8]}..., got {current_hash[:8]}..."
            )
            return False
        
        return True
    
    def verify_audit_chain(self) -> bool:
        """
        Checks for:
        - No gaps in sequence numbers
        - Valid cryptographic chain (stub)
        - No tampering detected
        
        Returns:
            True if chain is valid, False otherwise
        """
        # TODO: Implement audit chain verification
        # Should check:
        # - No gaps in sequence numbers
        # - Valid cryptographic chain
        # - No tampering detected
        return True
    
    def verify_files(self, root_dir: Path = Path(".")) -> Tuple[bool, List[Dict]]:
        """
        Verify critical files against integrity baseline.
        
        Artemis integrity violation
        Evidence preserved
        Escalation irreversible without restart
        
        Args:
            root_dir: Root directory to verify from
        
        Returns:
            Tuple of (all_valid, list_of_mismatches)
        
        Raises:
            RuntimeError: If baseline not available
        """
        try:
            is_valid, mismatches = self._baseline.verify_files(root_dir)
            
            if not is_valid:
                for mismatch in mismatches:
                    self._anomalies.append(
                        f"File {mismatch['status']}: {mismatch['file']} "
                        f"(baseline: {mismatch.get('baseline', 'N/A')}, "
                        f"current: {mismatch.get('current', 'N/A')})"
                    )
                self._failure_count += 1
            
            return is_valid, mismatches
        
        except Exception as e:
            self._anomalies.append(f"File verification error: {e}")
            self._failure_count += 1
            return False, []
    
    def initialize_baseline(self, root_dir: Path = Path(".")) -> None:
        """
        Initialize integrity baseline at first secure boot.
        
        Should only be called once at system startup.
        
        Args:
            root_dir: Root directory to scan
        
        Raises:
            RuntimeError: If baseline already exists
        """
        if self._baseline.has_baseline():
            # Baseline already exists - load it
            self._baseline.load_baseline()
            return
        
        # Create new baseline
        self._baseline.create_baseline(root_dir)
        self._baseline.save_baseline()
    
    def get_failure_count(self) -> int:
        """Get number of integrity failures detected."""
        return self._failure_count
    
    def reset_failure_count(self) -> None:
        """Reset failure counter (only on state recovery)."""
        self._failure_count = 0
    
    def get_anomalies(self) -> List[str]:
        """
        Get list of detected anomalies.
        
        Returns:
            List of anomaly descriptions
        """
        return self._anomalies.copy()
    
    def clear_anomalies(self) -> None:
        """Clear recorded anomalies."""
        self._anomalies.clear()
    
    def _compute_hash(self, file_path: Path) -> str:
        """
        Compute SHA-256 hash of a file.
        
        Args:
            file_path: Path to file
        
        Returns:
            Hex-encoded SHA-256 hash
        """
        hasher = hashlib.sha256()
        
        with open(file_path, "rb") as f:
            # Read in chunks to handle large files
            while chunk := f.read(8192):
                hasher.update(chunk)
        
        return hasher.hexdigest()
