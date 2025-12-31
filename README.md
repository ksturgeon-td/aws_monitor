# AWS Resource Monitor Dashboard

A web-based dashboard for monitoring AWS resources across multiple regions with cost tracking and projections.

## Features

- **Multi-Region Monitoring**: Automatically discovers and monitors resources across all enabled AWS regions
- **Resource Tracking**: Monitor EC2 instances, S3 buckets, Glue databases, SageMaker instances, and more
- **Cost Analysis**: View current costs, projections, and trends using AWS Cost Explorer
- **Real-time Updates**: Auto-refresh with configurable caching
- **Interactive Dashboard**: Web-based interface built with Streamlit

## Supported AWS Services

- EC2 (instances with status: running, stopped, terminated)
- S3 (buckets with size and object counts)
- Glue (databases and tables)
- SageMaker (notebook instances, training jobs, endpoints)
- Cost Explorer (cost analysis and projections)

## Prerequisites

- Python 3.8+
- AWS Account with appropriate permissions
- AWS CLI configured with credentials

## Quick Start

The easiest way to get started is using the automated setup script:

```bash
cd aws_monitor
./run.sh
```

This script will automatically:
- Create a virtual environment (if needed)
- Install all dependencies
- Load environment variables from `.env` (if present)
- Verify AWS credentials
- Launch the dashboard at `http://localhost:8501`

## Manual Installation

If you prefer to set up manually:

1. Clone or navigate to this directory:
```bash
cd aws_monitor
```

2. Create a virtual environment:
```bash
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Configure environment (optional):
```bash
cp .env.example .env
# Edit .env with your preferred settings
```

## AWS Credentials

The dashboard uses AWS CLI credentials or environment variables. The `run.sh` script will automatically verify your credentials before launching.

Configure AWS credentials using one of these methods:

**Option 1: AWS CLI (recommended)**
```bash
aws configure
```

**Option 2: Named profile in .env file**
```bash
# In .env file
AWS_PROFILE=your-profile-name
```

**Option 3: Environment variables**
```bash
export AWS_ACCESS_KEY_ID=your_access_key
export AWS_SECRET_ACCESS_KEY=your_secret_key
export AWS_DEFAULT_REGION=us-east-1
```

## Required IAM Permissions

Your AWS user/role needs the following permissions:

```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Action": [
      "ec2:DescribeInstances",
      "ec2:DescribeRegions",
      "s3:ListAllMyBuckets",
      "s3:GetBucketLocation",
      "glue:GetDatabases",
      "glue:GetTables",
      "sagemaker:ListNotebookInstances",
      "sagemaker:ListTrainingJobs",
      "sagemaker:ListEndpoints",
      "ce:GetCostAndUsage",
      "ce:GetCostForecast",
      "cloudwatch:GetMetricStatistics"
    ],
    "Resource": "*"
  }]
}
```

## Usage

**Quick Start (recommended):**
```bash
./run.sh
```

**Manual Start:**
```bash
source .venv/bin/activate  # Activate virtual environment first
streamlit run app.py
```

The dashboard will open in your default web browser at `http://localhost:8501`

## Configuration

Edit `.env` to customize:

- `RESOURCE_CACHE_TTL`: Cache duration for resource data (default: 300 seconds)
- `COST_CACHE_TTL`: Cache duration for cost data (default: 3600 seconds)
- `API_TIMEOUT`: Timeout for AWS API calls (default: 30 seconds)
- `MAX_PARALLEL_WORKERS`: Max concurrent API calls (default: 10)
- `ENABLED_REGIONS`: Specific regions to monitor (leave empty for all)

## Architecture

- **Streamlit**: Web dashboard framework
- **boto3**: AWS SDK for Python
- **Parallel Fetching**: Concurrent API calls across regions using ThreadPoolExecutor
- **Caching**: Streamlit native caching with configurable TTL
- **Modular Design**: Separate clients for each AWS service

## Troubleshooting

**No resources showing:**
- Check AWS credentials are configured correctly
- Verify IAM permissions are sufficient
- Check that you have resources in your AWS account

**Slow loading:**
- Reduce number of monitored regions in `.env`
- Increase cache TTL values
- Check network connectivity to AWS

**Cost data not available:**
- Ensure Cost Explorer is enabled in your AWS account
- Verify `ce:GetCostAndUsage` permission
- Note: Cost data has ~24-hour delay

## License

MIT
