# lift_dashboard.py
import streamlit as st
import requests
import pandas as pd
from datetime import datetime, timedelta
import plotly.graph_objects as go
import plotly.express as px
import time
from PIL import Image
import io
import pytz

# Set your timezone here
YOUR_TIMEZONE = 'Asia/Kathmandu'

# Page config
st.set_page_config(
    page_title="Lift Capacity Monitor",
    layout="wide",
    page_icon="🏢",
    initial_sidebar_state="expanded"
)

# Initialize theme state before CSS
if 'theme' not in st.session_state:
    st.session_state.theme = 'Light'

def inject_custom_css():
    is_dark = st.session_state.theme == 'Dark'

    # Professional Light Mode vs Tech Dark Mode
    if is_dark:
        bg_main = "#0f172a"
        bg_card = "#1e293b"
        sidebar = "#0f172a"
        text_main = "#f8fafc"
        text_muted = "#94a3b8"
        border = "#334155"
        accent = "#3b82f6"
    else:
        bg_main = "#EEF2FF"      # soft indigo/lavender tint 
        bg_card = "#F8F7FF"      # very light purple card
        sidebar = "#F0F4FF"      # slightly deeper lavender sidebar
        text_main = "#1E1B4B"    # deep indigo text
        text_muted = "#6B7280"
        border = "#C7D2FE"       # indigo-tinted border
        accent = "#4F46E5"       # strong indigo accent

    css = f"""
    <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.0/font/bootstrap-icons.css">
    <style>
        :root {{
            --bg-main:      {bg_main};
            --bg-card:      {bg_card};
            --sidebar:      {sidebar};
            --accent:       {accent};
            --text-main:    {text_main};
            --text-muted:   {text_muted};
            --border:       {border};
            --success:      #10b981;
            --warning:      #f59e0b;
            --danger:       #ef4444;
            --radius:       8px;
        }}

        /* ── Page base ── */
        html, body, .stApp {{
            font-family: 'Inter', sans-serif !important;
            background-color: var(--bg-main) !important;
            color: var(--text-main) !important;
        }}
        [data-testid="stAppViewContainer"] {{
            background-color: var(--bg-main) !important;
        }}
        .main .block-container {{
            padding-top: 0rem !important;
            margin-top: -8rem !important; /* Extremely aggressive negative margin to kill top gap */
            padding-bottom: 2rem !important;
            max-width: 1400px !important;
        }}

        [data-testid="stVerticalBlock"] > [data-testid="stVerticalBlockBorderWrapper"]:first-child {{
            margin-top: 0 !important;
            padding-top: 0 !important;
        }}  

        [data-testid="stAppViewBlockContainer"] {{
            padding-top: 0rem !important;
        }}

        /* ── Sidebar ── */
        [data-testid="stSidebar"] {{
            background: var(--sidebar) !important;
            border-right: 1px solid var(--border) !important;
        }}
        [data-testid="stSidebar"] * {{
            color: var(--text-main) !important;
        }}
        [data-testid="stSidebar"] h1,
        [data-testid="stSidebar"] h2,
        [data-testid="stSidebar"] h3,
        [data-testid="stSidebar"] strong {{
            color: var(--text-main) !important;
            font-weight: 700 !important;
        }}
        [data-testid="stSidebar"] hr {{
            border-color: var(--border) !important;
        }}

        /* ── Hero header ── */
        .main-header {{
            font-size: 1.8rem;
            font-weight: 700;
            color: var(--text-main);
            margin-bottom: 0px;
            letter-spacing: -0.5px;
        }}
        .sub-header {{
            font-size: 1.1rem;
            font-weight: 600;
            color: var(--text-main);
            padding-bottom: 0.8rem;
            border-bottom: 1px solid var(--border);
            margin-bottom: 1.5rem;
            margin-top: 1.5rem;
        }}

        /* ── KPI cards ── */
        .metric-card {{
            background: var(--bg-card);
            border-radius: var(--radius);
            padding: 1.5rem 1.2rem;
            margin-bottom: 1.5rem;
            border: 1px solid var(--border);
            box-shadow: 0 4px 6px -1px rgb(0 0 0 / 0.05), 0 2px 4px -2px rgb(0 0 0 / 0.05);
            display: flex;
            flex-direction: column;
            justify-content: center;
        }}
        .metric-value {{
            font-size: 2.2rem;
            font-weight: 700;
            color: var(--accent) !important;
            line-height: 1;
            letter-spacing: -1px;
        }}
        .metric-label {{
            font-size: 0.85rem;
            font-weight: 500;
            color: var(--text-muted) !important;
            margin-top: 0.5rem;
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }}

        /* ── Status banners ── */
        .status-box {{
            padding: 1rem 1.2rem;
            border-radius: var(--radius);
            margin: 1rem 0;
            font-weight: 600;
            font-size: 0.95rem;
            border-left: 4px solid;
            background: var(--bg-card);
        }}
        .status-box-ok      {{ border-left-color: var(--success); color: var(--success) !important; }}
        .status-box-warning {{ border-left-color: var(--warning); color: var(--warning) !important; }}
        .status-box-danger  {{ border-left-color: var(--danger); color: var(--danger) !important; }}

        /* ── Info box ── */
        .info-box {{
            background: var(--bg-card);
            padding: 1.2rem 1.5rem;
            border-radius: var(--radius);
            border: 1px solid var(--border);
            margin: 1rem 0;
            color: var(--text-main) !important;
            font-size: 0.95rem;
        }}

        /* ── Tabs ── */
        .stTabs [data-baseweb="tab-list"] {{
            gap: 2rem;
            border-bottom: 1px solid var(--border);
            padding-bottom: 0px;
        }}
        .stTabs [data-baseweb="tab"] {{
            background: transparent;
            color: var(--text-muted);
            border: none;
            font-weight: 500;
            font-size: 0.95rem;
            padding: 0.8rem 0;
            margin-bottom: -1px;
        }}
        .stTabs [aria-selected="true"] {{
            color: var(--accent) !important;
            border-bottom: 2px solid var(--accent) !important;
            font-weight: 600;
        }}

        /* ── Buttons ── */
        .stButton > button {{
            background: var(--accent) !important;
            color: #ffffff !important;
            border: none !important;
            border-radius: 6px !important;
            font-weight: 500 !important;
            font-size: 0.9rem !important;
            padding: 0.6rem 1.5rem !important;
            transition: opacity 0.2s ease !important;
        }}
        .stButton > button:hover {{
            opacity: 0.9 !important;
        }}

        /* ── Upload box ── */
        .upload-box {{
            border: 1px dashed var(--border);
            border-radius: var(--radius);
            padding: 3rem 2rem;
            text-align: center;
            background: var(--bg-card);
            margin: 1rem 0;
        }}

        /* ── Image container ── */
        .image-container {{
            border-radius: var(--radius);
            overflow: hidden;
            border: 1px solid var(--border);
            background: var(--bg-card);
            display: flex;
            justify-content: center;
            align-items: center;
        }}

        /* ── Native Streamlit metric ── */
        [data-testid="stMetricValue"] {{
            color: var(--text-main) !important;
            font-weight: 700 !important;
            font-size: 2rem !important;
        }}
        [data-testid="stMetricLabel"] {{
            color: var(--text-muted) !important;
            font-weight: 500;
            font-size: 0.85rem !important;
        }}

        /* ── General overrides ── */
        .stMarkdown p, .stText {{ color: var(--text-main) !important; }}
        [data-testid="stDataFrame"] {{ border-radius: var(--radius) !important; border: 1px solid var(--border) !important; background: var(--bg-card); }}

        /* ── Streamlit default Header removal ── */
        header[data-testid="stHeader"] {{
            background-color: transparent !important;
        }}

        /* ── Streamlit Inputs (Selectbox, File Uploader, etc) for Dark Mode ── */
        .stSelectbox div[data-baseweb="select"] > div,
        .stTextInput div[data-baseweb="input"] > div {{
            background-color: var(--bg-card) !important;
            color: var(--text-main) !important;
            border-color: var(--border) !important;
        }}
        .stSelectbox div[data-baseweb="select"] span {{
            color: var(--text-main) !important;
        }}
        
        [data-testid="stFileUploader"] section {{
            background-color: var(--bg-card) !important;
            border: 1px dashed var(--border) !important;
        }}
        [data-testid="stFileUploader"] section * {{
            color: var(--text-main) !important;
        }}
        [data-testid="stFileUploadDropzone"] {{
            background-color: transparent !important;
        }}
    </style>
    """

    # Add extra overrides specifically for Dark Mode tables
    if is_dark:
        css += """
<style>
    /* Force Dataframe transparency/colors in Dark Mode */
    [data-testid="stDataFrame"] {
        background-color: var(--bg-card) !important;
    }
    [data-testid="stDataFrame"] > div {
        background-color: var(--bg-card) !important;
    }
    /* Glide Data Grid overrides */
    [data-testid="stDataFrame"] [data-testid="stTable"] {
        background-color: var(--bg-card) !important;
    }
    
    /* File Uploader button fix */
    [data-testid="stFileUploader"] button {
        background-color: var(--accent) !important;
        color: white !important;
    }
</style>
"""
    
    return css, bg_main, bg_card, sidebar, text_main, text_muted, border, accent

