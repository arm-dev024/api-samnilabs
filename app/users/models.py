import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass
class User:
    email: str
    full_name: str
    auth_provider: str
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    google_id: str | None = None
    picture_url: str | None = None
    hashed_password: str | None = None
    is_active: bool = True
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dynamo_item(self) -> dict:
        """Convert to a DynamoDB item dict."""
        item = {
            "id": self.id,
            "email": self.email,
            "full_name": self.full_name,
            "auth_provider": self.auth_provider,
            "is_active": self.is_active,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }
        if self.google_id is not None:
            item["google_id"] = self.google_id
        if self.picture_url is not None:
            item["picture_url"] = self.picture_url
        if self.hashed_password is not None:
            item["hashed_password"] = self.hashed_password
        return item

    @classmethod
    def from_dynamo_item(cls, item: dict) -> "User":
        """Create a User from a DynamoDB item dict."""
        return cls(
            id=item["id"],
            email=item["email"],
            full_name=item["full_name"],
            auth_provider=item["auth_provider"],
            google_id=item.get("google_id"),
            picture_url=item.get("picture_url"),
            hashed_password=item.get("hashed_password"),
            is_active=item.get("is_active", True),
            created_at=item.get("created_at", ""),
            updated_at=item.get("updated_at", ""),
        )
