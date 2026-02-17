#!/bin/bash

# Enable required Vertex AI and Generative AI APIs

echo "Enabling Vertex AI APIs for project: cloud-comrades-0120692"
echo "============================================================"
echo ""

# Enable Vertex AI API
echo "1. Enabling Vertex AI API..."
gcloud services enable aiplatform.googleapis.com --project=cloud-comrades-0120692

# Enable Generative AI API (for Gemini models)
echo ""
echo "2. Enabling Generative AI API..."
gcloud services enable generativelanguage.googleapis.com --project=cloud-comrades-0120692

# Enable additional required APIs
echo ""
echo "3. Enabling additional APIs..."
gcloud services enable compute.googleapis.com --project=cloud-comrades-0120692

echo ""
echo "============================================================"
echo "✓ API enablement complete!"
echo ""
echo "Note: It may take a few minutes for the APIs to be fully activated."
echo "After enabling, you may need to:"
echo "  1. Accept Terms of Service for Generative AI in the Cloud Console"
echo "  2. Wait 5-10 minutes for model access to propagate"
echo ""
echo "To check if Gemini models are available, visit:"
echo "https://console.cloud.google.com/vertex-ai/generative/language/locations/us-central1"