# Call the CSS injector immediately and get theme variables
css_str, bg_main, bg_card, sidebar, text_main, text_muted, border, accent = inject_custom_css()
st.markdown(css_str, unsafe_allow_html=True)

# Configuration
API_URL = "http://127.0.0.1:8000"
LOCAL_URL = "http://127.0.0.1:8000"

# Initialize session state
if 'lifts' not in st.session_state:
    st.session_state.lifts = {}
if 'last_result' not in st.session_state:
    st.session_state.last_result = None
if 'processing' not in st.session_state:
    st.session_state.processing = False

# Title with Logo
st.markdown(f"""
<div style="margin-bottom: 2rem; display: flex; justify-content: space-between; align-items: flex-end;">
    <div style="display: flex; align-items: center; gap: 20px;">
        <img src="{LOCAL_URL}/static/images/AlertOps logo.png" 
             style="width: 100px; height: 100px; border-radius: 8px; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1);">
        <div>
            <h1 class="main-header" style="font-size: 2.2rem; line-height: 1;">Lift Capacity Monitor</h1>
            <div style="color: var(--text-muted); font-size: 1rem; margin-top: 6px;">AI-powered real-time occupancy detection</div>
        </div>
    </div>
    <div style="margin-bottom: 0.5rem;">
        <span style="background: var(--bg-card); color: var(--success); padding: 8px 16px; border-radius: 6px; font-size: 0.85rem; font-weight: 600; border: 1px solid var(--border); box-shadow: 0 1px 2px rgba(0,0,0,0.05);">
            ● SYSTEM ONLINE
        </span>
    </div>
</div>
""", unsafe_allow_html=True)


