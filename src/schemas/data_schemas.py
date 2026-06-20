"""
JSON Schema definitions for client data ingestion.
These define the expected structure for each data category
that the client provides for the GTM Sprint analysis.
"""

GTM_OPERATING_MODEL_SCHEMA = {
    "type": "object",
    "required": ["company_profile", "gtm_model", "sales_process"],
    "properties": {
        "company_profile": {
            "type": "object",
            "required": ["name", "industry", "stage", "arr"],
            "properties": {
                "name": {"type": "string"},
                "industry": {"type": "string"},
                "sub_vertical": {"type": "string"},
                "stage": {"type": "string", "enum": ["seed", "series_a", "series_b", "series_c", "series_d_plus"]},
                "arr": {"type": "number", "description": "Annual Recurring Revenue in USD"},
                "mrr": {"type": "number"},
                "headcount": {"type": "integer"},
                "gtm_headcount": {"type": "integer"},
                "founding_year": {"type": "integer"},
                "hq_location": {"type": "string"},
                "target_markets": {"type": "array", "items": {"type": "string"}},
            },
        },
        "gtm_model": {
            "type": "object",
            "required": ["motion_type"],
            "properties": {
                "motion_type": {
                    "type": "string",
                    "enum": ["product_led", "sales_led", "hybrid", "partner_led", "community_led"],
                },
                "primary_channel": {"type": "string"},
                "secondary_channels": {"type": "array", "items": {"type": "string"}},
                "icp_definition": {
                    "type": "object",
                    "properties": {
                        "company_size": {"type": "string"},
                        "industries": {"type": "array", "items": {"type": "string"}},
                        "titles": {"type": "array", "items": {"type": "string"}},
                        "budget_range": {"type": "string"},
                        "pain_points": {"type": "array", "items": {"type": "string"}},
                    },
                },
                "personas": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "title": {"type": "string"},
                            "role_in_buying": {"type": "string"},
                            "key_concerns": {"type": "array", "items": {"type": "string"}},
                        },
                    },
                },
                "pricing_model": {"type": "string"},
                "avg_deal_size": {"type": "number"},
                "avg_sales_cycle_days": {"type": "integer"},
                "win_rate": {"type": "number"},
                "expansion_rate": {"type": "number"},
            },
        },
        "sales_process": {
            "type": "object",
            "properties": {
                "stages": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string"},
                            "conversion_rate": {"type": "number"},
                            "avg_days_in_stage": {"type": "integer"},
                            "activities": {"type": "array", "items": {"type": "string"}},
                        },
                    },
                },
                "lead_sources": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "source": {"type": "string"},
                            "volume_monthly": {"type": "integer"},
                            "conversion_rate": {"type": "number"},
                            "cac": {"type": "number"},
                        },
                    },
                },
                "bottlenecks": {"type": "array", "items": {"type": "string"}},
                "automation_level": {
                    "type": "string",
                    "enum": ["none", "basic", "moderate", "advanced", "ai_native"],
                },
            },
        },
        "competitive_landscape": {
            "type": "object",
            "properties": {
                "direct_competitors": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string"},
                            "positioning": {"type": "string"},
                            "strengths": {"type": "array", "items": {"type": "string"}},
                            "weaknesses": {"type": "array", "items": {"type": "string"}},
                        },
                    },
                },
                "differentiation": {"type": "array", "items": {"type": "string"}},
                "moat_assessment": {"type": "string"},
            },
        },
    },
}

SALES_TELEMETRY_SCHEMA = {
    "type": "object",
    "required": ["pipeline"],
    "properties": {
        "pipeline": {
            "type": "object",
            "properties": {
                "total_pipeline_value": {"type": "number"},
                "weighted_pipeline": {"type": "number"},
                "pipeline_coverage_ratio": {"type": "number"},
                "stages": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string"},
                            "deal_count": {"type": "integer"},
                            "total_value": {"type": "number"},
                            "avg_age_days": {"type": "integer"},
                            "conversion_to_next": {"type": "number"},
                        },
                    },
                },
            },
        },
        "velocity_metrics": {
            "type": "object",
            "properties": {
                "avg_deal_velocity_days": {"type": "integer"},
                "time_to_first_value_days": {"type": "integer"},
                "monthly_meetings_booked": {"type": "integer"},
                "meeting_to_opp_rate": {"type": "number"},
                "demo_to_close_rate": {"type": "number"},
                "response_time_hours": {"type": "number"},
            },
        },
        "rep_performance": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "rep_id": {"type": "string"},
                    "quota": {"type": "number"},
                    "attainment_pct": {"type": "number"},
                    "deals_closed": {"type": "integer"},
                    "avg_deal_size": {"type": "number"},
                    "win_rate": {"type": "number"},
                    "activities_per_day": {"type": "number"},
                },
            },
        },
        "cohort_metrics": {
            "type": "object",
            "properties": {
                "nrr_pct": {"type": "number", "description": "Net Revenue Retention %"},
                "gross_churn_pct": {"type": "number"},
                "expansion_revenue_pct": {"type": "number"},
                "logo_retention_pct": {"type": "number"},
                "avg_contract_length_months": {"type": "integer"},
            },
        },
    },
}

