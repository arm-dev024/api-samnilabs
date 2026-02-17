import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone

from app.agents.models import Agent


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
    subscription_plan_id: str | None = None
    stripe_customer_id: str | None = None
    stripe_subscription_id: str | None = None
    subscription_status: str = "none"  # "none" | "active" | "canceled" | "past_due"
    subscribed_at: str | None = None
    agents: list[Agent] = field(default_factory=list)
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
        if self.subscription_plan_id is not None:
            item["subscription_plan_id"] = self.subscription_plan_id
        if self.stripe_customer_id is not None:
            item["stripe_customer_id"] = self.stripe_customer_id
        if self.stripe_subscription_id is not None:
            item["stripe_subscription_id"] = self.stripe_subscription_id
        item["subscription_status"] = self.subscription_status
        if self.subscribed_at is not None:
            item["subscribed_at"] = self.subscribed_at
        if self.agents:
            item["agents"] = [agent.to_dict() for agent in self.agents]
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
            subscription_plan_id=item.get("subscription_plan_id"),
            stripe_customer_id=item.get("stripe_customer_id"),
            stripe_subscription_id=item.get("stripe_subscription_id"),
            subscription_status=item.get("subscription_status", "none"),
            subscribed_at=item.get("subscribed_at"),
            agents=[Agent.from_dict(a) for a in item.get("agents", [])],
            created_at=item.get("created_at", ""),
            updated_at=item.get("updated_at", ""),
        )
