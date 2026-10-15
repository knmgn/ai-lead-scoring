from typing import List, Optional
from pydantic import BaseModel, Field


class EnrichedCompanyData(BaseModel):
    company_name: str = Field(..., description="Canonical or extracted company name")
    domain: str = Field(..., description="Company domain")
    industry: str = Field(..., description="Primary industry vertical")
    employee_range: str = Field(..., description="Estimated headcount range (e.g., 500-1,000)")
    estimated_revenue: str = Field(..., description="Estimated annual revenue range")
    description: str = Field(..., description="Summary of core business and value proposition")
    tech_stack: List[str] = Field(default_factory=list, description="Known technologies and tools detected")
    recent_news: List[str] = Field(default_factory=list, description="Recent press releases, funding, or product launches")
    target_market: str = Field(..., description="B2B, B2C, Enterprise, Mid-Market, etc.")
    source: str = Field("Web Scraper / Intelligence Engine", description="Source of enrichment data")
    is_mock: bool = Field(False, description="True if mock fallback was utilized")
