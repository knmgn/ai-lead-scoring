from typing import List, Literal
from pydantic import BaseModel, Field


class SalesPitch(BaseModel):
    subject_line: str = Field(
        ...,
        description="High-converting, hyper-personalized email subject line"
    )
    value_proposition: str = Field(
        ...,
        description="Concise 2-sentence value proposition tailored specifically to their pain point"
    )
    key_talking_points: List[str] = Field(
        ...,
        description="3 compelling talking points referencing their industry, scale, or stated challenge"
    )
    recommended_cta: str = Field(
        ...,
        description="Low-friction call to action (e.g., 15-min technical discovery call)"
    )


class LeadScoringResult(BaseModel):
    score_tier: Literal["S", "A", "B", "C"] = Field(
        ...,
        description="Lead qualification tier: S (Enterprise / High Intent), A (High Fit), B (Mid Fit / Nurture), C (Poor Fit / Disqualified)"
    )
    total_score: int = Field(
        ...,
        ge=0,
        le=100,
        description="Overall weighted qualification score from 0 to 100"
    )
    icp_fit_score: int = Field(
        ...,
        ge=0,
        le=100,
        description="Firmographic alignment with Target ICP (Company size, revenue, industry)"
    )
    intent_urgency_score: int = Field(
        ...,
        ge=0,
        le=100,
        description="Urgency, timeline clarity, and explicit pain points mentioned in message"
    )
    budget_authority_score: int = Field(
        ...,
        ge=0,
        le=100,
        description="Likelihood of budget ownership, executive sponsorship, and decision authority"
    )
    company_summary: str = Field(
        ...,
        description="Executive briefing of the prospect's company business model and operational focus"
    )
    evaluation_rationale: List[str] = Field(
        ...,
        description="Bullet points explaining why this tier and score were awarded"
    )
    recommended_sales_pitch: SalesPitch = Field(
        ...,
        description="Custom sales pitch and outreach strategy for the sales rep"
    )
    suggested_action: Literal[
        "IMMEDIATE_AE_OUTREACH",
        "STANDARD_SDR_QUALIFY",
        "AUTOMATED_NURTURE",
        "DISQUALIFIED"
    ] = Field(
        ...,
        description="Prescribed RevOps next step for sales routing"
    )
    routing_priority: Literal["URGENT", "HIGH", "MEDIUM", "LOW"] = Field(
        ...,
        description="Operational priority queue level"
    )
