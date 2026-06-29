import streamlit as st
import pandas as pd
import numpy as np
import io
import json
import os

from pyautoflow.transformation import run_pipeline
from pyautoflow.reporting.report_generator import generate_reports

st.set_page_config(
    page_title="PyAutoFlow — Workflow Automation",
    page_icon="🔄",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Styling
st.markdown("""
<style>
    .main-title {
        font-size: 3rem !important;
        font-weight: 700;
        background: linear-gradient(90deg, #36D1DC, #5B86E5);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.2rem;
    }
    .sub-title {
        font-size: 1.2rem;
        color: #6c757d;
        margin-bottom: 2rem;
    }
    .section-header {
        font-size: 1.8rem;
        font-weight: 600;
        border-bottom: 2px solid #5B86E5;
        padding-bottom: 0.5rem;
        margin-top: 1.5rem;
        margin-bottom: 1rem;
    }
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="main-title">PyAutoFlow 🔄</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-title">Python-Based Workflow Automation & Reporting Tool</div>', unsafe_allow_html=True)

# Sidebar - Settings & File Upload
st.sidebar.header("📁 Ingestion & Configuration")

uploaded_file = st.sidebar.file_uploader("Upload CSV or JSON file", type=["csv", "json"])

# Load data helper
@st.cache_data
def load_data(file_obj, is_csv=True):
    if is_csv:
        return pd.read_csv(file_obj)
    else:
        return pd.read_json(file_obj)

df = None
file_name = ""

if uploaded_file is not None:
    is_csv = uploaded_file.name.endswith('.csv')
    df = load_data(uploaded_file, is_csv=is_csv)
    file_name = uploaded_file.name
else:
    # Fallback to demo sample
    demo_option = st.sidebar.selectbox("No file uploaded. Choose a demo dataset:", ["Sample Sales (CSV)", "Sample Sales (JSON)"])
    base_dir = os.path.dirname(os.path.abspath(__file__))
    if "CSV" in demo_option:
        csv_path = os.path.join(base_dir, "data", "sample_input.csv")
        if os.path.exists(csv_path):
            df = pd.read_csv(csv_path)
            file_name = "sample_input.csv"
    else:
        json_path = os.path.join(base_dir, "data", "sample_input.json")
        if os.path.exists(json_path):
            df = pd.read_json(json_path)
            file_name = "sample_input.json"

if df is not None:
    st.sidebar.success(f"Loaded '{file_name}' ({df.shape[0]} rows, {df.shape[1]} columns)")

    # 1. Cleaning settings
    st.sidebar.markdown("### 🧹 1. Cleaning Settings")
    clean = st.sidebar.checkbox("Run Data Cleaning", value=True)
    missing_strategy = st.sidebar.selectbox("Missing Value Strategy", ["smart", "drop", "fill"], index=0)

    # 2. Filter settings
    st.sidebar.markdown("### 🔍 2. Filtering")
    filters_input = st.sidebar.text_area("Pandas query conditions (one per line)", value="units > 5\nrevenue > 0")
    filters = [f.strip() for f in filters_input.split('\n') if f.strip()]

    # 3. Derivations settings
    st.sidebar.markdown("### ➕ 3. Derived Columns")
    deriv_input = st.sidebar.text_area("Derivations (Col=Expr, one per line)", value="profit=revenue - cost\nmargin_pct=profit / revenue * 100")
    
    derivations = {}
    for line in deriv_input.split('\n'):
        if '=' in line:
            col, expr = line.split('=', 1)
            derivations[col.strip()] = expr.strip()

    # 4. Aggregation settings
    st.sidebar.markdown("### 📊 4. Group Aggregation")
    available_cols = list(df.columns)
    group_cols = st.sidebar.multiselect("Group by columns", options=available_cols, default=["region", "category"] if "region" in available_cols else [])
    
    agg_cols = st.sidebar.multiselect("Columns to aggregate", options=[c for c in available_cols if c not in group_cols], default=["revenue", "cost", "units"] if "revenue" in available_cols else [])
    agg_func = st.sidebar.selectbox("Aggregation function", ["sum", "mean", "min", "max", "count"], index=0)
    
    agg_map = {col: agg_func for col in agg_cols} if group_cols and agg_cols else None

    # 5. Rolling settings
    st.sidebar.markdown("### 📈 5. Rolling Statistics")
    rolling_col = st.sidebar.selectbox("Rolling stats column", options=["None"] + available_cols, index=0)
    rolling_window = st.sidebar.slider("Rolling window size", min_value=2, max_value=30, value=5)

    # 6. Outlier settings
    st.sidebar.markdown("### 🚨 6. Outlier Detection")
    outlier_col = st.sidebar.selectbox("Outlier detection column", options=["None"] + available_cols, index=0)
    outlier_multiplier = st.sidebar.slider("IQR Multiplier", min_value=1.0, max_value=3.0, value=1.5, step=0.1)

    # Trigger Pipeline
    run_btn = st.sidebar.button("🚀 Execute Workflow Pipeline", type="primary", use_container_width=True)

    # Display Preview of original data
    st.markdown('<div class="section-header">Raw Input Preview</div>', unsafe_allow_html=True)
    st.dataframe(df.head(10), use_container_width=True)

    # Run the transformation pipeline
    if run_btn or 'pipeline_results' in st.session_state:
        # Save results to session state to keep them across updates
        if run_btn or 'pipeline_results' not in st.session_state:
            with st.spinner("Processing workflow pipeline..."):
                r_col = None if rolling_col == "None" else rolling_col
                o_col = None if outlier_col == "None" else outlier_col
                
                results = run_pipeline(
                    df.copy(),
                    clean=clean,
                    missing_strategy=missing_strategy,
                    filters=filters if filters else None,
                    derivations=derivations if derivations else None,
                    group_by=group_cols if group_cols else None,
                    agg_map=agg_map if agg_map else None,
                    rolling_col=r_col,
                    rolling_window=rolling_window,
                    outlier_col=o_col,
                    outlier_multiplier=outlier_multiplier
                )
                st.session_state['pipeline_results'] = results

        results = st.session_state['pipeline_results']

        # Layout Tabs
        tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
            "✨ Cleaned & Transformed", 
            "📈 Statistical Summary", 
            "📊 Grouped Aggregation", 
            "⏱️ Rolling Stats",
            "🚨 Outliers",
            "📄 Generated Reports"
        ])

        with tab1:
            st.subheader("Cleaned & Transformed Data")
            st.dataframe(results["clean"], use_container_width=True)
            
            # Simple downloads
            csv_data = results["clean"].to_csv(index=False).encode('utf-8')
            st.download_button(
                label="📥 Download Cleaned CSV",
                data=csv_data,
                file_name=f"clean_{file_name}",
                mime="text/csv"
            )

        with tab2:
            st.subheader("Numeric Summary")
            st.dataframe(results["summary"], use_container_width=True)
            
            # Draw charts from numeric columns
            numeric_cols = results["clean"].select_dtypes(include=[np.number]).columns
            if len(numeric_cols) > 0:
                selected_chart_col = st.selectbox("Select column to visualize:", numeric_cols)
                st.bar_chart(results["clean"][selected_chart_col])

        with tab3:
            st.subheader("Group Aggregation Results")
            if "aggregated" in results:
                st.dataframe(results["aggregated"], use_container_width=True)
                
                # Chart
                if group_cols and len(agg_cols) > 0:
                    x_axis = group_cols[0]
                    y_axis = agg_cols[0]
                    st.markdown(f"**Visualizing {y_axis} by {x_axis}**")
                    st.bar_chart(data=results["aggregated"], x=x_axis, y=y_axis)
            else:
                st.info("Configure 'Group by columns' and 'Columns to aggregate' in the sidebar to view aggregation results.")

        with tab4:
            st.subheader("Rolling Statistics")
            if "rolling" in results:
                st.dataframe(results["rolling"], use_container_width=True)
                
                # Rolling Chart
                r_mean = f"{rolling_col}_rolling_mean"
                r_std = f"{rolling_col}_rolling_std"
                chart_data = results["rolling"][[rolling_col, r_mean, r_std]]
                st.line_chart(chart_data)
            else:
                st.info("Select a 'Rolling stats column' in the sidebar to generate rolling statistics.")

        with tab5:
            st.subheader("Outlier Detection")
            if "outliers" in results:
                st.write(f"Flagged **{len(results['outliers'])}** outlier record(s) in `{outlier_col}`")
                st.dataframe(results["outliers"], use_container_width=True)
            else:
                st.info("Select an 'Outlier detection column' in the sidebar to flag outliers.")

        with tab6:
            st.subheader("Pipeline Reports Download Center")
            
            # Generate reports using standard generator
            temp_out_dir = "temp_output"
            os.makedirs(temp_out_dir, exist_ok=True)
            
            written_paths = generate_reports(
                results,
                output_dir=temp_out_dir,
                formats=["csv", "json", "txt"],
                run_label="webapp_run"
            )
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.markdown("### 📊 CSV Reports")
                for path in written_paths.get("csv", []):
                    bname = os.path.basename(path)
                    with open(path, "rb") as f:
                        st.download_button(f"📥 Download {bname}", f.read(), file_name=bname, mime="text/csv")
                        
            with col2:
                st.markdown("### 🗄️ JSON Reports")
                for path in written_paths.get("json", []):
                    bname = os.path.basename(path)
                    with open(path, "rb") as f:
                        st.download_button(f"📥 Download {bname}", f.read(), file_name=bname, mime="application/json")
                        
            with col3:
                st.markdown("### 📄 Text Summary")
                for path in written_paths.get("txt", []):
                    bname = os.path.basename(path)
                    with open(path, "r", encoding="utf-8") as f:
                        report_content = f.read()
                        st.download_button(f"📥 Download {bname}", report_content, file_name=bname, mime="text/plain")
            
            # Display Plain Text Report summary directly in streamlit
            if written_paths.get("txt"):
                st.markdown("### 📋 Preview Text Report Summary")
                st.text_area("Pipeline Log Report Summary", report_content, height=400)
else:
    st.warning("Please upload a file or use one of the demo datasets to start.")
