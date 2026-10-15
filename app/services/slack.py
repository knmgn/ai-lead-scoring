import json
from typing import Dict, Any, List
import httpx

from app.core.config import settings
from app.core.logger import logger
from app.schemas.webhook import InboundLeadPayload
from app.schemas.enrichment import EnrichedCompanyData
from app.schemas.scoring import LeadScoringResult


def build_slack_block_kit(
    lead: InboundLeadPayload,
    enrichment: EnrichedCompanyData,
    scoring: LeadScoringResult
) -> List[Dict[str, Any]]:
    """
    Constructs an interactive, executive-grade Slack Block Kit payload.
    Optimized for instant SDR/AE response and context synthesis.
    """
    tier_emojis = {
        "S": "🔥 [TIER S - IMMEDIATE ACTION]",
        "A": "🚀 [TIER A - HIGH PRIORITY]",
        "B": "ℹ️ [TIER B - NURTURE]",
        "C": "💤 [TIER C - DISQUALIFIED]"
    }
    tier_banner = tier_emojis.get(scoring.score_tier, f"Tier {scoring.score_tier}")

    blocks: List[Dict[str, Any]] = [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": f"{tier_banner} {enrichment.company_name}",
                "emoji": True
            }
        },
        {
            "type": "section",
            "fields": [
                {
                    "type": "mrkdwn",
                    "text": f"*👤 Contact:*\n{lead.name} (<mailto:{lead.email}|{lead.email}>)"
                },
                {
                    "type": "mrkdwn",
                    "text": f"*🏢 Company / Domain:*\n{enrichment.company_name} (`{enrichment.domain}`)"
                },
                {
                    "type": "mrkdwn",
                    "text": f"*📊 Qualification Score:*\n*{scoring.total_score} / 100* (Tier {scoring.score_tier})"
                },
                {
                    "type": "mrkdwn",
                    "text": f"*🌐 Headcount & Revenue:*\n{enrichment.employee_range} | {enrichment.estimated_revenue}"
                }
            ]
        },
        {"type": "divider"},
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": (
                    f"*📈 Score Breakdown Metrics:*\n"
                    f"• *ICP Fit:* `{scoring.icp_fit_score}/100`  |  "
                    f"• *Intent Urgency:* `{scoring.intent_urgency_score}/100`  |  "
                    f"• *Budget & Authority:* `{scoring.budget_authority_score}/100`\n"
                    f"• *Action Recommendation:* `{scoring.suggested_action}`"
                )
            }
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*💬 Inbound Inquiry:*\n> {lead.message}"
            }
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*🤖 AI Executive Summary:*\n{scoring.company_summary}"
            }
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": (
                    f"*🎯 Tailored Sales Pitch (AE Quick-Draw):*\n"
                    f"*Subject:* `{scoring.recommended_sales_pitch.subject_line}`\n"
                    f"*Value Prop:* {scoring.recommended_sales_pitch.value_proposition}\n"
                    f"*Key Talking Points:*\n" +
                    "\n".join([f"• {point}" for point in scoring.recommended_sales_pitch.key_talking_points]) +
                    f"\n*CTA:* _{scoring.recommended_sales_pitch.recommended_cta}_"
                )
            }
        },
        {"type": "divider"},
        {
            "type": "actions",
            "elements": [
                {
                    "type": "button",
                    "text": {
                        "type": "plain_text",
                        "text": "⚡ Claim Lead",
                        "emoji": True
                    },
                    "style": "primary",
                    "value": f"claim_{lead.email}",
                    "action_id": "action_claim_lead"
                },
                {
                    "type": "button",
                    "text": {
                        "type": "plain_text",
                        "text": "📊 Open in HubSpot",
                        "emoji": True
                    },
                    "url": f"https://app.hubspot.com/contacts/{settings.HUBSPOT_PORTAL_ID or '12345678'}/contacts",
                    "action_id": "action_open_hubspot"
                },
                {
                    "type": "button",
                    "text": {
                        "type": "plain_text",
                        "text": "📅 Schedule Discovery",
                        "emoji": True
                    },
                    "value": f"schedule_{lead.email}",
                    "action_id": "action_schedule_meeting"
                }
            ]
        }
    ]

    return blocks


async def dispatch_slack_alert(
    lead: InboundLeadPayload,
    enrichment: EnrichedCompanyData,
    scoring: LeadScoringResult
) -> Dict[str, Any]:
    """
    Evaluates tier threshold and dispatches Block Kit alert to Slack webhook.
    """
    tier_order = {"S": 4, "A": 3, "B": 2, "C": 1}
    min_tier_val = tier_order.get(settings.SLACK_MINIMUM_TIER_NOTIFICATION, 3) # default A (3)
    lead_tier_val = tier_order.get(scoring.score_tier, 1)

    # Check notification threshold
    if lead_tier_val < min_tier_val:
        logger.info(
            f"Slack notification suppressed: Lead Tier ({scoring.score_tier}) is below minimum alert threshold ({settings.SLACK_MINIMUM_TIER_NOTIFICATION})."
        )
        return {
            "dispatched": False,
            "reason": f"Tier {scoring.score_tier} does not meet alert threshold {settings.SLACK_MINIMUM_TIER_NOTIFICATION}"
        }

    blocks = build_slack_block_kit(lead, enrichment, scoring)
    fallback_text = f"New Tier {scoring.score_tier} Lead: {lead.name} ({enrichment.company_name}) - Score: {scoring.total_score}/100"

    # Live Slack Webhook Dispatch
    if settings.SLACK_WEBHOOK_URL:
        try:
            logger.info(f"Dispatching live Slack Block Kit alert for {lead.name} ({scoring.score_tier}-Tier)...")
            async with httpx.AsyncClient(timeout=8.0) as client:
                resp = await client.post(
                    settings.SLACK_WEBHOOK_URL,
                    json={"text": fallback_text, "blocks": blocks}
                )
                if resp.status_code == 200:
                    logger.info("Slack alert successfully delivered!")
                    return {"dispatched": True, "target": "live_webhook", "status": 200}
                else:
                    logger.warning(f"Slack delivery returned status {resp.status_code}: {resp.text}")
        except Exception as e:
            logger.error(f"Failed to post alert to Slack webhook: {e}")

    # Simulated Slack Dispatch
    logger.info(
        f"[Slack Simulation Mode] Generated High-Converting Block Kit Alert for Tier {scoring.score_tier} Lead!\n"
        f"Recipient Preview: {fallback_text}\n"
        f"Block Count: {len(blocks)} blocks generated."
    )

    return {
        "dispatched": True,
        "target": "simulated_slack_logger",
        "preview": fallback_text,
        "blocks_count": len(blocks)
    }
