import json
from typing import Optional
from openai import AsyncOpenAI
import anthropic

from app.core.config import settings
from app.core.logger import logger
from app.schemas.webhook import InboundLeadPayload
from app.schemas.enrichment import EnrichedCompanyData
from app.schemas.scoring import LeadScoringResult, SalesPitch


SYSTEM_PROMPT = """You are an elite Enterprise Revenue Operations & AI Sales Architect.
Your mandate is to rigorously evaluate inbound enterprise leads, score their fit against our Ideal Customer Profile (ICP), and generate hyper-tailored sales pitch assets for Account Executives (AEs) and Sales Development Reps (SDRs).

### OUR TARGET ICP & VALUE OFFERING:
- Target Industries: {target_industry}
- Target Size: {target_employee_min} to {target_employee_max} employees (Enterprise to Scale-Up)
- Revenue Scale: > {target_revenue_min} ARR
- Solution Offering: {product_offering}

### LEAD QUALIFICATION TIERS:
- **Tier S (Score: 90-100)**: Premier Enterprise ICP. Explicit urgent pain point, high buying intent, significant deal size potential. Route immediately to Senior AE.
- **Tier A (Score: 75-89)**: Strong Fit ICP. Clear problem statement, healthy budget indicators, solid company scale. Route to SDR for priority discovery.
- **Tier B (Score: 50-74)**: Moderate Fit. Mid-market or early growth, less concrete urgency, or educational interest. Add to marketing nurture & automated follow-up.
- **Tier C (Score: 0-49)**: Disqualified / Mismatched. Job seekers, personal email spam, students, or negligible budget.

### INSTRUCTIONS:
1. Objectively evaluate the combined firmographic enrichment and the prospect's actual message.
2. Calculate individual sub-scores for ICP Fit, Intent Urgency, and Budget/Authority.
3. Compute the overall weighted score (0-100) and assign the matching Tier (S/A/B/C).
4. Craft an executive summary of the prospect company's operations.
5. Provide a crisp, non-generic Sales Pitch including a punchy subject line, value proposition, and bulleted talking points.
"""


