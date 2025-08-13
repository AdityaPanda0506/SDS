# app.py
import streamlit as st
import json
import os
from datetime import datetime

# Import your RDKit-free SDS generator
from sds_generator import generate_sds, generate_docx

# -----------------------------
# Page Configuration
# -----------------------------
st.set_page_config(
    page_title="MEDxAI - SDS Generator",
    page_icon="🧪",
    layout="wide"
)

# -----------------------------
# Custom CSS for MEDxAI Branding
# -----------------------------
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Roboto:wght@300;400;500;700&display=swap');

    html, body, [class*="css"] {
        font-family: 'Roboto', sans-serif;
    }

    .medxai-header {
        background: linear-gradient(135deg, #1e3c72, #2a5298);
        color: white;
        padding: 2rem;
        border-radius: 12px;
        text-align: center;
        box-shadow: 0 4px 12px rgba(0,0,0,0.1);
        margin-bottom: 2rem;
    }

    .medxai-header h1 {
        margin: 0;
        font-size: 2.5rem;
        font-weight: 700;
    }

    .medxai-header p {
        margin: 0.5rem 0 0;
        font-size: 1.1rem;
        opacity: 0.9;
    }

    .stButton>button {
        background: #1e3c72;
        color: white;
        border: none;
        border-radius: 8px;
        padding: 0.6rem 1.2rem;
        font-weight: 500;
    }

    .stButton>button:hover {
        background: #2a5298;
    }

    .section-card {
        background: white;
        border: 1px solid #e0e0e0;
        border-radius: 10px;
        padding: 1rem;
        margin-bottom: 1rem;
        box-shadow: 0 2px 6px rgba(0,0,0,0.05);
    }

    .section-title {
        font-size: 1.3rem;
        font-weight: 600;
        color: #1e3c72;
        margin-bottom: 0.8rem;
        padding-bottom: 0.5rem;
        border-bottom: 2px solid #e0e0e0;
    }

    .note-box {
        background-color: #f8f9fa;
        border-left: 4px solid #2a5298;
        padding: 10px 15px;
        margin: 10px 0;
        border-radius: 4px;
        font-size: 0.95em;
        color: #495057;
    }

    .disclaimer {
        font-size: 0.85em;
        color: #6c757d;
        font-style: italic;
        text-align: center;
        margin-top: 3rem;
    }
</style>
""", unsafe_allow_html=True)

# -----------------------------
# Header: MEDxAI Branding
# -----------------------------
st.markdown("""
<div class="medxai-header">
    <h1>🧪 MEDxAI</h1>
    <p>AI-Powered Safety Data Sheet Generator for Research Molecules</p>
</div>
""", unsafe_allow_html=True)

# -----------------------------
# Sidebar Input
# -----------------------------
with st.sidebar:
    st.header("🔍 Input Molecule")
    smiles = st.text_input(
        "Enter SMILES String:",
        placeholder="e.g., CC(=O)OC1=CC=CC=C1C(=O)O",
        help="Simplified Molecular Input Line Entry System (SMILES)"
    )

    st.markdown("---")
    st.markdown("### 🛠️ Actions")
    generate_btn = st.button("Generate SDS Report", type="primary")

    st.markdown("---")
    st.markdown("""
    <div style="font-size:0.9em; color:#555;">
    <strong>How to Use:</strong><br>
    1. Enter a valid SMILES string.<br>
    2. Click "Generate SDS Report".<br>
    3. View, download, or export the SDS.
    </div>
    """, unsafe_allow_html=True)

# -----------------------------
# Main Content
# -----------------------------
if generate_btn or smiles:
    if not smiles.strip():
        st.warning("Please enter a SMILES string to generate the SDS.")
    else:
        with st.spinner("Fetching data from PubChem..."):
            # No RDKit validation — use PubChem to validate
            sds = generate_sds(smiles.strip())
            if sds is None:
                st.error("❌ Could not process the SMILES string. Please check spelling or try another compound.")
            else:
                compound_name = sds["Section1"]["data"].get("Product Identifier", "Unknown Compound")
                st.success(f"✅ SDS Generated for: **{compound_name}**")

                # Tabs
                tab1, tab2, tab3 = st.tabs(["📋 Report", "📥 Download DOCX", "📦 Export JSON"])

                # -----------------------------
                # Tab 1: Interactive SDS Report
                # -----------------------------
                with tab1:
                    st.subheader("📋 Safety Data Sheet (SDS) - All 16 Sections")

                    for i in range(1, 17):
                        section_key = f"Section{i}"
                        section = sds.get(section_key, {})
                        title = section.get("title", f"Section {i}")
                        data = section.get("data", {})

                        with st.expander(f"**{i}. {title}**", expanded=(i == 1)):
                            st.markdown('<div class="section-card">', unsafe_allow_html=True)
                            st.markdown(f'<div class="section-title">{title}</div>', unsafe_allow_html=True)

                            if data:
                                for key, value in data.items():
                                    if isinstance(value, list):
                                        val = "<br>".join([f"• {v}" for v in value if v]) or "Not available"
                                    elif not value or value == "Not available":
                                        val = "<em>Not available</em>"
                                    else:
                                        val = str(value)

                                    if i == 3 and "Hazard" in key:
                                        st.markdown(f"""
                                        <div style="background:#ffe6e6; border-left:5px solid #ff4d4d; padding:10px; margin:5px 0; border-radius:4px;">
                                            <strong>{key}:</strong> {val}
                                        </div>
                                        """, unsafe_allow_html=True)
                                    else:
                                        st.markdown(f"**{key}:** {val}", unsafe_allow_html=True)
                            else:
                                st.markdown("*No data available.*")

                            st.markdown('</div>', unsafe_allow_html=True)

                # -----------------------------
                # Tab 2: Download DOCX
                # -----------------------------
                with tab2:
                    st.subheader("📥 Download DOCX (Word Document)")

                    if st.button("📄 Generate & Download DOCX", type="primary"):
                        with st.spinner("Generating Word document..."):
                            docx_path = generate_docx(sds, compound_name)
                            if os.path.exists(docx_path):
                                with open(docx_path, "rb") as f:
                                    st.download_button(
                                        label="⬇️ Download Word (.docx)",
                                        data=f.read(),
                                        file_name=f"SDS_{compound_name.replace(' ', '_')}.docx",
                                        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                                    )
                                # Clean up
                                os.remove(docx_path)
                            else:
                                st.error("Failed to generate DOCX.")

                # -----------------------------
                # Tab 3: Export JSON
                # -----------------------------
                with tab3:
                    st.subheader("📦 Export Raw JSON Data")
                    st.markdown("Get the structured SDS data in JSON format for integration or analysis.")

                    json_str = json.dumps(sds, indent=2)
                    st.download_button(
                        label="⬇️ Download JSON",
                        data=json_str,
                        file_name=f"sds_{compound_name.replace(' ', '_')}.json",
                        mime="application/json"
                    )
                    with st.expander("👁️ Preview JSON"):
                        st.json(sds)

# -----------------------------
# Footer / Disclaimer
# -----------------------------
st.markdown("""
<hr>
<div class="disclaimer">
    Disclaimer: This report is generated for <strong>research use only</strong>. 
    Always verify with lab testing and official regulatory sources before handling any chemical.
    MEDxAI does not assume liability for misuse or incorrect data interpretation.
</div>
""", unsafe_allow_html=True)
