"""Parallel execution of AWS API calls across multiple regions."""

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Callable, Dict, List, Any
from config.settings import settings

logger = logging.getLogger(__name__)


class ParallelFetcher:
    """Execute AWS API calls in parallel across multiple regions."""

    def __init__(self, max_workers: int = None):
        """Initialize parallel fetcher.

        Args:
            max_workers: Maximum number of parallel workers
                        (defaults to settings.MAX_PARALLEL_WORKERS)
        """
        self.max_workers = max_workers or settings.MAX_PARALLEL_WORKERS

    def fetch_from_regions(
        self,
        regions: List[str],
        fetch_function: Callable[[str], Dict],
        timeout: int = None
    ) -> Dict[str, Any]:
        """Fetch resources from multiple regions in parallel.

        Args:
            regions: List of AWS region names
            fetch_function: Function to call for each region.
                          Should accept region name as parameter.
            timeout: Timeout in seconds for each fetch operation
                    (defaults to settings.API_TIMEOUT)

        Returns:
            Dictionary mapping region names to results.
            Regions that failed will have an 'error' key in their result.
        """
        timeout = timeout or settings.API_TIMEOUT
        results = {}

        if not regions:
            logger.warning("No regions specified for parallel fetch")
            return results

        logger.info(
            f"Fetching resources from {len(regions)} regions in parallel "
            f"(max {self.max_workers} workers)"
        )

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit all tasks
            future_to_region = {
                executor.submit(fetch_function, region): region
                for region in regions
            }

            # Collect results as they complete
            for future in as_completed(future_to_region):
                region = future_to_region[future]

                try:
                    result = future.result(timeout=timeout)
                    results[region] = result
                    logger.debug(f"Successfully fetched data from {region}")

                except TimeoutError:
                    logger.error(f"Timeout fetching data from {region}")
                    results[region] = {
                        'error': f'Timeout after {timeout}s',
                        'region': region
                    }

                except Exception as e:
                    logger.error(f"Error fetching data from {region}: {e}")
                    results[region] = {
                        'error': str(e),
                        'region': region
                    }

        successful = sum(1 for r in results.values() if 'error' not in r)
        logger.info(
            f"Parallel fetch completed: {successful}/{len(regions)} regions successful"
        )

        return results

    def aggregate_results(self, region_results: Dict[str, Dict]) -> Dict:
        """Aggregate results from multiple regions.

        Args:
            region_results: Dictionary of results from each region

        Returns:
            Aggregated results with global summary
        """
        all_items = []
        errors = []
        successful_regions = []

        for region, result in region_results.items():
            if 'error' in result:
                errors.append({
                    'region': region,
                    'error': result['error']
                })
            else:
                successful_regions.append(region)

                # Extract items (works for instances, buckets, etc.)
                if 'instances' in result:
                    all_items.extend(result['instances'])
                elif 'buckets' in result:
                    all_items.extend(result['buckets'])
                elif 'databases' in result:
                    all_items.extend(result['databases'])
                elif 'items' in result:
                    all_items.extend(result['items'])

        return {
            'items': all_items,
            'total_count': len(all_items),
            'successful_regions': successful_regions,
            'failed_regions': [e['region'] for e in errors],
            'errors': errors
        }


# Create a singleton instance
parallel_fetcher = ParallelFetcher()
