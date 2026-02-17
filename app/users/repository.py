from datetime import datetime, timezone

from boto3.dynamodb.conditions import Key

from app.database import get_dynamodb_table
from app.users.models import User


class UserRepository:
    """Handles all data access for User entities via DynamoDB."""

    def __init__(self) -> None:
        self.table = get_dynamodb_table()

    def get_by_id(self, user_id: str) -> User | None:
        response = self.table.get_item(Key={"id": user_id})
        item = response.get("Item")
        return User.from_dynamo_item(item) if item else None

    def get_by_email(self, email: str) -> User | None:
        response = self.table.query(
            IndexName="email-index",
            KeyConditionExpression=Key("email").eq(email),
        )
        items = response.get("Items", [])
        return User.from_dynamo_item(items[0]) if items else None

    def get_by_google_id(self, google_id: str) -> User | None:
        response = self.table.query(
            IndexName="google_id-index",
            KeyConditionExpression=Key("google_id").eq(google_id),
        )
        items = response.get("Items", [])
        return User.from_dynamo_item(items[0]) if items else None

    def create(self, user: User) -> User:
        user.updated_at = datetime.now(timezone.utc).isoformat()
        self.table.put_item(Item=user.to_dynamo_item())
        return user

    def update(self, user: User) -> User:
        user.updated_at = datetime.now(timezone.utc).isoformat()
        self.table.put_item(Item=user.to_dynamo_item())
        return user
