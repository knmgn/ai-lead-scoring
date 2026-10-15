import uuid
from typing import Literal
from fastapi import FastAPI, HTTPException, BackgroundTasks, status
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.logger import logger
from app.schemas.webhook import InboundLeadPayload
from app.schemas.enrichment import EnrichedCompanyData
from app.schemas.scoring import LeadScoringResult
from app.schemas.response import LeadProcessingResponse, IntegrationStatus
from app.services.scraper import enrich_company
from app.services.llm_scorer import score_lead_with_llm
from app.services.hubspot import sync_to_hubspot
from app.services.slack import dispatch_slack_alert


app = FastAPI(
    title=settings.APP_NAME,
    version="1.0.0",
    description="""
## Enterprise AI Lead Scoring & Enrichment Engine
**Automated B2B Revenue Operations & Real-Time Pipeline Acceleration API**

This API processes inbound leads from webhooks, enriches corporate firmographics in real-time,
executes LLM-powered qualification scoring using structured schemas, and synchronizes actionable
intelligence with HubSpot CRM and Slack.

### Architecture Highlights:
* **Real-Time Webhook Ingestion**: Integrates with HubSpot, Typeform, Webflow, or custom forms.
* **Firmographic Enrichment**: Extracts company size, revenue, tech stack, and recent business initiatives.
* **Structured AI Scoring**: Categorizes leads into **Tier S, A, B, C** with custom sales pitches.
* **Multi-Channel Dispatch**: HubSpot Contact & Deal automation + Interactive Slack Block Kit alerts.
""",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS Middleware configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/", tags=["Health"])
async def root():
    return {
        "service": settings.APP_NAME,
        "status": "operational",
        "documentation": "/docs",
        "llm_provider": settings.LLM_PROVIDER,
        "environment": settings.APP_ENV
    }


@app.get("/health", tags=["Health"])
async def health_check():
    return {
        "status": "healthy",
        "app_name": settings.APP_NAME,
        "llm_engine": {
            "provider": settings.LLM_PROVIDER,
            "openai_configured": bool(settings.OPENAI_API_KEY),
            "anthropic_configured": bool(settings.ANTHROPIC_API_KEY),
        },
        "crm_engine": {
            "hubspot_configured": bool(settings.HUBSPOT_ACCESS_TOKEN)
        },
        "notification_engine": {
            "slack_configured": bool(settings.SLACK_WEBHOOK_URL),
            "minimum_tier": settings.SLACK_MINIMUM_TIER_NOTIFICATION
        }
    }


@app.post(
    "/webhook/lead",
    response_model=LeadProcessingResponse,
    status_code=status.HTTP_200_OK,
    tags=["Lead Ingestion & Pipeline Orchestration"],
    summary="Ingest Inbound Lead Webhook",
    description="Main pipeline endpoint: enriches company domain, scores lead via LLM, and dispatches to HubSpot & Slack."
)
async def process_inbound_lead(payload: InboundLeadPayload):
    lead_id = f"lead_{uuid.uuid4().hex[:10]}"
    logger.info(f"[{lead_id}] Received inbound lead from {payload.email} ({payload.company_domain})")

    try:
        # Step 1: Real-Time Firmographic Enrichment
        enrichment: EnrichedCompanyData = await enrich_company(
            domain=payload.company_domain,
            fallback_company_name=payload.company_name
        )

        # Step 2: AI Lead Scoring & Sales Pitch Generation (LLM Structured Outputs)
        scoring: LeadScoringResult = await score_lead_with_llm(
            lead=payload,
            enrichment=enrichment
        )

        # Step 3: HubSpot CRM Synchronization (Contact & Deal creation)
        hubspot_result = await sync_to_hubspot(
            lead=payload,
            enrichment=enrichment,
            scoring=scoring
        )

        # Step 4: Slack Interactive Notification Dispatch
        slack_result = await dispatch_slack_alert(
            lead=payload,
            enrichment=enrichment,
            scoring=scoring
        )

        integrations = IntegrationStatus(
            hubspot_synced=hubspot_result.get("synced", False),
            hubspot_contact_id=hubspot_result.get("contact_id"),
            hubspot_deal_id=hubspot_result.get("deal_id"),
            slack_notified=slack_result.get("dispatched", False),
            slack_channel=slack_result.get("target"),
            execution_notes=(
                f"CRM: {hubspot_result.get('mode', 'live')} | "
                f"Slack: {slack_result.get('target', 'live')} | "
                f"LLM: {settings.LLM_PROVIDER}"
            )
        )

        logger.info(
            f"[{lead_id}] Pipeline completed successfully: "
            f"Tier {scoring.score_tier} (Score: {scoring.total_score}/100) -> Next: {scoring.suggested_action}"
        )

        return LeadProcessingResponse(
            success=True,
            lead_id=lead_id,
            lead=payload,
            enrichment=enrichment,
            scoring=scoring,
            integrations=integrations
        )

    except Exception as e:
        logger.error(f"[{lead_id}] Critical failure in lead pipeline: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Pipeline processing failed: {str(e)}"
        )


@app.post(
    "/demo/simulate/{preset}",
    response_model=LeadProcessingResponse,
    tags=["Demo Simulation"],
    summary="Simulate Pre-Configured Lead Tiers",
    description="Instantly test pipeline execution for specific tiers ('tier_s', 'tier_a', 'tier_b', 'tier_c')."
)
async def simulate_lead(preset: Literal["tier_s", "tier_a", "tier_b", "tier_c"]):
    presets = {
        "tier_s": InboundLeadPayload(
            name="Alex Montgomery",
            email="alex.m@stripe.com",
            company_domain="stripe.com",
            company_name="Stripe",
            message="We are currently experiencing severe lead triage delays across our Global Sales Operations. Looking to deploy automated AI qualification and instant Slack routing for inbound enterprise inquiries before Q4 budget closes."
        ),
        "tier_a": InboundLeadPayload(
            name="Elena Rostova",
            email="elena.r@acme-test.io",
            company_domain="acme-test.io",
            company_name="Acme Innovations",
            message="Hi team, our SDR team of 15 reps is spending 4 hours a day manually checking LinkedIn and company websites. We want to automate company enrichment and lead routing into HubSpot."
        ),
        "tier_b": InboundLeadPayload(
            name="Jordan Lee",
            email="jordan@earlystage-startup.co",
            company_domain="notion.so",
            company_name="Growth Labs",
            message="Just curious about how your AI scoring works compared to standard rules. Do you have documentation or a self-serve tier for seed-stage startups?"
        ),
        "tier_c": InboundLeadPayload(
            name="Chris Taylor",
            email="chris.taylor@gmail.com",
            company_domain="gmail.com",
            company_name="Independent",
            message="Hello, I am a university student interested in machine learning and wondering if you have any internships available this summer?"
        ),
    }

    if preset not in presets:
        raise HTTPException(status_code=400, detail="Invalid preset tier")

    return await process_inbound_lead(presets[preset])


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host=settings.HOST, port=settings.PORT, reload=settings.DEBUG)
