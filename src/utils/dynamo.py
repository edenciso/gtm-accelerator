"""
DynamoDB helper utilities for the GTM Accelerator Sprint.
Single-table design with PK/SK patterns for all entities.
"""

import os
import json
import boto3
from datetime import datetime, timezone
from decimal import Decimal
from boto3.dynamodb.conditions import Key

dynamodb = boto3.resource("dynamodb")


def _get_table(table_env_var: str):
    table_name = os.environ.get(table_env_var)
    if not table_name:
        raise ValueError(f"Environment variable {table_env_var} not set")
    return dynamodb.Table(table_name)


def data_table():
    return _get_table("DATA_TABLE")


def reports_table():
    return _get_table("REPORTS_TABLE")


def engagements_table():
    return _get_table("ENGAGEMENTS_TABLE")


class DecimalEncoder(json.JSONEncoder):
    """JSON encoder that handles Decimal types from DynamoDB."""
    def default(self, obj):
        if isinstance(obj, Decimal):
            if obj % 1 == 0:
                return int(obj)
            return float(obj)
        return super().default(obj)


def to_dynamo(data: dict) -> dict:
    """Convert Python dict to DynamoDB-safe format (handle floats -> Decimal)."""
    return json.loads(json.dumps(data), parse_float=Decimal)


def from_dynamo(item: dict) -> dict:
    """Convert DynamoDB item to regular Python dict."""
    return json.loads(json.dumps(item, cls=DecimalEncoder))


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# ============================================================
# Engagement Operations
# ============================================================
def create_engagement(engagement_id: str, data: dict) -> dict:
    table = engagements_table()
    item = {
        "PK": f"ENG#{engagement_id}",
        "SK": "META",
        "engagement_id": engagement_id,
        "company_name": data["company_name"],
        "contact_email": data["contact_email"],
        "contact_name": data.get("contact_name", ""),
        "stage": data.get("stage", ""),
        "arr_range": data.get("arr_range", ""),
        "status": "created",
        "data_ingested": {
            "gtm": False,
            "sales": False,
            "financials": False,
            "tools": False,
        },
        "created_at": now_iso(),
        "updated_at": now_iso(),
    }
    table.put_item(Item=to_dynamo(item))
    return from_dynamo(item)


def get_engagement(engagement_id: str) -> dict | None:
    table = engagements_table()
    resp = table.get_item(Key={"PK": f"ENG#{engagement_id}", "SK": "META"})
    item = resp.get("Item")
    return from_dynamo(item) if item else None


def update_engagement_status(engagement_id: str, status: str, data_type: str = None):
    table = engagements_table()
    update_expr = "SET #s = :s, updated_at = :u"
    expr_values = {":s": status, ":u": now_iso()}
    expr_names = {"#s": "status"}

    if data_type:
        update_expr += f", data_ingested.{data_type} = :t"
        expr_values[":t"] = True

    table.update_item(
        Key={"PK": f"ENG#{engagement_id}", "SK": "META"},
        UpdateExpression=update_expr,
        ExpressionAttributeValues=to_dynamo(expr_values),
        ExpressionAttributeNames=expr_names,
    )


# ============================================================
# Data Ingestion Operations
# ============================================================
def store_data(engagement_id: str, data_type: str, data: dict):
    """Store ingested JSON data for a specific engagement and data type."""
    table = data_table()
    item = {
        "PK": f"ENG#{engagement_id}",
        "SK": f"DATA#{data_type}",
        "GSI1PK": f"TYPE#{data_type}",
        "GSI1SK": f"ENG#{engagement_id}",
        "engagement_id": engagement_id,
        "data_type": data_type,
        "payload": data,
        "ingested_at": now_iso(),
    }
    table.put_item(Item=to_dynamo(item))
    update_engagement_status(engagement_id, "data_ingested", data_type)


def get_data(engagement_id: str, data_type: str) -> dict | None:
    """Retrieve stored data for a given engagement and type."""
    table = data_table()
    resp = table.get_item(
        Key={"PK": f"ENG#{engagement_id}", "SK": f"DATA#{data_type}"}
    )
    item = resp.get("Item")
    return from_dynamo(item).get("payload") if item else None


def get_all_data(engagement_id: str) -> dict:
    """Retrieve all data types for an engagement."""
    table = data_table()
    resp = table.query(
        KeyConditionExpression=Key("PK").eq(f"ENG#{engagement_id}")
        & Key("SK").begins_with("DATA#")
    )
    result = {}
    for item in resp.get("Items", []):
        item = from_dynamo(item)
        result[item["data_type"]] = item.get("payload", {})
    return result


# ============================================================
# Report Operations
# ============================================================
def create_report_record(engagement_id: str, report_id: str) -> dict:
    table = reports_table()
    item = {
        "PK": f"ENG#{engagement_id}",
        "SK": f"RPT#{report_id}",
        "engagement_id": engagement_id,
        "report_id": report_id,
        "status": "generating",
        "progress": 0,
        "sections_completed": [],
        "created_at": now_iso(),
        "updated_at": now_iso(),
    }
    table.put_item(Item=to_dynamo(item))
    return from_dynamo(item)


def update_report_progress(
    engagement_id: str, report_id: str, progress: int, section: str = None,
    status: str = None, s3_key: str = None, report_data: dict = None
):
    table = reports_table()
    update_parts = ["updated_at = :u", "progress = :p"]
    expr_values = {":u": now_iso(), ":p": progress}

    if section:
        update_parts.append("sections_completed = list_append(if_not_exists(sections_completed, :empty), :sec)")
        expr_values[":sec"] = [section]
        expr_values[":empty"] = []

    if status:
        update_parts.append("#s = :s")
        expr_values[":s"] = status

    if s3_key:
        update_parts.append("s3_key = :sk")
        expr_values[":sk"] = s3_key

    if report_data:
        update_parts.append("report_data = :rd")
        expr_values[":rd"] = report_data

    expr_names = {}
    if status:
        expr_names["#s"] = "status"

    kwargs = {
        "Key": {"PK": f"ENG#{engagement_id}", "SK": f"RPT#{report_id}"},
        "UpdateExpression": "SET " + ", ".join(update_parts),
        "ExpressionAttributeValues": to_dynamo(expr_values),
    }
    if expr_names:
        kwargs["ExpressionAttributeNames"] = expr_names

    table.update_item(**kwargs)


def get_report(engagement_id: str, report_id: str = None) -> dict | None:
    table = reports_table()
    if report_id:
        resp = table.get_item(
            Key={"PK": f"ENG#{engagement_id}", "SK": f"RPT#{report_id}"}
        )
        item = resp.get("Item")
        return from_dynamo(item) if item else None
    else:
        resp = table.query(
            KeyConditionExpression=Key("PK").eq(f"ENG#{engagement_id}")
            & Key("SK").begins_with("RPT#"),
            ScanIndexForward=False,
            Limit=1,
        )
        items = resp.get("Items", [])
        return from_dynamo(items[0]) if items else None


def get_report_status(engagement_id: str) -> dict | None:
    report = get_report(engagement_id)
    if not report:
        return None
    return {
        "report_id": report.get("report_id"),
        "status": report.get("status"),
        "progress": report.get("progress"),
        "sections_completed": report.get("sections_completed", []),
        "updated_at": report.get("updated_at"),
    }
