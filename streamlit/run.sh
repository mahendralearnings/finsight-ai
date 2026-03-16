#!/bin/bash
# FinSight AI - Streamlit Demo Runner

echo "============================================"
echo "  FinSight AI - Streamlit Demo"
echo "============================================"

# Check if streamlit is installed
if ! command -v streamlit &> /dev/null; then
    echo "Installing Streamlit..."
    pip install streamlit requests
fi

# Check if API key is set
if grep -q "YOUR_API_KEY_HERE" app.py; then
    echo ""
    echo "⚠️  WARNING: API key not set!"
    echo ""
    echo "Get your API key:"
    echo "  cd ~/finsight-ai/terraform"
    echo "  terraform output -raw api_key_value"
    echo ""
    echo "Then edit app.py and replace YOUR_API_KEY_HERE"
    echo ""
fi

# Run Streamlit
echo "Starting Streamlit..."
echo "Open in browser: http://localhost:8501"
echo ""
streamlit run app.py
