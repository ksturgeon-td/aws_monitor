"""Configuration management for AWS Monitor Dashboard."""

import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class Settings:
    """Application settings loaded from environment variables."""

    # AWS Configuration
    AWS_DEFAULT_REGION = os.getenv('AWS_DEFAULT_REGION', 'us-east-1')
    AWS_PROFILE = os.getenv('AWS_PROFILE', 'default')

    # Cache Configuration (in seconds)
    RESOURCE_CACHE_TTL = int(os.getenv('RESOURCE_CACHE_TTL', 300))  # 5 minutes
    COST_CACHE_TTL = int(os.getenv('COST_CACHE_TTL', 3600))  # 1 hour

    # API Configuration
    API_TIMEOUT = int(os.getenv('API_TIMEOUT', 30))  # 30 seconds
    MAX_PARALLEL_WORKERS = int(os.getenv('MAX_PARALLEL_WORKERS', 10))

    # UI Configuration
    PAGE_TITLE = "AWS Resource Monitor"
    PAGE_ICON = "☁️"
    LAYOUT = "wide"

    # Regions to monitor (empty list = all regions)
    ENABLED_REGIONS = [r.strip() for r in os.getenv('ENABLED_REGIONS', '').split(',') if r.strip()]

    @classmethod
    def get_all(cls) -> dict:
        """Get all settings as a dictionary."""
        return {
            key: value for key, value in cls.__dict__.items()
            if not key.startswith('_') and not callable(value)
        }


# Create a singleton instance
settings = Settings()
