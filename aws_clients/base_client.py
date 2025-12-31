"""Base AWS client with credential handling and error management."""

import logging
import time
from typing import Any, Callable, Optional
import boto3
from botocore.exceptions import ClientError, NoCredentialsError, PartialCredentialsError
from config.settings import settings

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class BaseAWSClient:
    """Base class for all AWS service clients.

    Handles:
    - Credential management (follows AWS credential chain)
    - Region configuration
    - Error handling with retry logic
    - Exponential backoff
    """

    def __init__(self, service_name: str, region: str = None):
        """Initialize AWS client for a specific service.

        Args:
            service_name: AWS service name (e.g., 'ec2', 's3', 'glue')
            region: AWS region (defaults to settings.AWS_DEFAULT_REGION)

        Raises:
            NoCredentialsError: If AWS credentials are not configured
            ClientError: If there's an error creating the client
        """
        self.service_name = service_name
        self.region = region or settings.AWS_DEFAULT_REGION

        try:
            self.client = boto3.client(
                service_name,
                region_name=self.region
            )
            logger.info(f"Initialized {service_name} client for region {self.region}")
        except NoCredentialsError:
            logger.error(
                "AWS credentials not found. Please configure AWS CLI or set "
                "AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY environment variables."
            )
            raise
        except PartialCredentialsError:
            logger.error(
                "Incomplete AWS credentials. Please ensure both AWS_ACCESS_KEY_ID "
                "and AWS_SECRET_ACCESS_KEY are set."
            )
            raise
        except Exception as e:
            logger.error(f"Error creating {service_name} client: {e}")
            raise

    def safe_api_call(
        self,
        func: Callable,
        max_retries: int = 3,
        **kwargs
    ) -> Optional[Any]:
        """Execute an AWS API call with retry logic and error handling.

        Args:
            func: The boto3 client method to call
            max_retries: Maximum number of retry attempts
            **kwargs: Arguments to pass to the API call

        Returns:
            API response or None if all retries fail

        Handles:
        - Throttling with exponential backoff
        - Transient errors with retry
        - Permission errors (logged but not retried)
        """
        for attempt in range(max_retries):
            try:
                response = func(**kwargs)
                return response

            except ClientError as e:
                error_code = e.response['Error']['Code']
                error_message = e.response['Error']['Message']

                # Handle throttling
                if error_code in ['Throttling', 'ThrottlingException', 'RequestLimitExceeded']:
                    if attempt < max_retries - 1:
                        wait_time = 2 ** attempt  # Exponential backoff: 1s, 2s, 4s
                        logger.warning(
                            f"Throttled by AWS API. Retrying in {wait_time}s "
                            f"(attempt {attempt + 1}/{max_retries})"
                        )
                        time.sleep(wait_time)
                        continue
                    else:
                        logger.error(f"API throttled after {max_retries} attempts")
                        return None

                # Handle permission errors (don't retry)
                elif error_code in ['AccessDenied', 'UnauthorizedOperation', 'AccessDeniedException']:
                    logger.error(
                        f"Permission denied for {self.service_name}: {error_message}. "
                        f"Check IAM permissions."
                    )
                    return None

                # Handle other errors
                elif attempt < max_retries - 1:
                    wait_time = 2 ** attempt
                    logger.warning(
                        f"API call failed: {error_code} - {error_message}. "
                        f"Retrying in {wait_time}s (attempt {attempt + 1}/{max_retries})"
                    )
                    time.sleep(wait_time)
                    continue
                else:
                    logger.error(
                        f"API call failed after {max_retries} attempts: "
                        f"{error_code} - {error_message}"
                    )
                    return None

            except Exception as e:
                if attempt < max_retries - 1:
                    wait_time = 2 ** attempt
                    logger.warning(
                        f"Unexpected error: {str(e)}. "
                        f"Retrying in {wait_time}s (attempt {attempt + 1}/{max_retries})"
                    )
                    time.sleep(wait_time)
                    continue
                else:
                    logger.error(f"API call failed after {max_retries} attempts: {str(e)}")
                    return None

        return None

    def get_client(self):
        """Get the boto3 client instance."""
        return self.client

    def get_region(self) -> str:
        """Get the current region."""
        return self.region

    def get_service_name(self) -> str:
        """Get the service name."""
        return self.service_name
