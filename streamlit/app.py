"""
FinSight AI - Streamlit Demo
A visual interface for your RAG-powered financial intelligence API.
"""
import streamlit as st
import requests
import os
from dotenv import load_dotenv

# =============================================================================
# Load Environment Variables
# =============================================================================
load_dotenv()

API_URL = os.getenv("FINSIGHT_API_URL", "")
API_KEY = os.getenv("FINSIGHT_API_KEY", "")

# =============================================================================
# Page Configuration
# =============================================================================
st.set_page_config(
    page_title="FinSight AI",
    page_icon="📊",
    layout="wide"
)

# =============================================================================
# Custom CSS
# =============================================================================
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        background: linear-gradient(90deg, #1e88e5, #42a5f5);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0;
    }
    .sub-header {
        color: #666;
        font-size: 1.1rem;
        margin-top: 0;
    }
    .source-box {
        background-color: #f0f7ff;
        border-left: 4px solid #1e88e5;
        padding: 10px 15px;
        margin: 10px 0;
        border-radius: 0 8px 8px 0;
    }
    .env-warning {
        background-color: #fff3cd;
        border: 1px solid #ffc107;
        border-radius: 8px;
        padding: 15px;
        margin: 10px 0;
    }
</style>
""", unsafe_allow_html=True)

# =============================================================================
# Header
# =============================================================================
st.markdown('<p class="main-header">📊 FinSight AI</p>', unsafe_allow_html=True)
st.markdown('<p class="sub-header">RAG-Powered Financial Intelligence Platform</p>', unsafe_allow_html=True)
st.markdown("---")

# =============================================================================
# Check Environment Variables
# =============================================================================
if not API_URL or not API_KEY:
    st.markdown("""
    <div class="env-warning">
        <h4>⚠️ Environment Variables Not Set</h4>
        <p>Create a <code>.env</code> file with:</p>
        <pre>
FINSIGHT_API_URL=https://your-api-gateway-url/prod/query
FINSIGHT_API_KEY=your_api_key_here
        </pre>
        <p>Then restart the app.</p>
    </div>
    """, unsafe_allow_html=True)
    st.stop()

# =============================================================================
# Sidebar - Info
# =============================================================================
with st.sidebar:
    st.header("📈 About")
    st.markdown("""
    **FinSight AI** uses:
    - 🔍 **pgvector** for semantic search
    - 🧠 **Claude 3 Haiku** for answers
    - 📄 **SEC Filings** as knowledge base
    
    Built on AWS with:
    - API Gateway
    - Lambda
    - RDS PostgreSQL
    - Amazon Bedrock
    """)
    
    st.markdown("---")
    st.header("✅ Config Status")
    st.success("API URL: Loaded")
    st.success("API Key: Loaded")
    
    st.markdown("---")
    st.header("💡 Sample Questions")
    st.markdown("""
    - What were Apple's revenue drivers?
    - Summarize the 10-K filing
    - What are the risk factors?
    - How did iPhone sales perform?
    """)

# =============================================================================
# Main Query Interface
# =============================================================================
col1, col2 = st.columns([3, 1])

with col1:
    query = st.text_input(
        "🔍 Ask a question about financial data",
        placeholder="e.g., What were Apple's revenue drivers in 2023?",
        key="query_input"
    )

with col2:
    search_button = st.button("🚀 Search", type="primary", use_container_width=True)

# Quick question buttons
st.markdown("**Quick questions:**")
quick_cols = st.columns(4)
quick_questions = [
    "What were Apple revenue drivers?",
    "Summarize the 10-K filing",
    "What are the risk factors?",
    "How did services revenue grow?"
]

for i, q in enumerate(quick_questions):
    if quick_cols[i].button(q, key=f"quick_{i}"):
        query = q
        search_button = True

# =============================================================================
# Query Execution
# =============================================================================
if search_button and query:
    with st.spinner("🔍 Searching financial documents..."):
        try:
            response = requests.post(
                API_URL,
                headers={
                    "Content-Type": "application/json",
                    "x-api-key": API_KEY
                },
                json={"query": query},
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                
                # Display answer
                st.markdown("### 💬 Answer")
                st.markdown(data.get("answer", "No answer returned"))
                
                # Display metrics
                st.markdown("### 📊 Details")
                metric_cols = st.columns(3)
                
                sources = data.get("sources", [])
                metric_cols[0].metric("📄 Sources", len(sources))
                
                chunks = data.get("chunks", 0)
                metric_cols[1].metric("🧩 Chunks", chunks)
                
                top_results = data.get("top_results", [])
                if top_results:
                    similarity = top_results[0].get("similarity", 0)
                    metric_cols[2].metric("🎯 Similarity", f"{similarity:.2%}")
                
                # Source details
                if sources:
                    st.markdown("### 📚 Sources")
                    for source in sources:
                        st.markdown(f"""
                        <div class="source-box">
                            📄 <strong>{source}</strong>
                        </div>
                        """, unsafe_allow_html=True)
                
                # Top results details
                if top_results:
                    with st.expander("🔍 View Retrieved Chunks"):
                        for i, result in enumerate(top_results):
                            st.markdown(f"""
                            **Chunk {i+1}** | Source: `{result.get('source', 'N/A')}` | 
                            Ticker: `{result.get('ticker', 'N/A')}` | 
                            Similarity: `{result.get('similarity', 0):.4f}`
                            """)
                            st.markdown("---")
                
                # Raw response
                with st.expander("🔧 Raw API Response"):
                    st.json(data)
            
            elif response.status_code == 403:
                st.error("🔒 Invalid API key. Check your .env file.")
            elif response.status_code == 400:
                st.error(f"❌ Bad request: {response.text}")
            else:
                st.error(f"❌ Error {response.status_code}: {response.text}")
                
        except requests.exceptions.Timeout:
            st.error("⏱️ Request timed out. The Lambda might be cold starting.")
        except requests.exceptions.ConnectionError:
            st.error("🔌 Connection error. Check your internet connection.")
        except Exception as e:
            st.error(f"❌ Error: {str(e)}")

# =============================================================================
# Footer
# =============================================================================
st.markdown("---")
st.markdown("""
<div style="text-align: center; color: #888; font-size: 0.9rem;">
    <p>FinSight AI | Built with AWS Bedrock, Lambda, pgvector & Streamlit</p>
    <p>Developer: Mahendra Nali</p>
</div>
""", unsafe_allow_html=True)
