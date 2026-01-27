"""
Key Manager - Secure key management with hardware support.
"""
import base64
import hashlib
import json
import os
import secrets
import tempfile
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from uuid import uuid4

import cryptography
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives.serialization import (
    BestAvailableEncryption,
    Encoding,
    NoEncryption,
    PrivateFormat,
    PublicFormat,
    load_pem_private_key,
    load_pem_public_key
)

from ..logging.structured_logger import StructuredLogger


class KeyType(Enum):
    """Key types."""
    SYMMETRIC = "symmetric"  # AES
    ASYMMETRIC = "asymmetric"  # RSA
    DERIVED = "derived"  # Derived from password


class KeyUsage(Enum):
    """Key usage restrictions."""
    ENCRYPTION = "encryption"
    DECRYPTION = "decryption"
    SIGNING = "signing"
    VERIFICATION = "verification"
    DERIVATION = "derivation"


@dataclass
class KeyMetadata:
    """Key metadata."""
    key_id: str
    key_type: KeyType
    algorithm: str
    key_size: int
    created_at: float
    expires_at: Optional[float] = None
    usage: List[KeyUsage] = None
    tags: List[str] = None
    description: Optional[str] = None
    
    def __post_init__(self):
        if self.usage is None:
            self.usage = []
        if self.tags is None:
            self.tags = []


