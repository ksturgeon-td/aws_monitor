"""S3 bucket monitoring client."""

import logging
from typing import Dict, List
from datetime import datetime, timedelta
from aws_clients.base_client import BaseAWSClient

logger = logging.getLogger(__name__)


class S3Client(BaseAWSClient):
    """Client for monitoring S3 buckets."""

    def __init__(self, region: str = None):
        """Initialize S3 client.

        Note: S3 is a global service, but we still track bucket regions.

        Args:
            region: AWS region (defaults to configured default region)
        """
        super().__init__('s3', region)
        # CloudWatch metrics for S3 are only available in us-east-1
        try:
            self.cloudwatch_client = BaseAWSClient('cloudwatch', 'us-east-1')
        except Exception as e:
            logger.warning(f"Could not create CloudWatch client: {e}")
            self.cloudwatch_client = None

    def get_buckets(self) -> Dict:
        """Get all S3 buckets (S3 is global, returns all buckets).

        Returns:
            Dict containing:
            - buckets: List of bucket details
            - summary: Aggregated statistics
            - region: Region name (for consistency with other clients)
        """
        try:
            response = self.safe_api_call(
                self.client.list_buckets
            )

            if not response or 'Buckets' not in response:
                logger.warning("No S3 bucket data returned")
                return self._empty_response()

            buckets = []
            total_size_bytes = 0

            # Parse buckets
            for bucket in response['Buckets']:
                bucket_data = self._parse_bucket(bucket)
                buckets.append(bucket_data)

                # Sum up sizes (if available)
                if bucket_data['size_bytes'] > 0:
                    total_size_bytes += bucket_data['size_bytes']

            total_buckets = len(buckets)
            total_size_gb = total_size_bytes / (1024 ** 3) if total_size_bytes > 0 else 0

            logger.info(
                f"Found {total_buckets} S3 buckets "
                f"({total_size_gb:.2f} GB total)"
            )

            return {
                'buckets': buckets,
                'summary': {
                    'total': total_buckets,
                    'total_size_bytes': total_size_bytes,
                    'total_size_gb': round(total_size_gb, 2)
                },
                'region': self.region  # For consistency
            }

        except Exception as e:
            logger.error(f"Error fetching S3 buckets: {e}")
            return self._empty_response()

    def _parse_bucket(self, bucket: Dict) -> Dict:
        """Parse S3 bucket data into a simplified format.

        Args:
            bucket: Raw bucket data from AWS API

        Returns:
            Simplified bucket dictionary
        """
        bucket_name = bucket['Name']
        creation_date = bucket.get('CreationDate')

        # Get bucket region
        bucket_region = self._get_bucket_region(bucket_name)

        # Get bucket size (using CloudWatch metrics)
        size_bytes, object_count = self._get_bucket_metrics(bucket_name)

        # Format creation date
        if creation_date:
            creation_date_str = creation_date.strftime('%Y-%m-%d %H:%M:%S')
        else:
            creation_date_str = 'N/A'

        return {
            'name': bucket_name,
            'region': bucket_region,
            'creation_date': creation_date_str,
            'size_bytes': size_bytes,
            'size_gb': round(size_bytes / (1024 ** 3), 2) if size_bytes > 0 else 0,
            'object_count': object_count
        }

    def _get_bucket_region(self, bucket_name: str) -> str:
        """Get the region of a bucket.

        Args:
            bucket_name: Name of the bucket

        Returns:
            Region name or 'Unknown'
        """
        try:
            response = self.safe_api_call(
                self.client.get_bucket_location,
                Bucket=bucket_name
            )

            if response and 'LocationConstraint' in response:
                # LocationConstraint is None for us-east-1
                region = response['LocationConstraint'] or 'us-east-1'
                return region
            else:
                return 'Unknown'

        except Exception as e:
            logger.debug(f"Could not get region for bucket {bucket_name}: {e}")
            return 'Unknown'

    def _get_bucket_metrics(self, bucket_name: str) -> tuple:
        """Get bucket size and object count from CloudWatch metrics.

        Falls back to direct S3 API calls if CloudWatch metrics are unavailable.

        Args:
            bucket_name: Name of the bucket

        Returns:
            Tuple of (size_bytes, object_count)
        """
        # Try CloudWatch metrics first (faster, but has 24-hour lag)
        if self.cloudwatch_client:
            try:
                end_time = datetime.utcnow()
                start_time = end_time - timedelta(days=2)  # Get last 2 days of data

                # Get bucket size
                size_response = self.cloudwatch_client.safe_api_call(
                    self.cloudwatch_client.get_client().get_metric_statistics,
                    Namespace='AWS/S3',
                    MetricName='BucketSizeBytes',
                    Dimensions=[
                        {'Name': 'BucketName', 'Value': bucket_name},
                        {'Name': 'StorageType', 'Value': 'StandardStorage'}
                    ],
                    StartTime=start_time,
                    EndTime=end_time,
                    Period=86400,  # 1 day
                    Statistics=['Average']
                )

                size_bytes = 0
                if size_response and 'Datapoints' in size_response and size_response['Datapoints']:
                    # Get the most recent datapoint
                    datapoints = sorted(
                        size_response['Datapoints'],
                        key=lambda x: x['Timestamp'],
                        reverse=True
                    )
                    size_bytes = int(datapoints[0]['Average'])

                # Get object count
                count_response = self.cloudwatch_client.safe_api_call(
                    self.cloudwatch_client.get_client().get_metric_statistics,
                    Namespace='AWS/S3',
                    MetricName='NumberOfObjects',
                    Dimensions=[
                        {'Name': 'BucketName', 'Value': bucket_name},
                        {'Name': 'StorageType', 'Value': 'AllStorageTypes'}
                    ],
                    StartTime=start_time,
                    EndTime=end_time,
                    Period=86400,
                    Statistics=['Average']
                )

                object_count = 0
                if count_response and 'Datapoints' in count_response and count_response['Datapoints']:
                    datapoints = sorted(
                        count_response['Datapoints'],
                        key=lambda x: x['Timestamp'],
                        reverse=True
                    )
                    object_count = int(datapoints[0]['Average'])

                # If we got valid data from CloudWatch, return it
                if size_bytes > 0 or object_count > 0:
                    logger.debug(
                        f"Got CloudWatch metrics for {bucket_name}: "
                        f"{size_bytes} bytes, {object_count} objects"
                    )
                    return (size_bytes, object_count)

            except Exception as e:
                logger.debug(f"CloudWatch metrics unavailable for {bucket_name}: {e}")

        # Fallback to direct S3 API (more accurate, but slower)
        logger.debug(f"Using direct S3 API for bucket metrics: {bucket_name}")
        return self._get_bucket_metrics_direct(bucket_name)

    def _get_bucket_metrics_direct(self, bucket_name: str) -> tuple:
        """Get bucket size and object count using direct S3 API calls.

        This is slower but more accurate than CloudWatch metrics.
        Limits to first 1000 objects to avoid timeouts.

        Args:
            bucket_name: Name of the bucket

        Returns:
            Tuple of (size_bytes, object_count)
        """
        try:
            size_bytes = 0
            object_count = 0
            max_objects = 1000  # Limit to avoid timeouts on large buckets

            # List objects (up to max_objects)
            paginator = self.client.get_paginator('list_objects_v2')
            page_iterator = paginator.paginate(
                Bucket=bucket_name,
                PaginationConfig={'MaxItems': max_objects}
            )

            for page in page_iterator:
                if 'Contents' in page:
                    for obj in page['Contents']:
                        size_bytes += obj.get('Size', 0)
                        object_count += 1

            if object_count >= max_objects:
                logger.debug(
                    f"Bucket {bucket_name} has 1000+ objects, "
                    f"showing partial count (size may be underestimated)"
                )

            return (size_bytes, object_count)

        except Exception as e:
            logger.debug(f"Could not get direct metrics for bucket {bucket_name}: {e}")
            return (0, 0)

    def _empty_response(self) -> Dict:
        """Return an empty response structure.

        Returns:
            Empty response dictionary
        """
        return {
            'buckets': [],
            'summary': {
                'total': 0,
                'total_size_bytes': 0,
                'total_size_gb': 0
            },
            'region': self.region
        }