def create_metric_card(label, value, delta=None, status_class=""):
    """
        Render a styled metric card in the Streamlit UI

        Query Parameters:
        - label: The descriptive text for the metric
        - value: The primary numerical or text value to display
        - delta: Optional secondary information or trend text (default: None)
        - status_class: CSS class for conditional styling (e.g., status-danger)
        """
    delta_html = f'<div style="font-size: 0.85rem; color: #94a3b8; margin-top: 0.5rem;">{delta}</div>' if delta else ''
    st.markdown(f"""
    <div class="metric-card {status_class}">
        <div class="metric-value">{value}</div>
        <div class="metric-label">{label}</div>
        {delta_html}
    </div>
    """, unsafe_allow_html=True)


# Sidebar Configuration
with st.sidebar:
    st.markdown("### Settings")
    st.markdown("---")

    # Add dark/light toggle
    is_dark_active = st.session_state.theme == "Dark"
    theme_toggle = st.toggle("Dark Mode", value=is_dark_active)
    new_theme = "Dark" if theme_toggle else "Light"
    
    if new_theme != st.session_state.theme:
        st.session_state.theme = new_theme
        st.rerun()

    st.markdown("---")
    st.markdown("### Configuration Panel")

    # Fetch lifts from API
    try:
        response = requests.get(f"{API_URL}/api/lift/list/", timeout=3)
        if response.status_code == 200:
            lifts_data = response.json().get('lifts', [])
            if lifts_data:
                st.session_state.lifts = {
                    f"{l['name']} (Max: {l['max_capacity']})": l['lift_id']
                    for l in lifts_data
                }
            else:
                st.session_state.lifts = {"Main Lift (Max: 5)": 1}
        else:
            st.session_state.lifts = {"Main Lift (Max: 5)": 1}
    except:
        st.session_state.lifts = {"Main Lift (Max: 5)": 1}

    # Lift selection
    if st.session_state.lifts:
        selected_lift_name = st.selectbox(
            "Select Lift:",
            list(st.session_state.lifts.keys())
        )
        lift_id = st.session_state.lifts[selected_lift_name]
    else:
        selected_lift_name = "Main Lift (Max: 5)"
        lift_id = 1

    st.markdown("---")

    st.markdown("---")

    # Instructions
    st.markdown("""
    <div class="info-box">
        <strong>System Instructions</strong><br><br>
        1. Select target lift<br>
        2. Choose Image or Video mode<br>
        3. Upload file<br>
        4. Process detection<br>
        5. Review capacity status
    </div>
    """, unsafe_allow_html=True)

    st.markdown("---")
    if st.button("Refresh Dashboard", use_container_width=True):
        st.rerun()

# Top KPI row in main content
try:
    response = requests.get(
        f"{API_URL}/api/lift/usage-stats/?lift_id={lift_id}&days=1",
        timeout=3
    )
    if response.status_code == 200:
        stats_data = response.json()
        if stats_data.get('stats'):
            today = stats_data['stats'][0].get('today')
            if today:
                kpi_col1, kpi_col2, kpi_col3, kpi_col4 = st.columns(4)
                with kpi_col1:
                    create_metric_card("Total Uses", today['usage_count'])
                with kpi_col2:
                    create_metric_card("Total People", today['total_people'])
                with kpi_col3:
                    create_metric_card("Overcrowding", today['overcrowding_count'])
                with kpi_col4:
                    create_metric_card("Peak Occupancy", today['max_people'])
except:
    st.info("Top Level KPIs loading...")

st.markdown("<br>", unsafe_allow_html=True)

# Main content tabs
tab1, tab2, tab3 = st.tabs(["DETECTION SYSTEM", "ANALYTICS DASHBOARD", "ACTIVITY LOG"])