class KeyManager:
    """
    Secure key management with hardware security module support.
    
    Features:
    - Secure key storage
    - Key rotation
    - Usage tracking
    - Hardware security module integration (future)
    - Key derivation from passwords
    """
    
    def __init__(self, key_store_path: Optional[Path] = None):
        self.logger = StructuredLogger(__name__)
        
        # Key storage
        self.key_store_path = key_store_path or Path("./data/keys")
        self.key_store_path.mkdir(parents=True, exist_ok=True)
        
        # In-memory key cache (encrypted)
        self.key_cache: Dict[str, bytes] = {}
        self.metadata_cache: Dict[str, KeyMetadata] = {}
        
        # Master key for cache encryption
        self.master_key = self._generate_master_key()
        
        # Hardware Security Module integration placeholder
        self.hsm_available = False
        self._detect_hsm()
        
        self.logger.info(
            "Key manager initialized",
            key_store=str(self.key_store_path),
            hsm_available=self.hsm_available
        )
    
    def _detect_hsm(self):
        """Detect available Hardware Security Modules."""
        # Check for YubiKey
        try:
            import yubikey_manager
            self.hsm_available = True
            self.logger.info("YubiKey detected")
        except ImportError:
            pass
        
        # Check for TPM
        try:
            import tpm2_pytss
            self.hsm_available = True
            self.logger.info("TPM detected")
        except ImportError:
            pass
    
    def _generate_master_key(self) -> bytes:
        """Generate or load master key."""
        master_key_path = self.key_store_path / "master.key"
        
        if master_key_path.exists():
            # Load existing master key
            with open(master_key_path, 'rb') as f:
                encrypted_key = f.read()
            
            # In production, this would be derived from a hardware key or KMS
            # For now, we'll use a fixed derivation (NOT FOR PRODUCTION)
            from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
            
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=b'hearth_master_salt',  # Should be unique per installation
                iterations=100000
            )
            
            # In production, get password from secure environment
            password = os.environ.get("HEARTH_MASTER_PASSWORD", "default_master_password").encode()
            master_key = kdf.derive(password)
            
            # Decrypt stored key
            fernet = Fernet(base64.urlsafe_b64encode(master_key))
            return fernet.decrypt(encrypted_key)
        
        else:
            # Generate new master key
            master_key = secrets.token_bytes(32)
            
            # Derive encryption key
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=b'hearth_master_salt',
                iterations=100000
            )
            
            password = os.environ.get("HEARTH_MASTER_PASSWORD", "default_master_password").encode()
            encryption_key = kdf.derive(password)
            
            # Encrypt and store
            fernet = Fernet(base64.urlsafe_b64encode(encryption_key))
            encrypted_key = fernet.encrypt(master_key)
            
            with open(master_key_path, 'wb') as f:
                f.write(encrypted_key)
            
            self.logger.info("New master key generated")
            return master_key
    
    def _encrypt_for_cache(self, data: bytes) -> bytes:
        """Encrypt data for in-memory cache."""
        fernet = Fernet(base64.urlsafe_b64encode(self.master_key))
        return fernet.encrypt(data)
    
    def _decrypt_from_cache(self, encrypted_data: bytes) -> bytes:
        """Decrypt data from in-memory cache."""
        fernet = Fernet(base64.urlsafe_b64encode(self.master_key))
        return fernet.decrypt(encrypted_data)
    
    def generate_symmetric_key(
        self,
        key_size: int = 256,
        usage: List[KeyUsage] = None,
        tags: List[str] = None,
        description: Optional[str] = None,
        expires_in_days: Optional[int] = None
    ) -> Tuple[str, bytes]:
        """
        Generate a symmetric encryption key.
        
        Returns: (key_id, key_bytes)
        """
        if key_size not in [128, 192, 256]:
            raise ValueError("Key size must be 128, 192, or 256 bits")
        
        key_bytes = secrets.token_bytes(key_size // 8)
        key_id = str(uuid4())
        
        metadata = KeyMetadata(
            key_id=key_id,
            key_type=KeyType.SYMMETRIC,
            algorithm=f"AES-{key_size}",
            key_size=key_size,
            created_at=time.time(),
            expires_at=(
                time.time() + expires_in_days * 86400
                if expires_in_days else None
            ),
            usage=usage or [KeyUsage.ENCRYPTION, KeyUsage.DECRYPTION],
            tags=tags or [],
            description=description
        )
        
        # Store key securely
        self._store_key(key_id, key_bytes, metadata)
        
        self.logger.info(
            "Symmetric key generated",
            key_id=key_id,
            key_size=key_size,
            algorithm=f"AES-{key_size}"
        )
        
        return key_id, key_bytes
    
    def generate_asymmetric_keypair(
        self,
        key_size: int = 2048,
        usage: List[KeyUsage] = None,
        tags: List[str] = None,
        description: Optional[str] = None,
        expires_in_days: Optional[int] = None
    ) -> Tuple[str, bytes, bytes]:
        """
        Generate an asymmetric key pair.
        
        Returns: (key_id, private_key_pem, public_key_pem)
        """
        if key_size not in [1024, 2048, 3072, 4096]:
            raise ValueError("Key size must be 1024, 2048, 3072, or 4096 bits")
        
        # Generate private key
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=key_size
        )
        
        # Get public key
        public_key = private_key.public_key()
        
        # Serialize keys
        private_pem = private_key.private_bytes(
            encoding=Encoding.PEM,
            format=PrivateFormat.PKCS8,
            encryption_algorithm=BestAvailableEncryption(self.master_key)
        )
        
        public_pem = public_key.public_bytes(
            encoding=Encoding.PEM,
            format=PublicFormat.SubjectPublicKeyInfo
        )
        
        key_id = str(uuid4())
        
        metadata = KeyMetadata(
            key_id=key_id,
            key_type=KeyType.ASYMMETRIC,
            algorithm=f"RSA-{key_size}",
            key_size=key_size,
            created_at=time.time(),
            expires_at=(
                time.time() + expires_in_days * 86400
                if expires_in_days else None
            ),
            usage=usage or [KeyUsage.SIGNING, KeyUsage.VERIFICATION],
            tags=tags or [],
            description=description
        )
        
        # Store private key securely
        self._store_key(key_id, private_pem, metadata)
        
        # Store public key separately (unencrypted)
        public_key_path = self.key_store_path / f"{key_id}.pub"
        with open(public_key_path, 'wb') as f:
            f.write(public_pem)
        
        self.logger.info(
            "Asymmetric key pair generated",
            key_id=key_id,
            key_size=key_size
        )
        
        return key_id, private_pem, public_pem
    
    def derive_key_from_password(
        self,
        password: str,
        salt: Optional[bytes] = None,
        key_size: int = 256,
        iterations: int = 100000,
        usage: List[KeyUsage] = None,
        tags: List[str] = None,
        description: Optional[str] = None
    ) -> Tuple[str, bytes]:
        """
        Derive key from password using PBKDF2.
        
        Returns: (key_id, derived_key)
        """
        if not salt:
            salt = secrets.token_bytes(16)
        
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=key_size // 8,
            salt=salt,
            iterations=iterations
        )
        
        derived_key = kdf.derive(password.encode())
        key_id = str(uuid4())
        
        metadata = KeyMetadata(
            key_id=key_id,
            key_type=KeyType.DERIVED,
            algorithm="PBKDF2-HMAC-SHA256",
            key_size=key_size,
            created_at=time.time(),
            usage=usage or [KeyUsage.ENCRYPTION, KeyUsage.DECRYPTION],
            tags=tags or [],
            description=description,
            # Store salt in metadata
            extra={"salt": base64.b64encode(salt).decode(), "iterations": iterations}
        )
        
        # Store derived key
        self._store_key(key_id, derived_key, metadata)
        
        self.logger.info(
            "Key derived from password",
            key_id=key_id,
            key_size=key_size,
            iterations=iterations
        )
        
        return key_id, derived_key
    
    def _store_key(self, key_id: str, key_data: bytes, metadata: KeyMetadata):
        """Store key securely."""
        # Encrypt key data
        encrypted_key = self._encrypt_for_cache(key_data)
        
        # Store in cache
        self.key_cache[key_id] = encrypted_key
        self.metadata_cache[key_id] = metadata
        
        # Store on disk (encrypted)
        key_path = self.key_store_path / f"{key_id}.key"
        metadata_path = self.key_store_path / f"{key_id}.meta"
        
        # Write encrypted key
        with open(key_path, 'wb') as f:
            f.write(encrypted_key)
        
        # Write metadata (unencrypted but safe)
        metadata_dict = {
            "key_id": metadata.key_id,
            "key_type": metadata.key_type.value,
            "algorithm": metadata.algorithm,
            "key_size": metadata.key_size,
            "created_at": metadata.created_at,
            "expires_at": metadata.expires_at,
            "usage": [u.value for u in metadata.usage],
            "tags": metadata.tags,
            "description": metadata.description,
            "extra": getattr(metadata, 'extra', {})
        }
        
        with open(metadata_path, 'w') as f:
            json.dump(metadata_dict, f, indent=2)
    
    def get_key(self, key_id: str) -> Optional[bytes]:
        """Retrieve key by ID."""
        # Check cache first
        if key_id in self.key_cache:
            encrypted_key = self.key_cache[key_id]
            return self._decrypt_from_cache(encrypted_key)
        
        # Load from disk
        key_path = self.key_store_path / f"{key_id}.key"
        if not key_path.exists():
            return None
        
        with open(key_path, 'rb') as f:
            encrypted_key = f.read()
        
        # Decrypt and cache
        key_data = self._decrypt_from_cache(encrypted_key)
        self.key_cache[key_id] = encrypted_key
        
        return key_data
    
    def get_key_metadata(self, key_id: str) -> Optional[KeyMetadata]:
        """Get key metadata."""
        if key_id in self.metadata_cache:
            return self.metadata_cache[key_id]
        
        metadata_path = self.key_store_path / f"{key_id}.meta"
        if not metadata_path.exists():
            return None
        
        with open(metadata_path, 'r') as f:
            metadata_dict = json.load(f)
        
        # Convert back to KeyMetadata
        metadata = KeyMetadata(
            key_id=metadata_dict["key_id"],
            key_type=KeyType(metadata_dict["key_type"]),
            algorithm=metadata_dict["algorithm"],
            key_size=metadata_dict["key_size"],
            created_at=metadata_dict["created_at"],
            expires_at=metadata_dict.get("expires_at"),
            usage=[KeyUsage(u) for u in metadata_dict["usage"]],
            tags=metadata_dict["tags"],
            description=metadata_dict.get("description")
        )
        
        # Add extra fields
        if "extra" in metadata_dict:
            metadata.extra = metadata_dict["extra"]
        
        self.metadata_cache[key_id] = metadata
        return metadata
    
    def rotate_key(self, key_id: str) -> Optional[str]:
        """Rotate (re-generate) a key."""
        metadata = self.get_key_metadata(key_id)
        if not metadata:
            return None
        
        # Generate new key based on old metadata
        if metadata.key_type == KeyType.SYMMETRIC:
            new_key_id, new_key = self.generate_symmetric_key(
                key_size=metadata.key_size,
                usage=metadata.usage,
                tags=metadata.tags,
                description=f"Rotated from {key_id}",
                expires_in_days=365
            )
        elif metadata.key_type == KeyType.ASYMMETRIC:
            new_key_id, _, _ = self.generate_asymmetric_keypair(
                key_size=metadata.key_size,
                usage=metadata.usage,
                tags=metadata.tags,
                description=f"Rotated from {key_id}",
                expires_in_days=365
            )
        else:
            # Can't rotate derived keys
            return None
        
        # Mark old key as expired
        metadata.expires_at = time.time()
        self._store_key(key_id, b"", metadata)  # Overwrite with empty
        
        self.logger.info(
            "Key rotated",
            old_key_id=key_id,
            new_key_id=new_key_id
        )
        
        return new_key_id
    
    def revoke_key(self, key_id: str) -> bool:
        """Revoke a key immediately."""
        if key_id not in self.metadata_cache:
            return False
        
        # Mark as expired
        metadata = self.metadata_cache[key_id]
        metadata.expires_at = time.time()
        
        # Overwrite key data with zeros
        zero_key = b'\x00' * (metadata.key_size // 8)
        self._store_key(key_id, zero_key, metadata)
        
        self.logger.warning("Key revoked", key_id=key_id)
        return True
    
    def list_keys(
        self,
        key_type: Optional[KeyType] = None,
        tags: Optional[List[str]] = None,
        include_expired: bool = False
    ) -> List[KeyMetadata]:
        """List keys with optional filtering."""
        keys = []
        
        # Load all metadata files
        for meta_path in self.key_store_path.glob("*.meta"):
            key_id = meta_path.stem.replace('.meta', '')
            metadata = self.get_key_metadata(key_id)
            
            if not metadata:
                continue
            
            # Apply filters
            if key_type and metadata.key_type != key_type:
                continue
            
            if tags and not any(tag in metadata.tags for tag in tags):
                continue
            
            if not include_expired and metadata.expires_at and metadata.expires_at < time.time():
                continue
            
            keys.append(metadata)
        
        return keys
    
    def cleanup_expired_keys(self) -> int:
        """Remove expired keys from disk and cache."""
        expired_count = 0
        
        for key_id in list(self.metadata_cache.keys()):
            metadata = self.metadata_cache[key_id]
            
            if metadata.expires_at and metadata.expires_at < time.time():
                # Remove from disk
                key_path = self.key_store_path / f"{key_id}.key"
                meta_path = self.key_store_path / f"{key_id}.meta"
                pub_path = self.key_store_path / f"{key_id}.pub"
                
                for path in [key_path, meta_path, pub_path]:
                    if path.exists():
                        path.unlink()
                
                # Remove from cache
                self.key_cache.pop(key_id, None)
                self.metadata_cache.pop(key_id, None)
                
                expired_count += 1
        
        if expired_count > 0:
            self.logger.info(
                "Expired keys cleaned up",
                count=expired_count
            )
        
        return expired_count