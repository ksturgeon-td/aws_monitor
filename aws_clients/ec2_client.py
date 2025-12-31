"""EC2 instance monitoring client."""

import logging
from typing import Dict, List
from datetime import datetime
from aws_clients.base_client import BaseAWSClient

logger = logging.getLogger(__name__)


class EC2Client(BaseAWSClient):
    """Client for monitoring EC2 instances."""

    def __init__(self, region: str = None):
        """Initialize EC2 client.

        Args:
            region: AWS region (defaults to configured default region)
        """
        super().__init__('ec2', region)

    def get_instances(self) -> Dict:
        """Get all EC2 instances in the region.

        Returns:
            Dict containing:
            - instances: List of instance details
            - summary: Aggregated statistics
            - region: Region name
        """
        try:
            response = self.safe_api_call(
                self.client.describe_instances
            )

            if not response or 'Reservations' not in response:
                logger.warning(f"No EC2 data returned for region {self.region}")
                return self._empty_response()

            instances = []
            stats = {
                'running': 0,
                'stopped': 0,
                'terminated': 0,
                'other': 0
            }

            # Parse reservations and instances
            for reservation in response['Reservations']:
                for instance in reservation['Instances']:
                    instance_data = self._parse_instance(instance)
                    instances.append(instance_data)

                    # Update statistics
                    state = instance_data['state']
                    if state in stats:
                        stats[state] += 1
                    else:
                        stats['other'] += 1

            total_instances = len(instances)

            logger.info(
                f"Found {total_instances} EC2 instances in {self.region} "
                f"({stats['running']} running, {stats['stopped']} stopped)"
            )

            return {
                'instances': instances,
                'summary': {
                    'total': total_instances,
                    **stats
                },
                'region': self.region
            }

        except Exception as e:
            logger.error(f"Error fetching EC2 instances in {self.region}: {e}")
            return self._empty_response()

    def _parse_instance(self, instance: Dict) -> Dict:
        """Parse EC2 instance data into a simplified format.

        Args:
            instance: Raw instance data from AWS API

        Returns:
            Simplified instance dictionary
        """
        # Get tags as a dictionary
        tags = {}
        if 'Tags' in instance:
            tags = {tag['Key']: tag['Value'] for tag in instance['Tags']}

        # Get instance name from tags
        name = tags.get('Name', instance['InstanceId'])

        # Parse launch time
        launch_time = instance.get('LaunchTime')
        if launch_time:
            launch_time_str = launch_time.strftime('%Y-%m-%d %H:%M:%S')
        else:
            launch_time_str = 'N/A'

        return {
            'instance_id': instance['InstanceId'],
            'name': name,
            'instance_type': instance.get('InstanceType', 'Unknown'),
            'state': instance['State']['Name'],
            'availability_zone': instance['Placement']['AvailabilityZone'],
            'private_ip': instance.get('PrivateIpAddress', 'N/A'),
            'public_ip': instance.get('PublicIpAddress', 'N/A'),
            'launch_time': launch_time_str,
            'tags': tags,
            'region': self.region
        }

    def _empty_response(self) -> Dict:
        """Return an empty response structure.

        Returns:
            Empty response dictionary
        """
        return {
            'instances': [],
            'summary': {
                'total': 0,
                'running': 0,
                'stopped': 0,
                'terminated': 0,
                'other': 0
            },
            'region': self.region
        }
