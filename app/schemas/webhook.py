from typing import Optional
from pydantic import BaseModel, Field


class InboundLeadPayload(BaseModel):
    name: str = Field(
        ...,
        description="Full name of the prospect",
        json_schema_extra={"example": "Sarah Jenkins"}
    )
    email: str = Field(
        ...,
        description="Business email address",
        json_schema_extra={"example": "sarah.jenkins@stripe.com"}
    )
    message: str = Field(
        ...,
        description="Inbound inquiry message submitted by the prospect",
        json_schema_extra={"example": "We are scaling our sales operations and currently losing 30% of high-intent leads due to slow response times. Looking to implement an AI triage and automated enrichment system within Q3."}
    )
    company_domain: str = Field(
        ...,
        description="Company domain or website",
        json_schema_extra={"example": "stripe.com"}
    )
    company_name: Optional[str] = Field(
        None,
        description="Company name if provided",
        json_schema_extra={"example": "Stripe"}
    )
    phone: Optional[str] = Field(
        None,
        description="Contact phone number",
        json_schema_extra={"example": "+1-415-555-0199"}
    )
    source: Optional[str] = Field(
        "Website Contact Form",
        description="Origin of the lead"
    )
