"""
Lambda handlers for report generation — ASYNC pattern.

generate_handler: validates data, creates record, invokes worker async, returns immediately.
get_report_handler / status_handler: read from DynamoDB for completed results.

The actual 5-agent pipeline runs in report_worker.py (separate Lambda, 15-min timeout).
"""

import os
import uuid
import json
import logging
import boto3

from src.utils.api import success, error, get_path_param
from src.utils.dynamo import (
    get_engagement,
    get_all_data,
    create_report_record,
    get_report,
    get_report_status,
)

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

lambda_client = boto3.client("lambda")
s3_client = boto3.client("s3")


def generate_handler(event, context):
    """
    POST /engagements/{engagement_id}/report/generate

    Returns immediately with report_id. The heavy work runs async in ReportWorkerFunction.
    Client polls GET /report/status until status=completed, then GET /report for downloads.
    """
    try:
        engagement_id = get_path_param(event, "engagement_id")
        if not engagement_id:
            return error("engagement_id is required", 400)

        engagement = get_engagement(engagement_id)
        if not engagement:
            return error("Engagement not found", 404)

        # Check minimum data exists
        all_data = get_all_data(engagement_id)
        available_types = list(all_data.keys())
        logger.info(f"Available data types: {available_types}")

        if "gtm" not in available_types:
            return error(
                "GTM operating model data is required. POST to /engagements/{id}/data/gtm first.",
                400,
                {"available_data": available_types, "required": ["gtm"]},
            )

        # Create report record
        report_id = str(uuid.uuid4())[:12]
        create_report_record(engagement_id, report_id)

        # Invoke worker Lambda ASYNC (InvocationType=Event fires and forgets)
        worker_fn = os.environ["WORKER_FUNCTION_NAME"]
        payload = {
            "engagement_id": engagement_id,
            "report_id": report_id,
            "company_name": engagement.get("company_name", ""),
        }

        lambda_client.invoke(
            FunctionName=worker_fn,
            InvocationType="Event",  # ASYNC — returns 202 immediately
            Payload=json.dumps(payload),
        )

        logger.info(f"Async worker invoked: engagement={engagement_id}, report={report_id}")

        return success(
            {
                "message": "Report generation started",
                "engagement_id": engagement_id,
                "report_id": report_id,
                "status": "generating",
                "poll_status": f"/engagements/{engagement_id}/report/status",
                "get_report": f"/engagements/{engagement_id}/report",
                "estimated_time_seconds": 120,
            },
            202,
        )

    except Exception as e:
        logger.error(f"Error triggering report: {e}", exc_info=True)
        return error(f"Failed to start report generation: {str(e)}", 500)


def get_report_handler(event, context):
    """GET /engagements/{engagement_id}/report — Get the latest report + download URLs."""
    try:
        engagement_id = get_path_param(event, "engagement_id")
        if not engagement_id:
            return error("engagement_id is required", 400)

        report = get_report(engagement_id)
        if not report:
            return error("No report found for this engagement", 404)

        # Generate fresh presigned URLs if completed
        if report.get("status") == "completed" and report.get("report_data"):
            bucket = os.environ.get("REPORT_BUCKET")
            report_data = report["report_data"]
            downloads = {}

            for key_field, label in [
                ("json_s3_key", "json_report"),
                ("markdown_s3_key", "markdown_report"),
            ]:
                s3_key = report_data.get(key_field)
                if s3_key:
                    downloads[label] = s3_client.generate_presigned_url(
                        "get_object",
                        Params={"Bucket": bucket, "Key": s3_key},
                        ExpiresIn=3600,
                    )
            report["downloads"] = downloads

        return success({"report": report})

    except Exception as e:
        logger.error(f"Error getting report: {e}")
        return error(str(e), 500)


def status_handler(event, context):
    """GET /engagements/{engagement_id}/report/status — Poll generation progress."""
    try:
        engagement_id = get_path_param(event, "engagement_id")
        if not engagement_id:
            return error("engagement_id is required", 400)

        status = get_report_status(engagement_id)
        if not status:
            return error("No report found for this engagement", 404)

        return success({"status": status})

    except Exception as e:
        logger.error(f"Error getting report status: {e}")
        return error(str(e), 500)
