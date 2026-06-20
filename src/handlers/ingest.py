"""
Lambda handlers for client data ingestion.
Each handler accepts JSON data, validates it, and stores in DynamoDB.
"""

import logging
from src.utils.api import success, error, parse_body, get_path_param
from src.utils.dynamo import store_data, get_engagement
from src.schemas.data_schemas import (
    GTM_OPERATING_MODEL_SCHEMA,
    SALES_TELEMETRY_SCHEMA,
    FINANCIALS_SCHEMA,
    TOOL_STACK_SCHEMA,
    validate_basic,
)

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


def _ingest_handler(event, data_type: str, schema: dict):
    """Generic ingestion handler."""
    try:
        engagement_id = get_path_param(event, "engagement_id")
        if not engagement_id:
            return error("engagement_id is required", 400)

        # Verify engagement exists
        engagement = get_engagement(engagement_id)
        if not engagement:
            return error("Engagement not found", 404)

        body = parse_body(event)
        if not body:
            return error("Request body is required", 400)

        # Basic validation
        validation_errors = validate_basic(body, schema)
        if validation_errors:
            return error(
                "Validation failed",
                400,
                {"validation_errors": validation_errors},
            )

        # Store data
        store_data(engagement_id, data_type, body)

        logger.info(f"Ingested {data_type} data for engagement {engagement_id}")

        return success({
            "message": f"{data_type} data ingested successfully",
            "engagement_id": engagement_id,
            "data_type": data_type,
        })

    except Exception as e:
        logger.error(f"Error ingesting {data_type} data: {e}")
        return error(str(e), 500)


def gtm_data_handler(event, context):
    """POST /engagements/{id}/data/gtm — Ingest GTM operating model data."""
    return _ingest_handler(event, "gtm", GTM_OPERATING_MODEL_SCHEMA)


def sales_data_handler(event, context):
    """POST /engagements/{id}/data/sales — Ingest sales telemetry data."""
    return _ingest_handler(event, "sales", SALES_TELEMETRY_SCHEMA)


def financials_data_handler(event, context):
    """POST /engagements/{id}/data/financials — Ingest financial data."""
    return _ingest_handler(event, "financials", FINANCIALS_SCHEMA)


def tool_stack_handler(event, context):
    """POST /engagements/{id}/data/tools — Ingest tool stack inventory."""
    return _ingest_handler(event, "tools", TOOL_STACK_SCHEMA)
