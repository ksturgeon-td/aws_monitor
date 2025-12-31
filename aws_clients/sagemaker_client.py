"""AWS SageMaker monitoring client."""

import logging
from typing import Dict, List
from datetime import datetime
from aws_clients.base_client import BaseAWSClient

logger = logging.getLogger(__name__)


class SageMakerClient(BaseAWSClient):
    """Client for monitoring AWS SageMaker resources."""

    def __init__(self, region: str = None):
        """Initialize SageMaker client.

        Args:
            region: AWS region (defaults to configured default region)
        """
        super().__init__('sagemaker', region)

    def get_resources(self) -> Dict:
        """Get all SageMaker resources in the region.

        Returns:
            Dict containing:
            - notebook_instances: List of notebook instance details
            - endpoints: List of endpoint details
            - training_jobs: List of recent training jobs
            - summary: Aggregated statistics
            - region: Region name
        """
        try:
            notebook_instances = self._get_notebook_instances()
            endpoints = self._get_endpoints()
            training_jobs = self._get_recent_training_jobs()

            # Calculate summary statistics
            active_notebooks = sum(
                1 for nb in notebook_instances if nb['status'] == 'InService'
            )
            active_endpoints = sum(
                1 for ep in endpoints if ep['status'] == 'InService'
            )
            running_training = sum(
                1 for tj in training_jobs if tj['status'] == 'InProgress'
            )

            logger.info(
                f"Found {len(notebook_instances)} notebook instances, "
                f"{len(endpoints)} endpoints, {len(training_jobs)} training jobs "
                f"in {self.region}"
            )

            return {
                'notebook_instances': notebook_instances,
                'endpoints': endpoints,
                'training_jobs': training_jobs,
                'summary': {
                    'total_notebooks': len(notebook_instances),
                    'active_notebooks': active_notebooks,
                    'total_endpoints': len(endpoints),
                    'active_endpoints': active_endpoints,
                    'total_training_jobs': len(training_jobs),
                    'running_training_jobs': running_training
                },
                'region': self.region
            }

        except Exception as e:
            logger.error(f"Error fetching SageMaker resources in {self.region}: {e}")
            return self._empty_response()

    def _get_notebook_instances(self) -> List[Dict]:
        """Get all SageMaker notebook instances.

        Returns:
            List of notebook instance details
        """
        try:
            response = self.safe_api_call(
                self.client.list_notebook_instances,
                MaxResults=100
            )

            if not response or 'NotebookInstances' not in response:
                return []

            instances = []
            for nb in response['NotebookInstances']:
                instance_data = {
                    'name': nb['NotebookInstanceName'],
                    'instance_type': nb.get('InstanceType', 'N/A'),
                    'status': nb.get('NotebookInstanceStatus', 'Unknown'),
                    'creation_time': str(nb.get('CreationTime', 'N/A')),
                    'last_modified': str(nb.get('LastModifiedTime', 'N/A')),
                    'url': nb.get('Url', 'N/A'),
                    'region': self.region
                }
                instances.append(instance_data)

            return instances

        except Exception as e:
            logger.debug(f"Error fetching notebook instances: {e}")
            return []

    def _get_endpoints(self) -> List[Dict]:
        """Get all SageMaker endpoints.

        Returns:
            List of endpoint details
        """
        try:
            response = self.safe_api_call(
                self.client.list_endpoints,
                MaxResults=100
            )

            if not response or 'Endpoints' not in response:
                return []

            endpoints = []
            for ep in response['Endpoints']:
                endpoint_data = {
                    'name': ep['EndpointName'],
                    'status': ep.get('EndpointStatus', 'Unknown'),
                    'creation_time': str(ep.get('CreationTime', 'N/A')),
                    'last_modified': str(ep.get('LastModifiedTime', 'N/A')),
                    'region': self.region
                }
                endpoints.append(endpoint_data)

            return endpoints

        except Exception as e:
            logger.debug(f"Error fetching endpoints: {e}")
            return []

    def _get_recent_training_jobs(self, max_results: int = 20) -> List[Dict]:
        """Get recent SageMaker training jobs.

        Args:
            max_results: Maximum number of training jobs to retrieve

        Returns:
            List of training job details
        """
        try:
            response = self.safe_api_call(
                self.client.list_training_jobs,
                MaxResults=max_results,
                SortBy='CreationTime',
                SortOrder='Descending'
            )

            if not response or 'TrainingJobSummaries' not in response:
                return []

            jobs = []
            for job in response['TrainingJobSummaries']:
                job_data = {
                    'name': job['TrainingJobName'],
                    'status': job.get('TrainingJobStatus', 'Unknown'),
                    'creation_time': str(job.get('CreationTime', 'N/A')),
                    'training_start': str(job.get('TrainingStartTime', 'N/A')),
                    'training_end': str(job.get('TrainingEndTime', 'N/A')),
                    'region': self.region
                }
                jobs.append(job_data)

            return jobs

        except Exception as e:
            logger.debug(f"Error fetching training jobs: {e}")
            return []

    def _empty_response(self) -> Dict:
        """Return an empty response structure.

        Returns:
            Empty response dictionary
        """
        return {
            'notebook_instances': [],
            'endpoints': [],
            'training_jobs': [],
            'summary': {
                'total_notebooks': 0,
                'active_notebooks': 0,
                'total_endpoints': 0,
                'active_endpoints': 0,
                'total_training_jobs': 0,
                'running_training_jobs': 0
            },
            'region': self.region
        }