with tab1:
    st.markdown('<h2 class="sub-header">Real-Time Detection System</h2>', unsafe_allow_html=True)

    col1, col2 = st.columns([3, 2])

    with col1:
        # Upload type selector
        upload_type = st.radio(
            "Upload Type",
            ["📷 Image", "🎥 Video"],
            horizontal=True,
            help="Choose whether to upload an image or video for analysis"
        )

        is_video = upload_type == "🎥 Video"

        if is_video:
            st.markdown("Upload Lift Video")
            uploaded_file = st.file_uploader(
                "Select video file",
                type=['mp4', 'avi', 'mov', 'mkv', 'webm'],
                help="Upload a lift interior video for frame-by-frame analysis",
                label_visibility="collapsed"
            )
        else:
            st.markdown("Upload Lift Image")
            uploaded_file = st.file_uploader(
                "Select image file",
                type=['jpg', 'jpeg', 'png'],
                help="Upload clear lift interior image",
                label_visibility="collapsed"
            )

        if uploaded_file is not None:
            # File info
            col_info1, col_info2, col_info3 = st.columns(3)
            with col_info1:
                st.markdown(f"**File:** {uploaded_file.name}")
            with col_info2:
                st.markdown(f"**Size:** {uploaded_file.size / 1024:.1f} KB")
            with col_info3:
                st.markdown(f"**Type:** {uploaded_file.type}")

            st.markdown("<br>", unsafe_allow_html=True)

            # Process button
            btn_label = "PROCESS VIDEO" if is_video else "PROCESS IMAGE"
            col_btn = st.columns([1, 2, 1])
            with col_btn[1]:
                if st.button(btn_label, type="primary", use_container_width=True):
                    st.session_state.processing = True

            if st.session_state.processing:
                progress_bar = st.progress(0)
                status_text = st.empty()

                try:
                    status_text.text(f"Uploading {'video' if is_video else 'image'}...")
                    progress_bar.progress(20)

                    uploaded_file.seek(0)
                    file_bytes = uploaded_file.read()

                    if len(file_bytes) == 0:
                        st.error("File is empty! Please select a valid file.")
                        st.session_state.processing = False
                    else:
                        status_text.text("Running AI detection...")
                        progress_bar.progress(50)

                        files = {
                            'file': (uploaded_file.name, file_bytes, uploaded_file.type or 'application/octet-stream')
                        }
                        data = {'lift_id': lift_id}

                        if is_video:
                            api_endpoint = f"{API_URL}/api/lift/process-video/"
                            data['sample_interval'] = '1.0'
                        else:
                            api_endpoint = f"{API_URL}/api/lift/process-image/"

                        response = requests.post(
                            api_endpoint,
                            files=files,
                            data=data,
                            timeout=300  # 5 mins for video processing
                        )

                        status_text.text("Analyzing results...")
                        progress_bar.progress(80)

                        if response.status_code == 200:
                            result = response.json()
                            st.session_state.last_result = result
                            progress_bar.progress(100)
                            status_text.text("Complete!")
                            time.sleep(0.5)
                            st.session_state.processing = False
                            st.rerun()
                        else:
                            st.error(f"API Error {response.status_code}")
                            try:
                                st.json(response.json())
                            except:
                                pass
                            st.session_state.processing = False

                except requests.exceptions.ConnectionError:
                    st.error("Cannot connect to API. Ensure server is running at http://127.0.0.1:8000")
                    st.session_state.processing = False
                except Exception as e:
                    st.error(f"Error: {str(e)}")
                    st.session_state.processing = False
        else:
            st.markdown(f"""
            <div class="upload-box">
                <div style="font-size: 3em; margin-bottom: 20px; color: #0066ff;">{'🎥' if is_video else '▲'}</div>
                <h3 style="color: #cbd5e1;">Upload Lift {'Video' if is_video else 'Image'}</h3>
                <p style="color: #94a3b8; margin-top: 10px;">
                    Drag and drop or click to browse
                </p>
                <p style="color: #64748b; font-size: 0.9em; margin-top: 15px;">
                    Supported: {'MP4, AVI, MOV, MKV, WEBM' if is_video else 'JPG, JPEG, PNG'}
                </p>
            </div>
            """, unsafe_allow_html=True)

    with col2:
        st.markdown("Detection Results")

        if st.session_state.last_result:
            result = st.session_state.last_result
            is_video_result = result.get('source_type') == 'VIDEO'

            if is_video_result:
                # Video results
                people_count = result['results']['peak_people_count']
                avg_people = result['results']['avg_people_count']
                max_capacity = result['lift']['max_capacity']
                is_overcrowded = result['results']['is_overcrowded']
                confidence = result['results']['confidence']
                warning_threshold = result['lift'].get('warning_threshold', max_capacity - 2)
                video_duration = result['results'].get('video_duration', 0)
                frames_analyzed = result['results'].get('frames_analyzed', 0)
            else:
                # Image results (existing logic)
                people_count = result['results']['people_count']
                max_capacity = result['lift']['max_capacity']
                is_overcrowded = result['results']['is_overcrowded']
                confidence = result['results']['confidence']
                warning_threshold = result['lift'].get('warning_threshold', max_capacity - 2)

            # Status banner
            if is_overcrowded:
                st.markdown("""
                <div class="status-box status-box-danger">
                    OVERLOADED<br>
                    <span style="font-size: 0.7em;">Immediate Action Required</span>
                </div>
                """, unsafe_allow_html=True)
            elif people_count >= warning_threshold:
                st.markdown("""
                <div class="status-box status-box-warning">
                    WARNING<br>
                    <span style="font-size: 0.7em;">Approaching Capacity</span>
                </div>
                """, unsafe_allow_html=True)
            else:
                st.markdown("""
                <div class="status-box status-box-ok">
                    NORMAL<br>
                    <span style="font-size: 0.7em;">Operating Normally</span>
                </div>
                """, unsafe_allow_html=True)

            # Metrics
            if is_video_result:
                col_m1, col_m2 = st.columns(2)
                with col_m1:
                    create_metric_card(
                        "Peak People",
                        people_count,
                        f"of {max_capacity} maximum",
                        "status-danger" if is_overcrowded else "status-ok"
                    )
                with col_m2:
                    create_metric_card(
                        "Avg People",
                        f"{avg_people}",
                        "across all frames"
                    )

                col_m3, col_m4 = st.columns(2)
                with col_m3:
                    create_metric_card(
                        "Confidence",
                        f"{confidence * 100:.1f}%",
                        "Average detection accuracy"
                    )
                with col_m4:
                    create_metric_card(
                        "Video Duration",
                        f"{video_duration}s",
                        f"{frames_analyzed} frames analyzed"
                    )
            else:
                col_m1, col_m2 = st.columns(2)
                with col_m1:
                    create_metric_card(
                        "People Count",
                        people_count,
                        f"of {max_capacity} maximum",
                        "status-danger" if is_overcrowded else "status-ok"
                    )
                with col_m2:
                    create_metric_card(
                        "Confidence",
                        f"{confidence * 100:.1f}%",
                        "Detection accuracy"
                    )

            # Occupancy gauge
            st.markdown("Capacity Analysis")
            occupancy_rate = min(people_count / max_capacity, 1.0) * 100

            fig = go.Figure(go.Indicator(
                mode="gauge+number+delta",
                value=occupancy_rate,
                domain={'x': [0, 1], 'y': [0, 1]},
                title={'text': "Peak Occupancy %" if is_video_result else "Occupancy %",
                       'font': {'size': 20, 'color': text_main}},
                delta={'reference': warning_threshold / max_capacity * 100,
                       'increasing': {'color': "#ef4444"}},
                gauge={
                    'axis': {'range': [None, 100], 'tickwidth': 1, 'tickcolor': text_main},
                    'bar': {'color': accent},
                    'bgcolor': "rgba(0,0,0,0)",
                    'borderwidth': 2,
                    'bordercolor': border,
                    'steps': [
                        {'range': [0, 60], 'color': 'rgba(16, 185, 129, 0.15)'},
                        {'range': [60, 80], 'color': 'rgba(245, 158, 11, 0.15)'},
                        {'range': [80, 100], 'color': 'rgba(239, 68, 68, 0.15)'}
                    ],
                    'threshold': {
                        'line': {'color': "#ef4444", 'width': 4},
                        'thickness': 0.75,
                        'value': 100
                    }
                }
            ))

            fig.update_layout(
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                font={'color': text_main, 'family': "Inter, Arial"},
                height=300
            )

            st.plotly_chart(fig, use_container_width=True)

            # Progress bar
            st.progress(
                min(people_count / max_capacity, 1.0),
                text=f"**{people_count}/{max_capacity} people** ({occupancy_rate:.0f}%)"
            )

            # Performance metrics
            col_p1, col_p2 = st.columns(2)
            with col_p1:
                st.metric("Processing Time", f"{result['results']['processing_time']:.2f}s")
            with col_p2:
                st.metric("Detection ID", f"#{result['detection_id']}")
        else:
            st.markdown("""
            <div class="info-box">
                <strong>Awaiting Analysis</strong><br><br>
                Upload an image or video and click the process button to begin detection.<br><br>
                <strong>Results will include:</strong><br>
                • People count (peak &amp; average for video)<br>
                • Occupancy level<br>
                • Detection confidence<br>
                • Annotated image / peak frame
            </div>
            """, unsafe_allow_html=True)

    # Show processed image / peak frame
    if st.session_state.last_result:
        result = st.session_state.last_result
        is_video_result = result.get('source_type') == 'VIDEO'

        # Get the image URL (peak_frame for video, processed for image)
        if is_video_result:
            processed_url_path = result.get('images', {}).get('peak_frame')
            section_title = "Peak Frame (Most Crowded Moment)"
        else:
            processed_url_path = result.get('images', {}).get('processed')
            section_title = "Processed Detection Image"

        if processed_url_path:
            st.markdown(f'<h2 class="sub-header">{section_title}</h2>', unsafe_allow_html=True)
            full_url = f"{API_URL}{processed_url_path}"
            try:
                response_img = requests.get(full_url, timeout=5)
                if response_img.status_code == 200:
                    st.markdown('<div class="image-container">', unsafe_allow_html=True)
                    img = Image.open(io.BytesIO(response_img.content))
                    st.image(img, use_column_width=True)
                    st.markdown('</div>', unsafe_allow_html=True)
            except:
                st.info("Processed image not available")

        # Video-specific: Annotated video playback
        if is_video_result:
            annotated_video_url = result.get('images', {}).get('annotated_video')
            if annotated_video_url:
                st.markdown('<h2 class="sub-header">Annotated Video (Detection Playback)</h2>', unsafe_allow_html=True)
                video_full_url = f"{API_URL}{annotated_video_url}"
                try:
                    # Use the URL directly for st.video() - better for browser compatibility
                    st.markdown('<div class="image-container">', unsafe_allow_html=True)
                    st.video(video_full_url)
                    st.markdown('</div>', unsafe_allow_html=True)
                    st.caption("Video with AI detection bounding boxes drawn on every frame")
                except Exception as e:
                    st.info(f"Could not load annotated video: {e}")

        # Video-specific: Frame-by-frame timeline chart
        if is_video_result and result.get('frame_results'):
            st.markdown('<h2 class="sub-header">Frame-by-Frame Analysis</h2>', unsafe_allow_html=True)

            frame_data = result['frame_results']
            df_frames = pd.DataFrame(frame_data)

            if len(df_frames) > 1:
                max_capacity = result['lift']['max_capacity']

                fig_timeline = go.Figure()

                fig_timeline.add_trace(go.Scatter(
                    x=df_frames['timestamp_sec'],
                    y=df_frames['people_count'],
                    mode='lines+markers',
                    name='People Count',
                    line=dict(color='#0066ff', width=3),
                    marker=dict(size=6, color='#00ccff'),
                    hovertemplate='<b>Time</b>: %{x}s<br><b>People</b>: %{y}<extra></extra>'
                ))

                # Add capacity line
                fig_timeline.add_hline(
                    y=max_capacity,
                    line_dash="dash",
                    line_color="#ef4444",
                    annotation_text=f"Max Capacity: {max_capacity}"
                )

                fig_timeline.update_layout(
                    title="People Count Over Time",
                    xaxis_title="Time (seconds)",
                    yaxis_title="People Count",
                    template="plotly_white",
                    height=350,
                    plot_bgcolor='rgba(0,0,0,0)',
                    paper_bgcolor='rgba(0,0,0,0)',
                    font=dict(color=text_main),
                    title_font=dict(color=text_main, size=16),
                    margin=dict(l=40, r=40, t=60, b=40)
                )

                fig_timeline.update_xaxes(gridcolor=border, linecolor=border, title_font=dict(color=text_main), tickfont=dict(color=text_main))
                fig_timeline.update_yaxes(gridcolor=border, linecolor=border, title_font=dict(color=text_main), tickfont=dict(color=text_main))

                st.plotly_chart(fig_timeline, use_container_width=True)

                # Summary stats under the chart
                col_s1, col_s2, col_s3, col_s4 = st.columns(4)
                with col_s1:
                    st.metric("Peak Count", int(df_frames['people_count'].max()))
                with col_s2:
                    st.metric("Avg Count", f"{df_frames['people_count'].mean():.1f}")
                with col_s3:
                    st.metric("Min Count", int(df_frames['people_count'].min()))
                with col_s4:
                    overcrowded_frames = len(df_frames[df_frames['people_count'] > max_capacity])
                    st.metric("Overcrowded Frames", f"{overcrowded_frames}/{len(df_frames)}")
            else:
                st.info("Not enough frames for timeline analysis")

