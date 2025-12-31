"""AWS Cost Explorer client for cost monitoring and projections."""

import logging
from typing import Dict, List
from datetime import datetime, timedelta
from aws_clients.base_client import BaseAWSClient

logger = logging.getLogger(__name__)


class CostExplorerClient(BaseAWSClient):
    """Client for monitoring AWS costs and generating projections."""

    def __init__(self, region: str = 'us-east-1'):
        """Initialize Cost Explorer client.

        Note: Cost Explorer is a global service, typically accessed via us-east-1

        Args:
            region: AWS region (defaults to us-east-1)
        """
        super().__init__('ce', region)

    def get_cost_and_usage(self) -> Dict:
        """Get comprehensive cost and usage data.

        Returns:
            Dict containing:
            - mtd_cost: Month-to-date cost
            - daily_costs: List of daily costs for the past 30 days
            - service_costs: Cost breakdown by service
            - projections: End-of-month cost projection
        """
        try:
            # Calculate date ranges
            today = datetime.now().date()
            month_start = today.replace(day=1)
            month_end_date = (month_start + timedelta(days=32)).replace(day=1) - timedelta(days=1)
            thirty_days_ago = today - timedelta(days=30)

            # Get MTD costs
            mtd_cost = self._get_cost_for_period(
                start_date=month_start,
                end_date=today
            )

            # Get daily costs for the past 30 days
            daily_costs = self._get_daily_costs(
                start_date=thirty_days_ago,
                end_date=today
            )

            # Get service breakdown
            service_costs = self._get_service_breakdown(
                start_date=month_start,
                end_date=today
            )

            # Calculate projections
            days_in_month = month_end_date.day
            days_elapsed = today.day
            daily_average = mtd_cost / days_elapsed if days_elapsed > 0 else 0
            projected_eom = daily_average * days_in_month

            # Get yesterday's cost
            yesterday = today - timedelta(days=1)
            yesterday_cost = self._get_cost_for_period(yesterday, today)

            logger.info(
                f"Cost Summary: MTD=${mtd_cost:.2f}, Projected=${projected_eom:.2f}, "
                f"Daily Avg=${daily_average:.2f}"
            )

            return {
                'mtd_cost': round(mtd_cost, 2),
                'projected_eom_cost': round(projected_eom, 2),
                'daily_average': round(daily_average, 2),
                'yesterday_cost': round(yesterday_cost, 2),
                'daily_costs': daily_costs,
                'service_costs': service_costs,
                'metadata': {
                    'month_start': str(month_start),
                    'today': str(today),
                    'days_elapsed': days_elapsed,
                    'days_in_month': days_in_month
                }
            }

        except Exception as e:
            logger.error(f"Error fetching cost data: {e}")
            return self._empty_response()

    def _get_cost_for_period(self, start_date, end_date) -> float:
        """Get total cost for a specific period.

        Args:
            start_date: Start date
            end_date: End date

        Returns:
            Total cost for the period
        """
        try:
            response = self.safe_api_call(
                self.client.get_cost_and_usage,
                TimePeriod={
                    'Start': str(start_date),
                    'End': str(end_date)
                },
                Granularity='MONTHLY',
                Metrics=['UnblendedCost']
            )

            if not response or 'ResultsByTime' not in response:
                return 0.0

            total_cost = 0.0
            for result in response['ResultsByTime']:
                amount = result.get('Total', {}).get('UnblendedCost', {}).get('Amount', '0')
                total_cost += float(amount)

            return total_cost

        except Exception as e:
            logger.debug(f"Error getting cost for period: {e}")
            return 0.0

    def _get_daily_costs(self, start_date, end_date) -> List[Dict]:
        """Get daily cost breakdown.

        Args:
            start_date: Start date
            end_date: End date

        Returns:
            List of daily cost entries
        """
        try:
            response = self.safe_api_call(
                self.client.get_cost_and_usage,
                TimePeriod={
                    'Start': str(start_date),
                    'End': str(end_date)
                },
                Granularity='DAILY',
                Metrics=['UnblendedCost']
            )

            if not response or 'ResultsByTime' not in response:
                return []

            daily_costs = []
            for result in response['ResultsByTime']:
                date = result.get('TimePeriod', {}).get('Start', 'Unknown')
                amount = result.get('Total', {}).get('UnblendedCost', {}).get('Amount', '0')

                daily_costs.append({
                    'date': date,
                    'cost': round(float(amount), 2)
                })

            return daily_costs

        except Exception as e:
            logger.debug(f"Error getting daily costs: {e}")
            return []

    def _get_service_breakdown(self, start_date, end_date) -> List[Dict]:
        """Get cost breakdown by AWS service.

        Args:
            start_date: Start date
            end_date: End date

        Returns:
            List of service cost entries
        """
        try:
            response = self.safe_api_call(
                self.client.get_cost_and_usage,
                TimePeriod={
                    'Start': str(start_date),
                    'End': str(end_date)
                },
                Granularity='MONTHLY',
                Metrics=['UnblendedCost'],
                GroupBy=[{
                    'Type': 'DIMENSION',
                    'Key': 'SERVICE'
                }]
            )

            if not response or 'ResultsByTime' not in response:
                return []

            service_costs = []

            # Aggregate service costs from all time periods
            service_totals = {}
            for result in response['ResultsByTime']:
                for group in result.get('Groups', []):
                    service_name = group.get('Keys', ['Unknown'])[0]
                    amount = group.get('Metrics', {}).get('UnblendedCost', {}).get('Amount', '0')
                    cost = float(amount)

                    if service_name in service_totals:
                        service_totals[service_name] += cost
                    else:
                        service_totals[service_name] = cost

            # Convert to list and sort by cost
            for service, cost in service_totals.items():
                service_costs.append({
                    'service': service,
                    'cost': round(cost, 2)
                })

            service_costs.sort(key=lambda x: x['cost'], reverse=True)

            return service_costs

        except Exception as e:
            logger.debug(f"Error getting service breakdown: {e}")
            return []

    def _empty_response(self) -> Dict:
        """Return an empty response structure.

        Returns:
            Empty response dictionary
        """
        return {
            'mtd_cost': 0.0,
            'projected_eom_cost': 0.0,
            'daily_average': 0.0,
            'yesterday_cost': 0.0,
            'daily_costs': [],
            'service_costs': [],
            'metadata': {}
        }