def _generate_deterministic_demo_score(
    lead: InboundLeadPayload,
    enrichment: EnrichedCompanyData
) -> LeadScoringResult:
    """
    Intelligent heuristic fallback scoring engine.
    Ensures the repository operates out-of-the-box even without active LLM API keys.
    """
    logger.info("Evaluating lead via intelligent heuristic rule engine (Demo / Fallback Mode)")
    
    msg = lead.message.lower()
    domain = lead.company_domain.lower()
    industry = enrichment.industry.lower()

    # High-intent signals in message
    urgent_signals = ["urgent", "q3", "q4", "budget", "enterprise", "automate", "triage", "scale", "losing", "pipeline", "implement"]
    urgent_matches = sum(1 for sig in urgent_signals if sig in msg)

    # ICP scale calculation
    is_large_enterprise = any(k in enrichment.employee_range for k in ["1,000", "3,000", "5,000", "10,000"]) or "b+" in enrichment.estimated_revenue.lower()
    is_mid_market = any(k in enrichment.employee_range for k in ["80", "100", "250", "500"])

    # Disqualification check
    if any(k in msg for k in ["job", "career", "resume", "internship", "student"]):
        return LeadScoringResult(
            score_tier="C",
            total_score=20,
            icp_fit_score=15,
            intent_urgency_score=10,
            budget_authority_score=10,
            company_summary=f"{enrichment.company_name} ({enrichment.industry}).",
            evaluation_rationale=[
                "Message indicates job application or educational inquiry rather than commercial purchase intent.",
                "Zero enterprise budget allocation indicated.",
                "Disqualified from sales rep outreach pipeline."
            ],
            recommended_sales_pitch=SalesPitch(
                subject_line=f"Thank you for reaching out to {settings.APP_NAME}",
                value_proposition="Automated acknowledgement of inquiry with redirect to relevant self-service resources.",
                key_talking_points=[
                    "No commercial sales follow-up recommended",
                    "Add to automated careers or newsletter directory"
                ],
                recommended_cta="Direct to public careers page or FAQ portal."
            ),
            suggested_action="DISQUALIFIED",
            routing_priority="LOW"
        )

    # Tier S Assessment
    if (is_large_enterprise and urgent_matches >= 2) or ("stripe.com" in domain or "datadog" in domain):
        return LeadScoringResult(
            score_tier="S",
            total_score=96,
            icp_fit_score=98,
            intent_urgency_score=95,
            budget_authority_score=95,
            company_summary=f"{enrichment.company_name} is a market-leading enterprise in {enrichment.industry} with estimated headcount of {enrichment.employee_range}. Core focus: {enrichment.description}",
            evaluation_rationale=[
                f"Flawless ICP match: {enrichment.company_name} possesses enterprise scale ({enrichment.employee_range}) and strong revenue backing ({enrichment.estimated_revenue}).",
                "Explicit pain point expressed in inbound message regarding response latency and pipeline leakage.",
                "Direct alignment with our AI RevOps and real-time lead triage automation offering."
            ],
            recommended_sales_pitch=SalesPitch(
                subject_line=f"Scaling {enrichment.company_name}'s inbound pipeline velocity with real-time AI triage",
                value_proposition=f"Help {enrichment.company_name} eliminate lead leakage and accelerate high-intent enterprise response times from hours to under 60 seconds.",
                key_talking_points=[
                    f"Address specific inquiry: Solve speed-to-lead bottleneck directly inside HubSpot & Slack",
                    f"Leverage automated firmographic enrichment to prioritize high-value prospects without manual SDR research",
                    f"Seamlessly integrate with their existing tech stack ({', '.join(enrichment.tech_stack[:3])})"
                ],
                recommended_cta="Propose a 15-minute technical architecture walkthrough with a Principal AI Architect."
            ),
            suggested_action="IMMEDIATE_AE_OUTREACH",
            routing_priority="URGENT"
        )

    # Tier A Assessment
    if is_mid_market or urgent_matches >= 1:
        return LeadScoringResult(
            score_tier="A",
            total_score=84,
            icp_fit_score=85,
            intent_urgency_score=82,
            budget_authority_score=85,
            company_summary=f"{enrichment.company_name} is a growing player in {enrichment.industry}. They specialize in {enrichment.description[:120]}...",
            evaluation_rationale=[
                f"Strong fit within core target headcount ({enrichment.employee_range}) and revenue bracket ({enrichment.estimated_revenue}).",
                "Demonstrated active interest in workflow modernization and revenue operations.",
                "High probability of qualified opportunity upon initial technical discovery."
            ],
            recommended_sales_pitch=SalesPitch(
                subject_line=f"Accelerating revenue workflow automation for {enrichment.company_name}",
                value_proposition=f"Enable {enrichment.company_name}'s revenue team to automatically enrich, score, and route inbound opportunities with zero latency.",
                key_talking_points=[
                    "Reduce manual qualification overhead by up to 75%",
                    "Instantly deliver enriched lead context into Slack and CRM",
                    "Proven ROI on pipeline conversion for mid-market revenue teams"
                ],
                recommended_cta="Suggest a 20-minute tailored platform demo."
            ),
            suggested_action="STANDARD_SDR_QUALIFY",
            routing_priority="HIGH"
        )

    # Tier B Fallback
    return LeadScoringResult(
        score_tier="B",
        total_score=64,
        icp_fit_score=65,
        intent_urgency_score=60,
        budget_authority_score=67,
        company_summary=f"{enrichment.company_name} operates within {enrichment.industry}.",
        evaluation_rationale=[
            "Moderate firmographic fit; company scale or budget readiness is emerging.",
            "Inquiry demonstrates general interest but lacks defined procurement timeline.",
            "Best suited for structured email nurturing and product-led onboarding."
        ],
        recommended_sales_pitch=SalesPitch(
            subject_line=f"Resources & Best Practices for {enrichment.company_name}'s RevOps Team",
            value_proposition="Provide automated educational resources and case studies on AI-driven lead qualification.",
            key_talking_points=[
                "Share benchmark report on speed-to-lead conversion gains",
                "Invite to upcoming webinar on automated inbound pipelines"
            ],
            recommended_cta="Invite to on-demand product tour or self-serve documentation."
        ),
        suggested_action="AUTOMATED_NURTURE",
        routing_priority="MEDIUM"
    )


