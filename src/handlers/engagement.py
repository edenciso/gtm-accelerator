"""
Lambda handlers for engagement lifecycle management.
"""

import uuid
import logging
from src.utils.api import success, error, parse_body, get_path_param
from src.utils.dynamo import create_engagement, get_engagement

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


def create_handler(event, context):
    """POST /engagements — Create a new client engagement."""
    try:
        body = parse_body(event)

        # Validate required fields
        if not body.get("company_name"):
            return error("company_name is required", 400)
        if not body.get("contact_email"):
            return error("contact_email is required", 400)

        engagement_id = str(uuid.uuid4())[:12]

        engagement = create_engagement(engagement_id, {
            "company_name": body["company_name"],
            "contact_email": body["contact_email"],
            "contact_name": body.get("contact_name", ""),
            "stage": body.get("stage", ""),
            "arr_range": body.get("arr_range", ""),
        })

        logger.info(f"Created engagement {engagement_id} for {body['company_name']}")

        return success({
            "message": "Engagement created successfully",
            "engagement_id": engagement_id,
            "engagement": engagement,
            "next_steps": {
                "1_ingest_gtm": f"/engagements/{engagement_id}/data/gtm",
                "2_ingest_sales": f"/engagements/{engagement_id}/data/sales",
                "3_ingest_financials": f"/engagements/{engagement_id}/data/financials",
                "4_ingest_tools": f"/engagements/{engagement_id}/data/tools",
                "5_generate_report": f"/engagements/{engagement_id}/report/generate",
            },
        }, 201)

    except Exception as e:
        logger.error(f"Error creating engagement: {e}")
        return error(str(e), 500)


def get_handler(event, context):
    """GET /engagements/{engagement_id} — Get engagement details."""
    try:
        engagement_id = get_path_param(event, "engagement_id")
        if not engagement_id:
            return error("engagement_id is required", 400)

        engagement = get_engagement(engagement_id)
        if not engagement:
            return error("Engagement not found", 404)

        return success({"engagement": engagement})

    except Exception as e:
        logger.error(f"Error getting engagement: {e}")
        return error(str(e), 500)
