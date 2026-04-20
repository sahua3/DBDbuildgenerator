from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    # Database
    database_url: str = "postgresql+asyncpg://dbd:dbdpassword@localhost:5432/dbd_builds"

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # Anthropic
    anthropic_api_key: Optional[str] = None

    # App
    secret_key: str = "dev-secret-key"
    environment: str = "development"
    cors_origins: str = "http://localhost:5173,http://localhost:3000"

    # Scraping schedules
    nightlight_scrape_interval_hours: int = 6
    shrine_scrape_cron_hour: int = 12
    shrine_scrape_cron_timezone: str = "America/New_York"

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",")]

    @property
    def use_real_ai(self) -> bool:
        return bool(self.anthropic_api_key)

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()


# Perk categories — canonical list used throughout the app
PERK_CATEGORIES = [
    "healing",
    "stealth",
    "chase",
    "gen_speed",
    "information",
    "altruism",
    "escape",
    "anti_hook",
    "aura_reading",
    "exhaustion",
    "endurance",
    "second_chance",
]

CATEGORY_DISPLAY = {
    "healing": "Healing",
    "stealth": "Stealth",
    "chase": "Chase",
    "gen_speed": "Gen Speed",
    "information": "Information",
    "altruism": "Altruism",
    "escape": "Escape",
    "anti_hook": "Anti-Hook",
    "aura_reading": "Aura Reading",
    "exhaustion": "Exhaustion",
    "endurance": "Endurance",
    "second_chance": "Second Chance",
}
