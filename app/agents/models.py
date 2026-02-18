import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass
class Agent:
    """An AI agent owned by a user, stored as an embedded item in the User record."""

    name: str
    description: str
    system_prompt: str
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    model: str = "gpt-4o-mini"
    temperature: float = 0.7
    max_tokens: int = 150
    voice_provider: str = "deepgram"  # "deepgram" | "cartesia" | etc.
    voice_id: str = "aura-2-thalia-en"
    is_active: bool = True
    calendar_id: str | None = None  # Optional link to calendar, e.g. "calendar[<id>]"
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict:
        """Convert to a plain dict for embedding inside a User DynamoDB item."""
        d = {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "system_prompt": self.system_prompt,
            "model": self.model,
            "temperature": str(self.temperature),
            "max_tokens": self.max_tokens,
            "voice_provider": self.voice_provider,
            "voice_id": self.voice_id,
            "is_active": self.is_active,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }
        if self.calendar_id is not None:
            d["calendar_id"] = self.calendar_id
        return d

    @classmethod
    def from_dict(cls, data: dict) -> "Agent":
        """Create an Agent from a dict stored in DynamoDB."""
        return cls(
            id=data["id"],
            name=data["name"],
            description=data["description"],
            system_prompt=data["system_prompt"],
            model=data.get("model", "gpt-4o-mini"),
            temperature=float(data.get("temperature", 0.7)),
            max_tokens=int(data.get("max_tokens", 150)),
            voice_provider=data.get("voice_provider", "deepgram"),
            voice_id=data.get("voice_id", "aura-2-thalia-en"),
            is_active=data.get("is_active", True),
            calendar_id=data.get("calendar_id"),
            created_at=data.get("created_at", ""),
            updated_at=data.get("updated_at", ""),
        )
