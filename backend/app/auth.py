import hashlib
from sqlalchemy.orm import Session
from .models import APIKey


def hash_key(raw_key: str) -> str:
    """Simple SHA-256 hash — good enough for API keys (not passwords)."""
    return hashlib.sha256(raw_key.encode()).hexdigest()


def verify_api_key(db: Session, raw_key: str) -> bool:
    """Checks if the given raw key matches an active key in the DB."""
    key_hash = hash_key(raw_key)
    record = (
        db.query(APIKey)
        .filter(APIKey.key_hash == key_hash, APIKey.is_active == True)
        .first()
    )
    return record is not None


def create_api_key(db: Session, project_id, raw_key: str, name: str = None) -> APIKey:
    """Stores a new hashed API key. Call this once to seed a real key."""
    key = APIKey(
        key_hash=hash_key(raw_key),
        project_id=project_id,
        name=name,
        is_active=True,
    )
    db.add(key)
    db.commit()
    db.refresh(key)
    return key
