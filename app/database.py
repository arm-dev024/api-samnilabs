import boto3
from app.config import settings


def get_dynamodb_resource():
    """Get a boto3 DynamoDB resource configured for local or AWS."""
    kwargs = {
        "region_name": settings.db_region,
    }
    if settings.db_endpoint_url:
        kwargs["endpoint_url"] = str(settings.db_endpoint_url)
        kwargs["aws_access_key_id"] = settings.db_aws_access_key_id
        kwargs["aws_secret_access_key"] = settings.db_aws_secret_access_key.get_secret_value()

    return boto3.resource("dynamodb", **kwargs)


def get_dynamodb_table():
    """Get the users DynamoDB table resource."""
    dynamodb = get_dynamodb_resource()
    return dynamodb.Table(settings.db_table_name)


def create_users_table_if_not_exists():
    """Create the users table in DynamoDB if it doesn't already exist."""
    dynamodb = get_dynamodb_resource()
    existing_tables = dynamodb.meta.client.list_tables()["TableNames"]

    if settings.db_table_name in existing_tables:
        return

    table = dynamodb.create_table(
        TableName=settings.db_table_name,
        KeySchema=[
            {"AttributeName": "id", "KeyType": "HASH"},
        ],
        AttributeDefinitions=[
            {"AttributeName": "id", "AttributeType": "S"},
            {"AttributeName": "email", "AttributeType": "S"},
            {"AttributeName": "google_id", "AttributeType": "S"},
        ],
        GlobalSecondaryIndexes=[
            {
                "IndexName": "email-index",
                "KeySchema": [
                    {"AttributeName": "email", "KeyType": "HASH"},
                ],
                "Projection": {"ProjectionType": "ALL"},
                "ProvisionedThroughput": {
                    "ReadCapacityUnits": 5,
                    "WriteCapacityUnits": 5,
                },
            },
            {
                "IndexName": "google_id-index",
                "KeySchema": [
                    {"AttributeName": "google_id", "KeyType": "HASH"},
                ],
                "Projection": {"ProjectionType": "ALL"},
                "ProvisionedThroughput": {
                    "ReadCapacityUnits": 5,
                    "WriteCapacityUnits": 5,
                },
            },
        ],
        ProvisionedThroughput={
            "ReadCapacityUnits": 5,
            "WriteCapacityUnits": 5,
        },
    )
    table.wait_until_exists()
