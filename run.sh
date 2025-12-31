#!/bin/bash
# Quick start script for AWS Resource Monitor Dashboard

echo "🚀 Starting AWS Resource Monitor Dashboard..."
echo ""

# Check if virtual environment exists
if [ ! -d ".venv" ]; then
    echo "📦 Virtual environment not found. Creating one..."
    python3 -m venv .venv
    echo "✅ Virtual environment created"
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source .venv/bin/activate

# Install/update dependencies
echo "📥 Installing dependencies..."
pip install -q --upgrade pip
pip install -q -r requirements.txt
echo "✅ Dependencies installed"

# Load environment variables from .env if it exists
if [ -f ".env" ]; then
    echo ""
    echo "📄 Loading environment variables from .env..."
    export $(grep -v '^#' .env | xargs)
    echo "✅ Environment variables loaded"

    # If AWS_PROFILE is set, display it
    if [ ! -z "$AWS_PROFILE" ]; then
        echo "   Using AWS Profile: $AWS_PROFILE"
    fi
fi

# Check AWS credentials (optional check - boto3 will handle this)
echo ""
echo "🔑 AWS credential check..."
if [ ! -z "$AWS_PROFILE" ]; then
    # Check with specific profile
    if aws sts get-caller-identity --profile "$AWS_PROFILE" > /dev/null 2>&1; then
        echo "✅ AWS credentials configured (profile: $AWS_PROFILE)"
    else
        echo "⚠️  Could not verify AWS profile '$AWS_PROFILE'"
        echo "   The dashboard will attempt to use it anyway (boto3 may succeed)"
        echo "   If you encounter errors, check your AWS configuration"
    fi
elif aws sts get-caller-identity > /dev/null 2>&1; then
    echo "✅ AWS credentials configured (default profile)"
else
    echo "⚠️  Could not verify AWS credentials"
    echo "   The dashboard will still start - boto3 will attempt to find credentials"
    echo "   If you encounter errors, configure AWS credentials:"
    echo "   - Run: aws configure"
    echo "   - Or set AWS_PROFILE in .env file"
    echo "   - Or set AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY in .env"
fi

# Run Streamlit app
echo ""
echo "🌐 Launching dashboard..."
echo "   Dashboard will open at: http://localhost:8501"
echo ""
streamlit run app.py
