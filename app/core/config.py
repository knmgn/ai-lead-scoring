from typing import Optional, Literal
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    # Application
    APP_NAME: str = "Enterprise AI Lead Scoring Engine"
    APP_ENV: str = "development"
    DEBUG: bool = True
    PORT: int = 8000
    HOST: str = "0.0.0.0"

    # AI Configuration
    LLM_PROVIDER: Literal["openai", "anthropic"] = "openai"
    OPENAI_API_KEY: Optional[str] = None
    OPENAI_MODEL: str = "gpt-4o"

    ANTHROPIC_API_KEY: Optional[str] = None
    ANTHROPIC_MODEL: str = "claude-3-5-sonnet-20241022"

    # Scraping & Enrichment
    FIRECRAWL_API_KEY: Optional[str] = None

    # CRM (HubSpot)
    HUBSPOT_ACCESS_TOKEN: Optional[str] = None
    HUBSPOT_PORTAL_ID: Optional[str] = None

    # Slack Notifications
    SLACK_WEBHOOK_URL: Optional[str] = None
    SLACK_MINIMUM_TIER_NOTIFICATION: Literal["S", "A", "B", "C"] = "A"

    # ICP Defaults
    TARGET_INDUSTRY: str = "B2B SaaS, FinTech, E-commerce, Enterprise Software"
    TARGET_EMPLOYEE_MIN: int = 50
    TARGET_EMPLOYEE_MAX: int = 5000
    TARGET_ANNUAL_REVENUE_MIN: str = "$5M"
    COMPANY_PRODUCT_OFFERING: str = "Enterprise AI RevOps Automation & Intelligent Lead Orchestration"


settings = Settings()
