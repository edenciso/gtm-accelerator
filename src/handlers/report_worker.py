"""
Report Worker Lambda — runs ASYNC (invoked by trigger Lambda).

This is the heavy lifter: runs the full 5-agent orchestration pipeline
via Bedrock Claude Sonnet 4.5, stores results to S3 + DynamoDB.

NOT behind API Gateway — no 29s timeout limit. Has full 15-min Lambda timeout.
Invoked via lambda:InvokeAsync from generate_handler or demo handler.
"""

import os
import json
import logging
import traceback
import boto3
from datetime import datetime, timezone

from src.utils.dynamo import (
    get_engagement,
    update_report_progress,
    DecimalEncoder,
)
from src.agents.orchestrator import GTMSprintOrchestrator

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

s3_client = boto3.client("s3")


def worker_handler(event, context):
    """
    Async worker entry point.

    Event payload:
    {
        "engagement_id": "abc123",
        "report_id": "rpt456",
        "company_name": "Acme AI"
    }
    """
    engagement_id = event.get("engagement_id")
    report_id = event.get("report_id")
    company_name = event.get("company_name", "unknown")

    logger.info(
        f"Worker started: engagement={engagement_id}, report={report_id}, "
        f"remaining_ms={context.get_remaining_time_in_millis()}"
    )

    try:
        # Run the full multi-agent orchestration (2-5 minutes)
        orchestrator = GTMSprintOrchestrator(engagement_id, report_id)
        report_output = orchestrator.run()

        # Store to S3
        bucket = os.environ.get("REPORT_BUCKET")
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        safe_company = company_name.replace(" ", "_").lower()[:50]

        json_key = f"reports/{engagement_id}/{report_id}/{safe_company}_report_{timestamp}.json"
        s3_client.put_object(
            Bucket=bucket,
            Key=json_key,
            Body=json.dumps(report_output, cls=DecimalEncoder, indent=2),
            ContentType="application/json",
        )

        md_key = f"reports/{engagement_id}/{report_id}/{safe_company}_report_{timestamp}.md"
        s3_client.put_object(
            Bucket=bucket,
            Key=md_key,
            Body=report_output.get("report_markdown", ""),
            ContentType="text/markdown",
        )

        # Update DynamoDB with S3 locations + completed status
        update_report_progress(
            engagement_id,
            report_id,
            progress=100,
            section="stored_to_s3",
            status="completed",
            s3_key=json_key,
            report_data={
                "json_s3_key": json_key,
                "markdown_s3_key": md_key,
                "company_name": report_output.get("company_name"),
                "generated_at": report_output.get("generated_at"),
                "sections_generated": list(report_output.get("sections", {}).keys()),
                "scorecard_overall_score": report_output.get("sections", {})
                    .get("scorecard", {}).get("overall_score"),
                "scorecard_grade": report_output.get("sections", {})
                    .get("scorecard", {}).get("overall_grade"),
            },
        )

        logger.info(f"Worker complete: report={report_id}, s3={json_key}")
        return {"status": "completed", "report_id": report_id}

    except Exception as e:
        error_detail = traceback.format_exc()
        logger.error(f"Worker FAILED:\n{error_detail}")
        try:
            update_report_progress(
                engagement_id,
                report_id,
                progress=0,
                status="failed",
                section=f"error: {str(e)[:200]}",
                report_data={
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "traceback": error_detail[-500:],
                },
            )
        except Exception:
            logger.error("Failed to update error status in DynamoDB")
        raise  # Re-raise so Lambda marks invocation as failed
