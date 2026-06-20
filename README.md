# ValueOS Agentic GTM Accelerator Workflow

**AWS SAM Deployment Package**
Agentic serverless deployment for automated GTM audit, gap analysis, and executive report generation workflow using AWS SAM, Bedrock and Claude orchestration.

---

## Architecture

```
Client JSON Data → API Gateway → Lambda (Ingest) → DynamoDB
                                                        ↓
API Gateway → Lambda (Orchestrator) → Multi-Agent Pipeline → S3 (Reports)
                                           ↓
                                    Agent 1: GTM Health Scorecard
                                    Agent 2: Architecture Blueprint
                                    Agent 3: Unit Economics Model
                                    Agent 4: Implementation Roadmap
                                    Agent 5: Report Compiler
```

**Stack:** API Gateway, Lambda (Python 3.12), DynamoDB, S3, Cognito, Bedrock (Claude Sonnet 4.5)

## Quick Start

### Prerequisites
- AWS CLI configured with appropriate credentials
- AWS SAM CLI installed (`brew install aws-sam-cli` or [install guide](https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/install-sam-cli.html))
- AWS Bedrock access enabled for `anthropic.claude-sonnet-4-5-20250514-v1:0` in your region
- Python 3.12+

### Deploy (< 5 minutes)

```bash
# 1. Build
sam build

# 2. Deploy (first time — guided)
sam deploy --guided

# 3. Deploy (subsequent)
sam deploy
```

### Enable Bedrock Model Access
1. Go to AWS Console → Amazon Bedrock → Model access
2. Request access to **Anthropic Claude Sonnet 4.5**
3. Wait for approval (usually instant)

---

## API Endpoints

After deployment, SAM outputs the `ApiEndpoint` URL. All endpoints require Cognito JWT auth (except noted).

### Engagement Management
| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/engagements` | Create new client engagement |
| `GET` | `/engagements/{id}` | Get engagement details |

### Data Ingestion (JSON → DynamoDB)
| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/engagements/{id}/data/gtm` | Ingest GTM operating model |
| `POST` | `/engagements/{id}/data/sales` | Ingest sales telemetry |
| `POST` | `/engagements/{id}/data/financials` | Ingest unit economics |
| `POST` | `/engagements/{id}/data/tools` | Ingest tool stack inventory |

### Report Generation (Agentic Workflow)
| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/engagements/{id}/report/generate` | Trigger full multi-agent report |
| `GET` | `/engagements/{id}/report` | Get report + download URLs |
| `GET` | `/engagements/{id}/report/status` | Check generation progress |

### Demo (One-Click)
| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/demo/run` | Load sample data + generate full report |

---

## FDE Live Demo Workflow

### One-Click Demo (fastest)
```bash
curl -X POST $API_URL/demo/run \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json"
```
This loads the built-in NeuralFlow AI sample dataset and runs the full 5-agent pipeline. Takes ~2-4 minutes. Returns the complete report inline.

### Client-Specific Demo
```bash
# 1. Create engagement
curl -X POST $API_URL/engagements \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"company_name":"Acme AI","contact_email":"ceo@acme.ai","stage":"series_b"}'

# 2. Ingest client data (use templates from sample_data/)
curl -X POST $API_URL/engagements/{ID}/data/gtm \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d @sample_data/input_gtm_template.json

# Repeat for /data/sales, /data/financials, /data/tools

# 3. Generate report
curl -X POST $API_URL/engagements/{ID}/report/generate \
  -H "Authorization: Bearer $TOKEN"
```

---

## Data Input Templates

JSON templates for client data collection are in `sample_data/`:

| File | Description |
|------|-------------|
| `input_gtm_template.json` | GTM operating model, ICP, sales process, competitors |
| `input_sales_template.json` | Pipeline data, velocity metrics, rep performance, cohort metrics |
| `input_financials_template.json` | Unit economics, revenue breakdown, cost structure, AI costs |
| `input_tools_template.json` | Current tool stack inventory with integrations |

## Report Output

The generated report contains 4 structured JSON sections + 1 compiled Markdown narrative:

1. **GTM Health Scorecard** — 10-dimension scoring (1-10 scale) with gap analysis
2. **AI-Native GTM Architecture Blueprint** — 6-layer architecture with tool recommendations
3. **Unit Economics Model** — True CAC/LTV/margins with 3 optimization scenarios
4. **Implementation Roadmap** — 16-week phased plan with KPIs and resource needs
5. **Executive Report** — Full Markdown narrative synthesizing all sections

Reports are stored in S3 with presigned download URLs returned in the API response.

---

## Project Structure

```
gtm-accelerator-sprint/
├── template.yaml                  # AWS SAM template (IaC)
├── samconfig.toml                 # SAM deployment config
├── requirements.txt               # Python dependencies
├── src/
│   ├── handlers/
│   │   ├── engagement.py          # Engagement CRUD
│   │   ├── ingest.py              # Data ingestion endpoints
│   │   ├── report_orchestrator.py # Report generation trigger
│   │   └── demo.py               # One-click demo
│   ├── agents/
│   │   └── orchestrator.py        # Multi-agent pipeline engine
│   ├── schemas/
│   │   └── data_schemas.py        # JSON validation schemas
│   ├── templates/
│   │   └── agent_prompts.py       # Agent system/user prompts
│   └── utils/
│       ├── api.py                 # API response helpers
│       ├── bedrock.py             # Bedrock Claude client
│       └── dynamo.py              # DynamoDB operations
├── sample_data/
│   ├── demo_data.py               # Built-in sample dataset
│   ├── input_gtm_template.json    # Client GTM data template
│   ├── input_sales_template.json  # Client sales data template
│   ├── input_financials_template.json
│   └── input_tools_template.json
├── tests/
│   └── test_api_flow.py           # Integration test script
└── docs/
    └── api_collection.json        # Postman/HTTP client collection
```

## Cleanup

```bash
sam delete --stack-name gtm-accelerator-sprint
```
## License
Proprietary — ValueLayer 2026. All rights reserved
