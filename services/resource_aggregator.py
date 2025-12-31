"""Resource aggregation service for combining data from all AWS clients."""

import logging
from typing import Dict, List
from aws_clients.ec2_client import EC2Client
from aws_clients.s3_client import S3Client
from aws_clients.glue_client import GlueClient
from aws_clients.sagemaker_client import SageMakerClient
from aws_clients.region_manager import region_manager
from services.parallel_fetcher import parallel_fetcher

logger = logging.getLogger(__name__)


class ResourceAggregator:
    """Aggregates resource data from all AWS services across regions."""

    def __init__(self):
        """Initialize the resource aggregator."""
        pass

    def fetch_all_resources(self, regions: List[str] = None) -> Dict:
        """Fetch all resources from all enabled services.

        Args:
            regions: List of regions to query (defaults to all enabled regions)

        Returns:
            Dictionary containing all resource data organized by service
        """
        if regions is None:
            regions = region_manager.get_enabled_regions()

        logger.info(f"Fetching all resources from {len(regions)} regions")

        result = {
            'ec2': self.fetch_ec2_resources(regions),
            's3': self.fetch_s3_resources(),  # S3 is global
            'glue': self.fetch_glue_resources(regions),
            'sagemaker': self.fetch_sagemaker_resources(regions),
            'regions_queried': regions,
            'total_regions': len(regions)
        }

        return result

    def fetch_ec2_resources(self, regions: List[str]) -> Dict:
        """Fetch EC2 instances from all regions.

        Args:
            regions: List of regions to query

        Returns:
            Aggregated EC2 data
        """
        logger.info(f"Fetching EC2 instances from {len(regions)} regions")

        def fetch_ec2_from_region(region: str) -> Dict:
            """Fetch EC2 data from a single region."""
            try:
                client = EC2Client(region=region)
                return client.get_instances()
            except Exception as e:
                logger.error(f"Error fetching EC2 from {region}: {e}")
                return {'error': str(e), 'region': region}

        # Fetch in parallel
        region_results = parallel_fetcher.fetch_from_regions(
            regions=regions,
            fetch_function=fetch_ec2_from_region
        )

        # Aggregate results
        all_instances = []
        total_running = 0
        total_stopped = 0
        total_terminated = 0
        successful_regions = []
        errors = []

        for region, result in region_results.items():
            if 'error' in result:
                errors.append({'region': region, 'error': result['error']})
            else:
                successful_regions.append(region)
                all_instances.extend(result.get('instances', []))

                summary = result.get('summary', {})
                total_running += summary.get('running', 0)
                total_stopped += summary.get('stopped', 0)
                total_terminated += summary.get('terminated', 0)

        logger.info(
            f"EC2 Summary: {len(all_instances)} total instances "
            f"({total_running} running, {total_stopped} stopped, "
            f"{total_terminated} terminated)"
        )

        return {
            'instances': all_instances,
            'summary': {
                'total': len(all_instances),
                'running': total_running,
                'stopped': total_stopped,
                'terminated': total_terminated
            },
            'successful_regions': successful_regions,
            'errors': errors
        }

    def fetch_s3_resources(self) -> Dict:
        """Fetch S3 buckets (S3 is global, no need for multi-region).

        Returns:
            S3 bucket data
        """
        logger.info("Fetching S3 buckets")

        try:
            # S3 is global, just use one client
            client = S3Client()
            result = client.get_buckets()

            logger.info(
                f"S3 Summary: {result['summary']['total']} buckets, "
                f"{result['summary']['total_size_gb']:.2f} GB"
            )

            return result

        except Exception as e:
            logger.error(f"Error fetching S3 buckets: {e}")
            return {
                'buckets': [],
                'summary': {
                    'total': 0,
                    'total_size_bytes': 0,
                    'total_size_gb': 0
                },
                'error': str(e)
            }

    def fetch_glue_resources(self, regions: List[str]) -> Dict:
        """Fetch Glue databases from all regions.

        Args:
            regions: List of regions to query

        Returns:
            Aggregated Glue data
        """
        logger.info(f"Fetching Glue databases from {len(regions)} regions")

        def fetch_glue_from_region(region: str) -> Dict:
            """Fetch Glue data from a single region."""
            try:
                client = GlueClient(region=region)
                return client.get_databases()
            except Exception as e:
                logger.error(f"Error fetching Glue from {region}: {e}")
                return {'error': str(e), 'region': region}

        # Fetch in parallel
        region_results = parallel_fetcher.fetch_from_regions(
            regions=regions,
            fetch_function=fetch_glue_from_region
        )

        # Aggregate results
        all_databases = []
        total_databases = 0
        total_tables = 0
        successful_regions = []
        errors = []

        for region, result in region_results.items():
            if 'error' in result:
                errors.append({'region': region, 'error': result['error']})
            else:
                successful_regions.append(region)
                all_databases.extend(result.get('databases', []))

                summary = result.get('summary', {})
                total_databases += summary.get('total_databases', 0)
                total_tables += summary.get('total_tables', 0)

        logger.info(
            f"Glue Summary: {total_databases} databases with {total_tables} tables"
        )

        return {
            'databases': all_databases,
            'summary': {
                'total_databases': total_databases,
                'total_tables': total_tables
            },
            'successful_regions': successful_regions,
            'errors': errors
        }

    def fetch_sagemaker_resources(self, regions: List[str]) -> Dict:
        """Fetch SageMaker resources from all regions.

        Args:
            regions: List of regions to query

        Returns:
            Aggregated SageMaker data
        """
        logger.info(f"Fetching SageMaker resources from {len(regions)} regions")

        def fetch_sagemaker_from_region(region: str) -> Dict:
            """Fetch SageMaker data from a single region."""
            try:
                client = SageMakerClient(region=region)
                return client.get_resources()
            except Exception as e:
                logger.error(f"Error fetching SageMaker from {region}: {e}")
                return {'error': str(e), 'region': region}

        # Fetch in parallel
        region_results = parallel_fetcher.fetch_from_regions(
            regions=regions,
            fetch_function=fetch_sagemaker_from_region
        )

        # Aggregate results
        all_notebooks = []
        all_endpoints = []
        all_training_jobs = []
        total_active_notebooks = 0
        total_active_endpoints = 0
        successful_regions = []
        errors = []

        for region, result in region_results.items():
            if 'error' in result:
                errors.append({'region': region, 'error': result['error']})
            else:
                successful_regions.append(region)
                all_notebooks.extend(result.get('notebook_instances', []))
                all_endpoints.extend(result.get('endpoints', []))
                all_training_jobs.extend(result.get('training_jobs', []))

                summary = result.get('summary', {})
                total_active_notebooks += summary.get('active_notebooks', 0)
                total_active_endpoints += summary.get('active_endpoints', 0)

        logger.info(
            f"SageMaker Summary: {len(all_notebooks)} notebooks, "
            f"{len(all_endpoints)} endpoints, {len(all_training_jobs)} training jobs"
        )

        return {
            'notebook_instances': all_notebooks,
            'endpoints': all_endpoints,
            'training_jobs': all_training_jobs,
            'summary': {
                'total_notebooks': len(all_notebooks),
                'active_notebooks': total_active_notebooks,
                'total_endpoints': len(all_endpoints),
                'active_endpoints': total_active_endpoints,
                'total_training_jobs': len(all_training_jobs)
            },
            'successful_regions': successful_regions,
            'errors': errors
        }

    def get_resource_summary(self, resources: Dict) -> Dict:
        """Generate a high-level summary of all resources.

        Args:
            resources: Full resource data from fetch_all_resources()

        Returns:
            Summary statistics
        """
        ec2_summary = resources.get('ec2', {}).get('summary', {})
        s3_summary = resources.get('s3', {}).get('summary', {})
        glue_summary = resources.get('glue', {}).get('summary', {})
        sagemaker_summary = resources.get('sagemaker', {}).get('summary', {})

        return {
            'ec2': {
                'total_instances': ec2_summary.get('total', 0),
                'running_instances': ec2_summary.get('running', 0),
                'stopped_instances': ec2_summary.get('stopped', 0)
            },
            's3': {
                'total_buckets': s3_summary.get('total', 0),
                'total_size_gb': s3_summary.get('total_size_gb', 0)
            },
            'glue': {
                'total_databases': glue_summary.get('total_databases', 0),
                'total_tables': glue_summary.get('total_tables', 0)
            },
            'sagemaker': {
                'total_notebooks': sagemaker_summary.get('total_notebooks', 0),
                'active_notebooks': sagemaker_summary.get('active_notebooks', 0),
                'total_endpoints': sagemaker_summary.get('total_endpoints', 0)
            },
            'regions': {
                'queried': resources.get('total_regions', 0)
            }
        }


# Create a singleton instance
resource_aggregator = ResourceAggregator()
