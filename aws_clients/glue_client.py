"""AWS Glue database and table monitoring client."""

import logging
from typing import Dict, List
from aws_clients.base_client import BaseAWSClient

logger = logging.getLogger(__name__)


class GlueClient(BaseAWSClient):
    """Client for monitoring AWS Glue databases and tables."""

    def __init__(self, region: str = None):
        """Initialize Glue client.

        Args:
            region: AWS region (defaults to configured default region)
        """
        super().__init__('glue', region)

    def get_databases(self) -> Dict:
        """Get all Glue databases in the region.

        Returns:
            Dict containing:
            - databases: List of database details with their tables
            - summary: Aggregated statistics
            - region: Region name
        """
        try:
            response = self.safe_api_call(
                self.client.get_databases
            )

            if not response or 'DatabaseList' not in response:
                logger.warning(f"No Glue data returned for region {self.region}")
                return self._empty_response()

            databases = []
            total_tables = 0

            # Parse databases
            for db in response['DatabaseList']:
                database_name = db['Name']

                # Get tables for this database
                tables = self._get_tables(database_name)
                table_count = len(tables)
                total_tables += table_count

                database_data = {
                    'name': database_name,
                    'description': db.get('Description', 'N/A'),
                    'location': db.get('LocationUri', 'N/A'),
                    'create_time': db.get('CreateTime', 'N/A'),
                    'table_count': table_count,
                    'tables': tables,
                    'region': self.region
                }

                databases.append(database_data)

            total_databases = len(databases)

            logger.info(
                f"Found {total_databases} Glue databases with {total_tables} tables "
                f"in {self.region}"
            )

            return {
                'databases': databases,
                'summary': {
                    'total_databases': total_databases,
                    'total_tables': total_tables
                },
                'region': self.region
            }

        except Exception as e:
            logger.error(f"Error fetching Glue databases in {self.region}: {e}")
            return self._empty_response()

    def _get_tables(self, database_name: str) -> List[Dict]:
        """Get all tables in a database.

        Args:
            database_name: Name of the database

        Returns:
            List of table details
        """
        try:
            tables = []
            next_token = None

            # Handle pagination
            while True:
                params = {'DatabaseName': database_name}
                if next_token:
                    params['NextToken'] = next_token

                response = self.safe_api_call(
                    self.client.get_tables,
                    **params
                )

                if not response or 'TableList' not in response:
                    break

                for table in response['TableList']:
                    table_data = {
                        'name': table['Name'],
                        'database': database_name,
                        'create_time': str(table.get('CreateTime', 'N/A')),
                        'update_time': str(table.get('UpdateTime', 'N/A')),
                        'table_type': table.get('TableType', 'N/A'),
                        'parameters': table.get('Parameters', {}),
                    }
                    tables.append(table_data)

                # Check for more pages
                next_token = response.get('NextToken')
                if not next_token:
                    break

            return tables

        except Exception as e:
            logger.debug(f"Error fetching tables for database {database_name}: {e}")
            return []

    def _empty_response(self) -> Dict:
        """Return an empty response structure.

        Returns:
            Empty response dictionary
        """
        return {
            'databases': [],
            'summary': {
                'total_databases': 0,
                'total_tables': 0
            },
            'region': self.region
        }
