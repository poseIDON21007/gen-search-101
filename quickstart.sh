#!/bin/bash

# Quick Start Script for Product Embeddings Pipeline
# This script guides you through the setup process

set -e  # Exit on error

echo "🚀 Product Embeddings Pipeline - Quick Start"
echo "=============================================="
echo ""

# Check Python version
echo "Checking Python version..."
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed. Please install Python 3.8 or higher."
    exit 1
fi

python_version=$(python3 --version 2>&1 | awk '{print $2}')
echo "✓ Found Python $python_version"
echo ""

# Check if gcloud is installed
echo "Checking gcloud CLI..."
if ! command -v gcloud &> /dev/null; then
    echo "⚠️  gcloud CLI is not installed."
    echo "   Install from: https://cloud.google.com/sdk/docs/install"
    echo "   Or continue with service account authentication"
    echo ""
else
    gcloud_version=$(gcloud version --format="value(core.version)" 2>/dev/null)
    echo "✓ Found gcloud CLI version $gcloud_version"
    echo ""
fi

# Create .env file if it doesn't exist
if [ ! -f .env ]; then
    echo "Creating .env file..."
    cp .env.example .env
    echo "✓ Created .env file"
    echo ""
    echo "📝 Please edit .env file and add your GCP_PROJECT_ID"
    echo "   Use: nano .env"
    echo ""
    read -p "Press Enter after you've updated the .env file..."
else
    echo "✓ Found existing .env file"
    echo ""
fi

# Install Python dependencies
echo "Installing Python dependencies..."
if [ -f requirements.txt ]; then
    pip3 install -q -r requirements.txt
    echo "✓ Installed all dependencies"
else
    echo "❌ requirements.txt not found"
    exit 1
fi
echo ""

# Source .env file
if [ -f .env ]; then
    export $(cat .env | grep -v '^#' | xargs)
fi

# Check if project ID is set
if [ -z "$GCP_PROJECT_ID" ] || [ "$GCP_PROJECT_ID" = "your-project-id-here" ]; then
    echo "❌ GCP_PROJECT_ID not set in .env file"
    echo "   Please edit .env and set your project ID"
    exit 1
fi

echo "✓ Using GCP Project: $GCP_PROJECT_ID"
echo ""

# Authenticate
echo "Checking authentication..."
echo "Choose authentication method:"
echo "  1) gcloud CLI (recommended for local development)"
echo "  2) Service Account JSON key"
echo ""
read -p "Enter choice (1 or 2): " auth_choice

if [ "$auth_choice" = "1" ]; then
    echo "Authenticating with gcloud..."
    gcloud auth application-default login
    gcloud config set project $GCP_PROJECT_ID
    echo "✓ Authenticated successfully"
elif [ "$auth_choice" = "2" ]; then
    read -p "Enter path to service account JSON key: " key_path
    if [ -f "$key_path" ]; then
        export GOOGLE_APPLICATION_CREDENTIALS="$key_path"
        echo "✓ Using service account key: $key_path"
    else
        echo "❌ File not found: $key_path"
        exit 1
    fi
else
    echo "❌ Invalid choice"
    exit 1
fi
echo ""

# Enable APIs
echo "Enabling required APIs..."
echo "This may take a few minutes..."

gcloud services enable aiplatform.googleapis.com --project=$GCP_PROJECT_ID 2>/dev/null || echo "  - Vertex AI API already enabled"
gcloud services enable bigquery.googleapis.com --project=$GCP_PROJECT_ID 2>/dev/null || echo "  - BigQuery API already enabled"

echo "✓ APIs enabled"
echo ""

# List JSON files
echo "Found the following product data files:"
ls -lh *.json 2>/dev/null | awk '{print "  - " $9 " (" $5 ")"}'
echo ""

# Confirm before running
echo "Ready to create embeddings and upload to BigQuery!"
echo ""
echo "This will:"
echo "  1. Load all JSON product files"
echo "  2. Create embeddings using Vertex AI"
echo "  3. Store data in BigQuery dataset: $BIGQUERY_DATASET_ID"
echo "  4. Table name: $BIGQUERY_TABLE_ID"
echo ""
echo "Estimated time: 8-10 minutes for ~2,500 products"
echo "Estimated cost: Less than $0.15"
echo ""

read -p "Do you want to proceed? (y/n): " confirm

if [ "$confirm" = "y" ] || [ "$confirm" = "Y" ]; then
    echo ""
    echo "🚀 Starting pipeline..."
    echo ""
    python3 create_embeddings_pipeline.py
    
    echo ""
    echo "=============================================="
    echo "✅ Pipeline completed successfully!"
    echo "=============================================="
    echo ""
    echo "Next steps:"
    echo "  1. View your data in BigQuery Console:"
    echo "     https://console.cloud.google.com/bigquery?project=$GCP_PROJECT_ID"
    echo ""
    echo "  2. Try vector search:"
    echo "     python3 vector_search.py"
    echo ""
    echo "  3. See README.md for sample queries"
    echo ""
else
    echo "Cancelled."
    exit 0
fi
