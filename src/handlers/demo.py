"""
Demo handler — One-click demo for FDE live client sessions.
Loads sample data, triggers async report generation via worker Lambda.
"""

import os
import uuid
import json
import logging
import boto3

from src.utils.api import success, error, parse_body
from src.utils.dynamo import (
    create_engagement,
    store_data,
    create_report_record,
)
from sample_data.demo_data import (
    SAMPLE_ENGAGEMENT,
    SAMPLE_GTM_DATA,
    SAMPLE_SALES_DATA,
    SAMPLE_FINANCIALS,
    SAMPLE_TOOLS,
)

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

lambda_client = boto3.client("lambda")


def run_demo_handler(event, context):
    """
    POST /demo/run

    One-click demo:
    1. Creates sample engagement + loads all sample data
    2. Invokes worker Lambda async for report generation
    3. Returns immediately with engagement_id + report_id for polling

    Optional body: {"company_name": "Custom Name"} to override demo company
    """
    try:
        body = parse_body(event) if event.get("body") else {}

        # Allow overriding demo company name
        engagement_data = SAMPLE_ENGAGEMENT.copy()
        if body.get("company_name"):
            engagement_data["company_name"] = body["company_name"]
            engagement_data["contact_email"] = body.get(
                "contact_email", "demo@example.com"
            )

        # Create engagement
        engagement_id = f"demo-{str(uuid.uuid4())[:8]}"
        create_engagement(engagement_id, engagement_data)
        logger.info(f"Demo: Created engagement {engagement_id}")

        # Load all data sections
        gtm_data = body.get("custom_gtm_data", SAMPLE_GTM_DATA)
        sales_data = body.get("custom_sales_data", SAMPLE_SALES_DATA)
        financials_data = body.get("custom_financials_data", SAMPLE_FINANCIALS)
        tools_data = body.get("custom_tools_data", SAMPLE_TOOLS)

        store_data(engagement_id, "gtm", gtm_data)
        store_data(engagement_id, "sales", sales_data)
        store_data(engagement_id, "financials", financials_data)
        store_data(engagement_id, "tools", tools_data)
        logger.info("Demo: All sample data loaded")

        # Create report record
        report_id = f"rpt-{str(uuid.uuid4())[:8]}"
        create_report_record(engagement_id, report_id)

        # Invoke worker Lambda ASYNC
        worker_fn = os.environ["WORKER_FUNCTION_NAME"]
        payload = {
            "engagement_id": engagement_id,
            "report_id": report_id,
            "company_name": engagement_data["company_name"],
        }

        lambda_client.invoke(
            FunctionName=worker_fn,
            InvocationType="Event",
            Payload=json.dumps(payload),
        )

        logger.info(f"Demo: Async worker invoked for report {report_id}")

        return success(
            {
                "message": "Demo started — report generating in background",
                "engagement_id": engagement_id,
                "report_id": report_id,
                "company_name": engagement_data["company_name"],
                "status": "generating",
                "poll_status": f"/engagements/{engagement_id}/report/status",
                "get_report": f"/engagements/{engagement_id}/report",
                "estimated_time_seconds": 120,
                "instructions": "Poll the status endpoint every 10-15 seconds until status=completed, then call get_report for download URLs.",
            },
            202,
        )

    except Exception as e:
        logger.error(f"Demo failed: {e}", exc_info=True)
        return error(f"Demo setup failed: {str(e)}", 500)
