from typing import Dict, Any, Optional
from datetime import datetime, timezone
from pydantic import BaseModel, Field

from app.schemas.webhook import InboundLeadPayload
from app.schemas.enrichment import EnrichedCompanyData
from app.schemas.scoring import LeadScoringResult


class IntegrationStatus(BaseModel):
    hubspot_synced: bool = Field(..., description="Whether lead was synced to HubSpot CRM")
    hubspot_contact_id: Optional[str] = Field(None, description="HubSpot Contact ID")
    hubspot_deal_id: Optional[str] = Field(None, description="HubSpot Deal ID if Tier S/A")
    slack_notified: bool = Field(..., description="Whether alert was dispatched to Slack")
    slack_channel: Optional[str] = Field(None, description="Slack channel or webhook target")
    execution_notes: Optional[str] = Field(None, description="Operational notes or simulation indicator")


class LeadProcessingResponse(BaseModel):
    success: bool = True
    lead_id: str = Field(..., description="Unique tracking identifier for this inbound submission")
    processed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    lead: InboundLeadPayload
    enrichment: EnrichedCompanyData
    scoring: LeadScoringResult
    integrations: IntegrationStatus