with tab2:
    st.markdown('<h2 class="sub-header">Usage Analytics Dashboard</h2>', unsafe_allow_html=True)

    # Date range selector
    col_date = st.columns([3, 1])
    with col_date[0]:
        days = st.selectbox("Analysis Period", [1, 7, 14, 30], index=1, format_func=lambda x: f"Last {x} days")

    try:
        response = requests.get(
            f"{API_URL}/api/lift/usage-stats/?lift_id={lift_id}&days={days}",
            timeout=5
        )

        if response.status_code == 200:
            stats_data = response.json()

            if stats_data.get('stats'):
                lift_stats = stats_data['stats'][0]
                period_stats = lift_stats.get('period_stats', {})

                # Summary KPIs
                col1, col2, col3, col4 = st.columns(4)

                with col1:
                    create_metric_card(
                        "Total Uses",
                        period_stats.get('total_uses', 0),
                        f"in {days} days"
                    )

                with col2:
                    create_metric_card(
                        "Total People",
                        period_stats.get('total_people', 0),
                        f"avg {period_stats.get('avg_people_per_use', 0):.1f}/use"
                    )

                with col3:
                    create_metric_card(
                        "Overcrowding Events",
                        period_stats.get('total_overcrowding', 0),
                        f"{period_stats.get('overcrowding_rate', 0):.1f}% rate",
                        "status-danger" if period_stats.get('total_overcrowding', 0) > 0 else "status-ok"
                    )

                with col4:
                    create_metric_card(
                        "Avg Daily Uses",
                        f"{period_stats.get('avg_uses_per_day', 0):.1f}",
                        "per day"
                    )

                # Today's stats
                st.markdown('<h3 class="sub-header" style="font-size: 1.4rem;">Today\'s Overview</h3>',
                            unsafe_allow_html=True)

                today_stats = lift_stats.get('today')
                if today_stats:
                    col_today1, col_today2, col_today3, col_today4 = st.columns(4)
                    with col_today1:
                        st.metric("Uses Today", today_stats.get('usage_count', 0))
                    with col_today2:
                        st.metric("People Today", today_stats.get('total_people', 0))
                    with col_today3:
                        st.metric("Overcrowding", today_stats.get('overcrowding_count', 0))
                    with col_today4:
                        st.metric("Peak Today", today_stats.get('max_people', 0))

                # Charts
                st.markdown('<h3 class="sub-header" style="font-size: 1.4rem;">Detection Trends</h3>',
                            unsafe_allow_html=True)

                recent = lift_stats.get('recent_detections', [])

                if recent and len(recent) > 1:
                    # Prepare data for charts with PROPER TIME FORMATTING
                    df_recent = pd.DataFrame(recent)

                    # Convert timestamp to datetime with proper timezone handling
                    df_recent['timestamp'] = pd.to_datetime(df_recent['timestamp'], utc=True)

                    # Convert to local timezone (Asia/Kathmandu)
                    local_tz = pytz.timezone(YOUR_TIMEZONE)
                    df_recent['local_time'] = df_recent['timestamp'].dt.tz_convert(local_tz).dt.tz_localize(None)

                    # Extract hour for grouping
                    df_recent['hour'] = df_recent['local_time'].dt.hour

                    # Format for display
                    df_recent['display_time'] = df_recent['local_time'].dt.strftime('%H:%M')
                    df_recent['display_date'] = df_recent['local_time'].dt.strftime('%Y-%m-%d %H:%M')

                    col_chart1, col_chart2 = st.columns(2)

                    with col_chart1:
                        # People count timeline
                        fig_timeline = go.Figure()

                        fig_timeline.add_trace(go.Scatter(
                            x=df_recent['local_time'],
                            y=df_recent['people_count'],
                            mode='lines+markers',
                            name='People Count',
                            line=dict(color='#0066ff', width=3),
                            marker=dict(size=8, color='#00ccff'),
                            hovertemplate='<b>Time</b>: %{x|%H:%M}<br><b>Date</b>: %{x|%Y-%m-%d}<br><b>Count</b>: %{y}<extra></extra>'
                        ))

                        # Add capacity line
                        max_capacity_val = today_stats.get('max_people', 8) if today_stats else 8
                        fig_timeline.add_hline(
                            y=max_capacity_val,
                            line_dash="dash",
                            line_color="#ef4444",
                            annotation_text=f"Max Capacity: {max_capacity_val}"
                        )

                        fig_timeline.update_layout(
                            title="People Count Timeline",
                            xaxis_title="Time",
                            yaxis_title="People Count",
                            template="plotly_white",
                            height=300,
                            plot_bgcolor='rgba(0,0,0,0)',
                            paper_bgcolor='rgba(0,0,0,0)',
                            font=dict(color='#2b2b2b'),
                            title_font=dict(color='#2b2b2b', size=16),
                            margin=dict(l=40, r=40, t=60, b=40),
                            xaxis=dict(
                                tickformat='%H:%M\n%b %d',
                                tickangle=45,
                                gridcolor='#e5e7eb'
                            ),
                            yaxis=dict(gridcolor='#e5e7eb')
                        )

                        st.plotly_chart(fig_timeline, use_container_width=True)

                    with col_chart2:
                        # Average People by Hour
                        if len(df_recent['hour'].unique()) > 1:
                            # Group by hour and calculate statistics
                            hourly_stats = df_recent.groupby('hour').agg({
                                'people_count': ['mean', 'count', 'max', 'min']
                            }).round(1)
                            hourly_stats.columns = ['avg_people', 'count', 'max_people', 'min_people']
                            hourly_stats = hourly_stats.reset_index()

                            # Create hour labels (e.g., "08:00", "14:00")
                            hourly_stats['hour_label'] = hourly_stats['hour'].apply(lambda x: f"{x:02d}:00")

                            # Create the bar chart
                            fig_hourly = go.Figure()

                            fig_hourly.add_trace(go.Bar(
                                x=hourly_stats['hour_label'],
                                y=hourly_stats['avg_people'],
                                marker_color='#0066ff',
                                opacity=0.8,
                                hovertemplate='<b>Hour</b>: %{x}<br><b>Avg People</b>: %{y:.1f}<br><b>Samples</b>: ' + \
                                              hourly_stats['count'].astype(str) + '<extra></extra>',
                                name='Average People'
                            ))

                            fig_hourly.update_layout(
                                title="Average People by Hour",
                                xaxis_title="Hour of Day (24h)",
                                yaxis_title="Average People",
                                template="plotly_white",
                                height=300,
                                plot_bgcolor='rgba(0,0,0,0)',
                                paper_bgcolor='rgba(0,0,0,0)',
                                font=dict(color='#0f172a'),
                                title_font=dict(color='#0f172a')
                            )

                            st.plotly_chart(fig_hourly, use_container_width=True)

                            # Show hourly statistics
                            st.markdown("Hourly Statistics:**")
                            col_h1, col_h2, col_h3 = st.columns(3)
                            with col_h1:
                                peak_hour = hourly_stats.loc[hourly_stats['avg_people'].idxmax()]
                                st.metric("Peak Hour", f"{peak_hour['hour_label']}")
                            with col_h2:
                                st.metric("Peak Avg", f"{peak_hour['avg_people']:.1f}")
                            with col_h3:
                                st.metric("Data Points", f"{len(df_recent)}")
                        else:
                            st.info("Not enough hourly data for analysis")

                # Recent detections table
                st.markdown('<h3 class="sub-header" style="font-size: 1.4rem;">Recent Detections</h3>',
                            unsafe_allow_html=True)

                if recent:
                    local_tz = pytz.timezone(YOUR_TIMEZONE)
                    for detection in recent[:5]:
                        status_color = detection['status_color']
                        status_icon = "OVERLOADED" if detection['is_overcrowded'] else "NORMAL"
                        status_class = "status-danger" if detection['is_overcrowded'] else "status-ok"

                        # Parse and format timestamp correctly
                        try:
                            # Parse timestamp with timezone
                            det_time = pd.to_datetime(detection['timestamp'], utc=True)
                            # Convert to local time
                            local_time = det_time.tz_convert(local_tz).tz_localize(None)
                            formatted_time = local_time.strftime('%I:%M %p')
                            formatted_date = local_time.strftime('%b %d')
                        except:
                            formatted_time = "Unknown"
                            formatted_date = ""

                        st.markdown(f"""
                        <div class="metric-card {status_class}">
                            <div style="display: flex; justify-content: space-between; align-items: center;">
                                <div>
                                    <strong style="font-size: 1.2em; color: #0055dd;">{detection['people_count']} people</strong>
                                    <span style="color: #64748b; margin-left: 15px;">
                                        {formatted_time} {formatted_date}
                                    </span>
                                </div>
                                <div>
                                    <span style="color: {status_color}; font-weight: bold; font-size: 1.1em;">
                                        {status_icon}
                                    </span>
                                    <span style="color: #94a3b8; margin-left: 10px;">
                                        {detection['confidence']:.1f}% conf
                                    </span>
                                </div>
                            </div>
                        </div>
                        """, unsafe_allow_html=True)
                else:
                    st.info("No recent detections available")
            else:
                st.info("No analytics data available yet")
    except Exception as e:
        st.error(f"Unable to load analytics data: {str(e)}")