FINANCIALS_SCHEMA = {
    "type": "object",
    "required": ["unit_economics"],
    "properties": {
        "unit_economics": {
            "type": "object",
            "properties": {
                "cac": {"type": "number", "description": "Customer Acquisition Cost"},
                "cac_blended": {"type": "number"},
                "cac_sales_led": {"type": "number"},
                "cac_product_led": {"type": "number"},
                "ltv": {"type": "number", "description": "Lifetime Value"},
                "ltv_cac_ratio": {"type": "number"},
                "payback_months": {"type": "number"},
                "gross_margin_pct": {"type": "number"},
                "contribution_margin_pct": {"type": "number"},
                "magic_number": {"type": "number"},
                "burn_multiple": {"type": "number"},
            },
        },
        "revenue_breakdown": {
            "type": "object",
            "properties": {
                "new_arr": {"type": "number"},
                "expansion_arr": {"type": "number"},
                "churned_arr": {"type": "number"},
                "net_new_arr": {"type": "number"},
                "services_revenue": {"type": "number"},
            },
        },
        "cost_structure": {
            "type": "object",
            "properties": {
                "total_gtm_spend": {"type": "number"},
                "sales_comp": {"type": "number"},
                "marketing_spend": {"type": "number"},
                "tool_subscriptions": {"type": "number"},
                "hosting_ai_costs": {"type": "number"},
                "total_cogs": {"type": "number"},
                "gross_margin_dollars": {"type": "number"},
            },
        },
        "ai_specific_costs": {
            "type": "object",
            "properties": {
                "llm_api_monthly": {"type": "number"},
                "ai_tool_subscriptions_monthly": {"type": "number"},
                "ai_headcount_costs_monthly": {"type": "number"},
                "total_ai_spend_monthly": {"type": "number"},
                "ai_spend_as_pct_revenue": {"type": "number"},
            },
        },
    },
}

TOOL_STACK_SCHEMA = {
    "type": "object",
    "required": ["tools"],
    "properties": {
        "tools": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["name", "category"],
                "properties": {
                    "name": {"type": "string"},
                    "category": {
                        "type": "string",
                        "enum": [
                            "crm", "sales_engagement", "email", "enrichment",
                            "intent_data", "analytics", "conversation_intelligence",
                            "marketing_automation", "ai_sdr", "content_generation",
                            "proposal_cpq", "customer_success", "billing",
                            "data_warehouse", "other",
                        ],
                    },
                    "vendor": {"type": "string"},
                    "monthly_cost": {"type": "number"},
                    "annual_cost": {"type": "number"},
                    "users": {"type": "integer"},
                    "utilization_pct": {"type": "number"},
                    "integrations": {"type": "array", "items": {"type": "string"}},
                    "satisfaction_score": {"type": "number", "minimum": 1, "maximum": 10},
                    "contract_end_date": {"type": "string"},
                    "data_flows": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "direction": {"type": "string", "enum": ["inbound", "outbound", "bidirectional"]},
                                "connected_tool": {"type": "string"},
                                "data_type": {"type": "string"},
                                "automation_level": {"type": "string"},
                            },
                        },
                    },
                },
            },
        },
        "gaps_identified": {"type": "array", "items": {"type": "string"}},
        "integration_quality": {
            "type": "string",
            "enum": ["poor", "basic", "moderate", "good", "excellent"],
        },
    },
}


def validate_basic(data: dict, schema: dict) -> list:
    """
    Lightweight validation — checks required fields exist.
    Full JSON Schema validation would use jsonschema library.
    """
    errors = []
    required = schema.get("required", [])
    for field in required:
        if field not in data:
            errors.append(f"Missing required field: '{field}'")
    return errors
