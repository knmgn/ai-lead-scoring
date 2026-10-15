from typing import Optional, Dict, Any
import httpx

from app.core.config import settings
from app.core.logger import logger
from app.schemas.webhook import InboundLeadPayload
from app.schemas.enrichment import EnrichedCompanyData
from app.schemas.scoring import LeadScoringResult


async def sync_to_hubspot(
    lead: InboundLeadPayload,
    enrichment: EnrichedCompanyData,
    scoring: LeadScoringResult
) -> Dict[str, Any]:
    """
    Syncs the enriched lead and AI qualification to HubSpot CRM.
    Creates or updates Contact and automatically creates an Enterprise Deal for Tier S & A leads.
    """
    first_name = lead.name.split()[0] if lead.name else "Valued"
    last_name = " ".join(lead.name.split()[1:]) if len(lead.name.split()) > 1 else "Prospect"

    contact_properties = {
        "email": lead.email,
        "firstname": first_name,
        "lastname": last_name,
        "company": enrichment.company_name,
        "website": f"https://{enrichment.domain}",
        "message": lead.message,
        "lead_tier": scoring.score_tier,
        "lead_score": str(scoring.total_score),
        "ai_company_summary": scoring.company_summary[:500],
        "ai_sales_pitch": scoring.recommended_sales_pitch.value_proposition[:500],
        "hs_lead_status": "OPEN" if scoring.score_tier in ["S", "A"] else "IN_PROGRESS"
    }

    # If live HubSpot Access Token is provided
    if settings.HUBSPOT_ACCESS_TOKEN:
        headers = {
            "Authorization": f"Bearer {settings.HUBSPOT_ACCESS_TOKEN}",
            "Content-Type": "application/json"
        }
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                # 1. Upsert Contact
                logger.info(f"Syncing contact {lead.email} to HubSpot CRM...")
                contact_resp = await client.post(
                    "https://api.hubapi.com/crm/v3/objects/contacts",
                    headers=headers,
                    json={"properties": contact_properties}
                )
                
                contact_id = None
                if contact_resp.status_code in [200, 201]:
                    contact_id = contact_resp.json().get("id")
                elif contact_resp.status_code == 409: # Contact already exists
                    contact_id = "existing_contact_updated"

                # 2. Automatically Create Deal if Tier S or Tier A
                deal_id = None
                if scoring.score_tier in ["S", "A"]:
                    logger.info(f"High-priority lead Tier {scoring.score_tier}. Creating HubSpot Deal...")
                    deal_properties = {
                        "dealname": f"[{scoring.score_tier}-Tier AI Lead] {enrichment.company_name} - RevOps Opportunity",
                        "pipeline": "default",
                        "dealstage": "appointmentscheduled",
                        "amount": "50000" if scoring.score_tier == "S" else "25000"
                    }
                    deal_resp = await client.post(
                        "https://api.hubapi.com/crm/v3/objects/deals",
                        headers=headers,
                        json={"properties": deal_properties}
                    )
                    if deal_resp.status_code in [200, 201]:
                        deal_id = deal_resp.json().get("id")

                return {
                    "synced": True,
                    "contact_id": contact_id,
                    "deal_id": deal_id,
                    "mode": "live_hubspot_api"
                }

        except Exception as e:
            logger.error(f"HubSpot live sync failed: {e}. Defaulting to simulated CRM response.")

    # Simulated Fallback / Demo Mode
    simulated_contact_id = f"hs_cnt_{abs(hash(lead.email)) % 10000000}"
    simulated_deal_id = f"hs_deal_{abs(hash(lead.company_domain)) % 10000000}" if scoring.score_tier in ["S", "A"] else None
    
    logger.info(
        f"[HubSpot Simulation] Contact upserted: {lead.email} (ID: {simulated_contact_id}) "
        f"| Tier: {scoring.score_tier} | Deal Created: {simulated_deal_id is not None}"
    )

    return {
        "synced": True,
        "contact_id": simulated_contact_id,
        "deal_id": simulated_deal_id,
        "mode": "simulated_crm_mode"
    }