with tab3:
    st.markdown('<h2 class="sub-header">Activity Log</h2>', unsafe_allow_html=True)

    try:
        response = requests.get(
            f"{API_URL}/api/lift/usage-stats/?lift_id={lift_id}&days=7",
            timeout=5
        )

        if response.status_code == 200:
            stats_data = response.json()

            if stats_data.get('stats'):
                recent_detections = stats_data['stats'][0].get('recent_detections', [])

                if recent_detections:
                    # Create DataFrame with proper time formatting
                    local_tz = pytz.timezone(YOUR_TIMEZONE)
                    df_data = []
                    for det in recent_detections:
                        try:
                            # Parse timestamp with timezone handling
                            det_time = pd.to_datetime(det['timestamp'], utc=True)
                            # Convert to local time (Asia/Kathmandu)
                            local_time = det_time.tz_convert(local_tz).tz_localize(None)
                            date_str = local_time.strftime('%Y-%m-%d')
                            time_str = local_time.strftime('%I:%M %p')
                        except:
                            date_str = "Unknown"
                            time_str = "Unknown"

                        df_data.append({
                            'Date': date_str,
                            'Time': time_str,
                            'People': det['people_count'],
                            'Status': 'OVERLOADED' if det['is_overcrowded'] else 'NORMAL',
                            'Confidence': f"{det['confidence']:.1f}%",
                            'ID': f"#{det['detection_id']}"
                        })

                    df = pd.DataFrame(df_data)


                    # Style the DataFrame
                    def color_status(val):
                        if 'OVERLOADED' in val:
                            return 'color: #ef4444; font-weight: 600;'
                        elif 'NORMAL' in val:
                            return 'color: #10b981; font-weight: 600;'
                        return ''

                    styled_df = df.style.map(color_status, subset=['Status'])

                    st.dataframe(styled_df, use_container_width=True, height=400, hide_index=True)

                    # Add some statistics
                    st.markdown('<h3 class="sub-header" style="font-size: 1.4rem;">Activity Statistics</h3>',
                                unsafe_allow_html=True)

                    col_stat1, col_stat2, col_stat3 = st.columns(3)
                    with col_stat1:
                        st.metric("Total Detections", len(df))
                    with col_stat2:
                        overloaded_count = len(df[df['Status'] == 'OVERLOADED'])
                        st.metric("Overloaded Events", overloaded_count)
                    with col_stat3:
                        avg_people = df['People'].mean()
                        st.metric("Avg People", f"{avg_people:.1f}")
                else:
                    st.info("No activity recorded yet")
    except Exception as e:
        st.error(f"Unable to load activity log: {str(e)}")

# Footer
st.markdown("---")
col1, col2, col3 = st.columns([1, 2, 1])

with col1:
    st.markdown(
        f"<div style='color: #94a3b8;'><strong>Last Updated:</strong> {datetime.now().strftime('%H:%M:%S')}</div>",
        unsafe_allow_html=True)

with col2:
    st.markdown(
        "<div style='color: #94a3b8; text-align: center;'><strong>Lift Capacity Monitoring System</strong> - AI-powered occupancy detection</div>",
        unsafe_allow_html=True)

with col3:
    if st.button("Refresh Data", use_container_width=True):
        st.rerun()