"""
Multi-Agent Orchestrator for GTM Accelerator Value Sprint.

Runs 5 specialized agents sequentially via Bedrock Claude Sonnet 4.5.
Fails fast with detailed error info if any agent fails.

Architecture:
  Agent 1: GTM Health Scorecard      → JSON
  Agent 2: Architecture Blueprint     → JSON
  Agent 3: Unit Economics Model       → JSON
  Agent 4: Implementation Roadmap     → JSON
  Agent 5: Report Compiler            → Markdown
"""

import json
import logging
import traceback
from datetime import datetime, timezone

from src.utils.bedrock import invoke_claude, invoke_claude_json
from src.utils.dynamo import (
    get_all_data,
    update_report_progress,
    update_engagement_status,
)
from src.templates.agent_prompts import (
    GTM_HEALTH_SCORECARD_SYSTEM,
    GTM_HEALTH_SCORECARD_USER,
    GTM_ARCHITECTURE_SYSTEM,
    GTM_ARCHITECTURE_USER,
    UNIT_ECONOMICS_SYSTEM,
    UNIT_ECONOMICS_USER,
    IMPLEMENTATION_ROADMAP_SYSTEM,
    IMPLEMENTATION_ROADMAP_USER,
    REPORT_COMPILER_SYSTEM,
    REPORT_COMPILER_USER,
)

logger = logging.getLogger(__name__)


class GTMSprintOrchestrator:
    """
    Orchestrates the multi-agent workflow for generating the
    GTM Accelerator Value Sprint Phase 1 deliverable.
    """

    def __init__(self, engagement_id: str, report_id: str):
        self.engagement_id = engagement_id
        self.report_id = report_id
        self.results = {}

    def _update(self, progress: int, section: str, status: str = "generating"):
        update_report_progress(
            self.engagement_id, self.report_id,
            progress=progress, section=section, status=status,
        )

    def _json_str(self, data) -> str:
        if isinstance(data, str):
            return data
        return json.dumps(data, indent=2, default=str)

    def _run_agent(self, name: str, progress: int, invoke_fn, **kwargs):
        """Run a single agent with consistent logging and error handling."""
        logger.info(f"Agent [{name}] starting...")
        try:
            result = invoke_fn(**kwargs)
            self._update(progress, name)
            logger.info(f"Agent [{name}] completed successfully")
            return result
        except Exception as e:
            tb = traceback.format_exc()
            logger.error(f"Agent [{name}] FAILED:\n{tb}")
            self._update(progress, f"{name}_error", status="generating")
            raise RuntimeError(f"Agent [{name}] failed: {e}") from e

    def run(self) -> dict:
        """Execute the full multi-agent pipeline."""
        logger.info(f"Orchestration starting: engagement={self.engagement_id}")

        # Load all client data
        all_data = get_all_data(self.engagement_id)
        gtm_data = self._json_str(all_data.get("gtm", {}))
        sales_data = self._json_str(all_data.get("sales", {}))
        financials_data = self._json_str(all_data.get("financials", {}))
        tools_data = self._json_str(all_data.get("tools", {}))

        company_name = "Client"
        gtm_raw = all_data.get("gtm", {})
        if isinstance(gtm_raw, dict):
            profile = gtm_raw.get("company_profile", {})
            if isinstance(profile, dict):
                company_name = profile.get("name", "Client")

        logger.info(f"Data loaded: {list(all_data.keys())} for company={company_name}")
        self._update(5, "data_loaded")

        # ── Agent 1: GTM Health Scorecard ──
        scorecard = self._run_agent(
            "gtm_health_scorecard", 20,
            invoke_claude_json,
            system_prompt=GTM_HEALTH_SCORECARD_SYSTEM,
            user_message=GTM_HEALTH_SCORECARD_USER.format(
                gtm_data=gtm_data,
                sales_data=sales_data,
                financials_data=financials_data,
                tools_data=tools_data,
            ),
            max_tokens=16000,
            temperature=0.3,
        )
        self.results["scorecard"] = scorecard
        scorecard_json = self._json_str(scorecard)

        # ── Agent 2: Architecture Blueprint ──
        architecture = self._run_agent(
            "architecture_blueprint", 40,
            invoke_claude_json,
            system_prompt=GTM_ARCHITECTURE_SYSTEM,
            user_message=GTM_ARCHITECTURE_USER.format(
                gtm_data=gtm_data,
                tools_data=tools_data,
                scorecard_results=scorecard_json,
            ),
            max_tokens=16000,
            temperature=0.3,
        )
        self.results["architecture"] = architecture
        architecture_json = self._json_str(architecture)

        # ── Agent 3: Unit Economics Model ──
        economics = self._run_agent(
            "unit_economics_model", 60,
            invoke_claude_json,
            system_prompt=UNIT_ECONOMICS_SYSTEM,
            user_message=UNIT_ECONOMICS_USER.format(
                financials_data=financials_data,
                gtm_data=gtm_data,
                sales_data=sales_data,
                scorecard_results=scorecard_json,
            ),
            max_tokens=16000,
            temperature=0.2,
        )
        self.results["economics"] = economics
        economics_json = self._json_str(economics)

        # ── Agent 4: Implementation Roadmap ──
        roadmap = self._run_agent(
            "implementation_roadmap", 80,
            invoke_claude_json,
            system_prompt=IMPLEMENTATION_ROADMAP_SYSTEM,
            user_message=IMPLEMENTATION_ROADMAP_USER.format(
                gtm_data=gtm_data,
                scorecard_results=scorecard_json,
                architecture_results=architecture_json,
                economics_results=economics_json,
                tools_data=tools_data,
            ),
            max_tokens=16000,
            temperature=0.3,
        )
        self.results["roadmap"] = roadmap
        roadmap_json = self._json_str(roadmap)

        # ── Agent 5: Report Compiler (Markdown, not JSON) ──
        report_date = datetime.now(timezone.utc).strftime("%B %d, %Y")
        report_markdown = self._run_agent(
            "report_compiled", 95,
            invoke_claude,
            system_prompt=REPORT_COMPILER_SYSTEM,
            user_message=REPORT_COMPILER_USER.format(
                company_name=company_name,
                report_date=report_date,
                scorecard_json=scorecard_json,
                architecture_json=architecture_json,
                economics_json=economics_json,
                roadmap_json=roadmap_json,
            ),
            max_tokens=16384,
            temperature=0.4,
        )
        self.results["report_markdown"] = report_markdown

        # Package final output
        final_output = {
            "engagement_id": self.engagement_id,
            "report_id": self.report_id,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "company_name": company_name,
            "sections": {
                "scorecard": self.results["scorecard"],
                "architecture": self.results["architecture"],
                "economics": self.results["economics"],
                "roadmap": self.results["roadmap"],
            },
            "report_markdown": self.results["report_markdown"],
        }

        self._update(100, "complete", status="completed")
        update_engagement_status(self.engagement_id, "report_generated")
        logger.info(f"Orchestration complete: engagement={self.engagement_id}")
        return final_output
