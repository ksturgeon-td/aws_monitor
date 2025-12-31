"""Region management for multi-region AWS monitoring."""

import logging
from typing import List, Optional
from aws_clients.base_client import BaseAWSClient
from config.settings import settings

logger = logging.getLogger(__name__)


class RegionManager:
    """Manages AWS region discovery and filtering."""

    def __init__(self):
        """Initialize the region manager."""
        self._all_regions: Optional[List[str]] = None
        self._enabled_regions: Optional[List[str]] = None

    def get_all_regions(self) -> List[str]:
        """Get all available AWS regions.

        Returns:
            List of region names (e.g., ['us-east-1', 'us-west-2', ...])
        """
        if self._all_regions is not None:
            return self._all_regions

        try:
            # Use EC2 client to describe regions
            ec2_client = BaseAWSClient('ec2', region=settings.AWS_DEFAULT_REGION)
            response = ec2_client.safe_api_call(
                ec2_client.get_client().describe_regions,
                AllRegions=False  # Only get enabled regions
            )

            if response and 'Regions' in response:
                self._all_regions = [region['RegionName'] for region in response['Regions']]
                logger.info(f"Discovered {len(self._all_regions)} AWS regions")
                return self._all_regions
            else:
                logger.warning("Could not fetch regions, using default")
                self._all_regions = [settings.AWS_DEFAULT_REGION]
                return self._all_regions

        except Exception as e:
            logger.error(f"Error fetching regions: {e}. Using default region.")
            self._all_regions = [settings.AWS_DEFAULT_REGION]
            return self._all_regions

    def get_enabled_regions(self) -> List[str]:
        """Get regions to monitor based on configuration.

        Returns:
            List of region names to monitor. If ENABLED_REGIONS is set in
            settings, returns those. Otherwise, returns all available regions.
        """
        if self._enabled_regions is not None:
            return self._enabled_regions

        # Check if specific regions are configured
        if settings.ENABLED_REGIONS:
            self._enabled_regions = settings.ENABLED_REGIONS
            logger.info(
                f"Using configured regions: {', '.join(self._enabled_regions)}"
            )
        else:
            # Use all available regions
            self._enabled_regions = self.get_all_regions()
            logger.info(
                f"Monitoring all {len(self._enabled_regions)} enabled regions"
            )

        return self._enabled_regions

    def is_region_available(self, region: str) -> bool:
        """Check if a region is available.

        Args:
            region: Region name to check

        Returns:
            True if region is available, False otherwise
        """
        all_regions = self.get_all_regions()
        return region in all_regions

    def filter_regions(self, regions: List[str]) -> List[str]:
        """Filter out invalid regions from a list.

        Args:
            regions: List of region names to filter

        Returns:
            List of valid region names
        """
        all_regions = self.get_all_regions()
        valid_regions = [r for r in regions if r in all_regions]

        if len(valid_regions) < len(regions):
            invalid = set(regions) - set(valid_regions)
            logger.warning(f"Filtered out invalid regions: {', '.join(invalid)}")

        return valid_regions

    def get_region_display_name(self, region: str) -> str:
        """Get a human-readable display name for a region.

        Args:
            region: Region code (e.g., 'us-east-1')

        Returns:
            Display name (e.g., 'US East (N. Virginia)')
        """
        # Common region display names
        region_names = {
            'us-east-1': 'US East (N. Virginia)',
            'us-east-2': 'US East (Ohio)',
            'us-west-1': 'US West (N. California)',
            'us-west-2': 'US West (Oregon)',
            'eu-west-1': 'EU (Ireland)',
            'eu-west-2': 'EU (London)',
            'eu-west-3': 'EU (Paris)',
            'eu-central-1': 'EU (Frankfurt)',
            'eu-north-1': 'EU (Stockholm)',
            'ap-south-1': 'Asia Pacific (Mumbai)',
            'ap-northeast-1': 'Asia Pacific (Tokyo)',
            'ap-northeast-2': 'Asia Pacific (Seoul)',
            'ap-northeast-3': 'Asia Pacific (Osaka)',
            'ap-southeast-1': 'Asia Pacific (Singapore)',
            'ap-southeast-2': 'Asia Pacific (Sydney)',
            'ca-central-1': 'Canada (Central)',
            'sa-east-1': 'South America (São Paulo)',
        }

        return region_names.get(region, region)

    def clear_cache(self):
        """Clear cached region data."""
        self._all_regions = None
        self._enabled_regions = None
        logger.info("Cleared region cache")


# Create a singleton instance
region_manager = RegionManager()