async def score_lead_with_llm(
    lead: InboundLeadPayload,
    enrichment: EnrichedCompanyData
) -> LeadScoringResult:
    """
    Evaluates an inbound lead using OpenAI (gpt-4o) or Anthropic (claude-3-5-sonnet)
    with structured schema enforcement. Falls back cleanly to demo engine if keys are absent.
    """
    prompt_context = {
        "target_industry": settings.TARGET_INDUSTRY,
        "target_employee_min": settings.TARGET_EMPLOYEE_MIN,
        "target_employee_max": settings.TARGET_EMPLOYEE_MAX,
        "target_revenue_min": settings.TARGET_ANNUAL_REVENUE_MIN,
        "product_offering": settings.COMPANY_PRODUCT_OFFERING,
    }
    formatted_system_prompt = SYSTEM_PROMPT.format(**prompt_context)

    user_payload_str = json.dumps({
        "lead_inbound": lead.model_dump(),
        "company_enrichment": enrichment.model_dump()
    }, indent=2)

    user_message = f"Please evaluate the following inbound lead and company data against our ICP:\n\n```json\n{user_payload_str}\n```"

    # 1. OpenAI Structured Output Execution
    if settings.LLM_PROVIDER == "openai" and settings.OPENAI_API_KEY:
        try:
            logger.info(f"Invoking OpenAI ({settings.OPENAI_MODEL}) Structured Output for {lead.company_domain}...")
            client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
            completion = await client.beta.chat.completions.parse(
                model=settings.OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": formatted_system_prompt},
                    {"role": "user", "content": user_message}
                ],
                response_format=LeadScoringResult,
                temperature=0.2,
            )
            parsed_result = completion.choices[0].message.parsed
            if parsed_result:
                logger.info(f"OpenAI scoring completed: Tier {parsed_result.score_tier} (Score: {parsed_result.total_score})")
                return parsed_result
        except Exception as e:
            logger.error(f"OpenAI scoring encountered error: {e}. Falling back to heuristic scoring.")

    # 2. Anthropic Execution
    elif settings.LLM_PROVIDER == "anthropic" and settings.ANTHROPIC_API_KEY:
        try:
            logger.info(f"Invoking Anthropic ({settings.ANTHROPIC_MODEL}) for {lead.company_domain}...")
            client = anthropic.AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)
            
            tool_schema = {
                "name": "record_lead_score",
                "description": "Record the structured qualification and sales pitch for the lead",
                "input_schema": LeadScoringResult.model_json_schema()
            }

            response = await client.messages.create(
                model=settings.ANTHROPIC_MODEL,
                max_tokens=2048,
                temperature=0.2,
                system=formatted_system_prompt,
                messages=[{"role": "user", "content": user_message}],
                tools=[tool_schema],
                tool_choice={"type": "tool", "name": "record_lead_score"}
            )

            for content_block in response.content:
                if content_block.type == "tool_use" and content_block.name == "record_lead_score":
                    parsed = LeadScoringResult(**content_block.input)
                    logger.info(f"Anthropic scoring completed: Tier {parsed.score_tier} (Score: {parsed.total_score})")
                    return parsed
        except Exception as e:
            logger.error(f"Anthropic scoring encountered error: {e}. Falling back to heuristic scoring.")

    # 3. Fallback / Deterministic Engine
    return _generate_deterministic_demo_score(lead, enrichment)
