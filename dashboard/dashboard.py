import streamlit as st
import requests
import pandas as pd
import time
import os
from datetime import datetime

# Move page config to the very top, before any other st commands
st.set_page_config(
    page_title="AI Surveillance System Dashboard (Weapon And Overcrowding)",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize theme state
if 'theme' not in st.session_state:
    st.session_state.theme = 'Dark'

def inject_custom_css():
    is_lavender = st.session_state.theme == 'Lavender'
    
    if is_lavender:
        bg_main = "#EEF2FF"
        bg_card = "#F8F7FF"
        sidebar = "#F0F4FF"
        text_main = "#1E1B4B"
        text_muted = "#6B7280"
        border = "#C7D2FE"
        accent = "#4F46E5"
        
        css = f"""
        <style>
            .stApp {{
                background-color: {bg_main} !important;
                color: {text_main} !important;
            }}
            [data-testid="stAppViewContainer"] {{
                background-color: {bg_main} !important;
            }}
            h1, h2, h3 {{
                color: {text_main} !important;
                background: none !important;
                -webkit-text-fill-color: initial !important;
                margin-bottom: 1rem;
            }}
            .stAlert {{
                border-radius: 12px;
                border: 1px solid {border};
                font-weight: bold;
            }}
            div[data-testid="stAlert"]:has(div:contains("")) {{
                background: rgba(163, 0, 0, 0.1) !important;
                border-color: #ff3333 !important;
                color: #ff3333 !important;
            }}
            .stButton > button {{
                background: {accent} !important;
                color: white !important;
                border: none !important;
                border-radius: 12px;
                font-weight: 700;
                text-transform: uppercase;
                letter-spacing: 1px;
                transition: all 0.3s ease;
                box-shadow: 0 4px 6px rgba(79, 70, 229, 0.3) !important;
            }}
            .stButton > button:hover {{
                transform: translateY(-2px);
                box-shadow: 0 6px 12px rgba(79, 70, 229, 0.4) !important;
            }}
            .stDataFrame, [data-testid="stDataFrame"], [data-testid="stDataFrame"] > div {{
                background-color: {bg_card} !important;
                border: 1px solid {border} !important;
                border-radius: 12px !important;
                color: {text_main} !important;
            }}
            .stDataFrame th, [data-testid="stDataFrame"] th {{
                background-color: {sidebar} !important;
                color: {text_main} !important;
                font-weight: 700 !important;
            }}
            .stDataFrame td, [data-testid="stDataFrame"] td {{
                background-color: {bg_card} !important;
                color: {text_main} !important;
            }}
            .stMarkdown img {{
                border-radius: 12px;
                border: 2px solid {border} !important;
                box-shadow: 0 4px 15px rgba(0, 0, 0, 0.1) !important;
            }}
            [data-testid="stSidebar"] {{
                background-color: {sidebar} !important;
                border-right: 1px solid {border} !important;
            }}
            [data-testid="stSidebar"] * {{
                color: {text_main} !important;
            }}
            [data-testid="stSidebar"] h1,
            [data-testid="stSidebar"] h2,
            [data-testid="stSidebar"] h3 {{
                color: {text_main} !important;
            }}
            [data-testid="stMetricValue"] {{
                color: {accent} !important;
                font-size: 2rem !important;
                font-weight: 700 !important;
            }}
            [data-testid="stMetricLabel"] {{
                color: {text_muted} !important;
                text-transform: uppercase !important;
                letter-spacing: 1px !important;
            }}
            .stTabs [data-baseweb="tab-list"] {{
                background-color: {bg_card} !important;
                border-radius: 12px !important;
                padding: 5px !important;
                border: 1px solid {border} !important;
            }}
            .stTabs [data-baseweb="tab"] {{
                background: transparent !important;
                color: {text_muted} !important;
                border-radius: 8px !important;
            }}
            .stTabs [aria-selected="true"] {{
                background-color: {accent} !important;
                color: white !important;
            }}
            .stText, .stMarkdown p, .stSubheader {{
                color: {text_main} !important;
            }}
            .stProgress > div > div {{
                background-color: {accent} !important;
            }}
            .streamlit-expanderHeader {{
                background-color: {sidebar} !important;
                border: 1px solid {border} !important;
                border-radius: 8px !important;
                color: {text_main} !important;
            }}
            a button {{
                background: {accent} !important;
                color: white !important;
                border: none !important;
                padding: 12px 24px !important;
                border-radius: 12px !important;
                font-size: 16px !important;
                font-weight: 600 !important;
                cursor: pointer !important;
                width: 100% !important;
                transition: all 0.3s ease !important;
                text-decoration: none !important;
            }}
            a button:hover {{
                transform: translateY(-3px) !important;
                box-shadow: 0 10px 20px rgba(79, 70, 229, 0.4) !important;
            }}
            /* Header link reset */
            h1 > a, h2 > a, h3 > a {{
                color: {text_main} !important;
            }}
            /* Header transparent */
            header[data-testid="stHeader"] {{
                background-color: transparent !important;
            }}
            /* Custom Event Log Table */
            .custom-table {{
                width: 100%;
                border-collapse: collapse;
                font-size: 0.95rem;
            }}
            .custom-table th {{
                background-color: {sidebar} !important;
                color: {text_main} !important;
                font-weight: 700;
                padding: 12px;
                text-align: left;
                position: sticky;
                top: 0;
                z-index: 1;
            }}
            .custom-table td {{
                background-color: {bg_card} !important;
                color: {text_main} !important;
                padding: 12px;
                border-bottom: 1px solid {border};
            }}
            .custom-progress-bg {{
                background: rgba(107, 114, 128, 0.2);
                border-radius: 4px;
                width: 100%;
            }}
            .custom-progress-fill {{
                background: {accent} !important;
                height: 8px;
                border-radius: 4px;
            }}
            .custom-link {{
                color: {accent} !important;
                text-decoration: none;
                font-weight: 600;
            }}
            .custom-link:hover {{
                text-decoration: underline;
            }}
            .table-container {{
                max-height: 600px;
                overflow-y: auto;
                border-radius: 12px;
                border: 1px solid {border};
            }}
        </style>
        """
    else:
        # Original dark theme css
        css = """
        <style>
            /* Main Dark Theme */
            .stApp {
                background: #0a0e27;
                color: #ffffff;
            }

            /* Headers */
            h1, h2, h3 {
                background: linear-gradient(90deg, #0066ff, #00ccff);
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
                background-clip: text;
                margin-bottom: 1rem;
            }

            /* Status Banners */
            .stAlert {
                border-radius: 12px;
                border: 1px solid;
                font-weight: bold;
            }

            /* Alert status (weapon detected) */
            div[data-testid="stAlert"]:has(div:contains("")) {
                background: rgba(163, 0, 0, 0.2) !important;
                border-color: #ff3333 !important;
                color: #ff9999 !important;
            }

            /* OK/Idle status */
            div[data-testid="stAlert"]:has(div:contains("")) {
                background: rgba(0, 102, 255, 0.2) !important;
                border-color: #0066ff !important;
                color: #99ccff !important;
            }

            /* Buttons */
            .stButton > button {
                background: linear-gradient(135deg, #0066ff, #00ccff);
                color: white !important;
                border: none !important;
                border-radius: 12px;
                font-weight: 700;
                text-transform: uppercase;
                letter-spacing: 1px;
                transition: all 0.3s ease;
                box-shadow: 0 10px 30px rgba(0, 102, 255, 0.3);
            }

            .stButton > button:hover {
                transform: translateY(-3px);
                box-shadow: 0 15px 40px rgba(0, 102, 255, 0.4);
            }

            /* Custom HTML Table */
            .table-container {
                max-height: 600px;
                overflow-y: auto;
                border-radius: 12px;
                border: 1px solid rgba(0, 102, 255, 0.3);
            }
            .custom-table {
                width: 100%;
                border-collapse: collapse;
                font-size: 0.95rem;
            }
            .custom-table th {
                background-color: rgba(0, 102, 255, 0.3) !important;
                color: #00ccff !important;
                font-weight: 700;
                padding: 12px;
                text-align: left;
                position: sticky;
                top: 0;
                z-index: 1;
            }
            .custom-table td {
                background-color: rgba(15, 23, 42, 0.6) !important;
                color: #cbd5e1 !important;
                padding: 12px;
                border-bottom: 1px solid rgba(0, 102, 255, 0.3);
            }
            .custom-progress-bg {
                background: rgba(255, 255, 255, 0.1);
                border-radius: 4px;
                width: 100%;
            }
            .custom-progress-fill {
                background: linear-gradient(90deg, #0066ff, #00ccff) !important;
                height: 8px;
                border-radius: 4px;
            }
            .custom-link {
                color: #00ccff !important;
                text-decoration: none;
                font-weight: 600;
            }
            .custom-link:hover {
                text-decoration: underline;
            }

            /* Video Feed Container */
            .stMarkdown img {
                border-radius: 12px;
                border: 2px solid rgba(0, 102, 255, 0.3);
                box-shadow: 0 0 40px rgba(0, 102, 255, 0.2);
            }

            /* Sidebar */
            [data-testid="stSidebar"] {
                background: linear-gradient(180deg, #0a0e27 0%, #050916 100%);
                border-right: 1px solid rgba(0, 102, 255, 0.3);
            }

            /* Metrics */
            [data-testid="stMetricValue"] {
                color: #00ccff !important;
                font-size: 2rem !important;
                font-weight: 700;
            }

            [data-testid="stMetricLabel"] {
                color: #94a3b8 !important;
                text-transform: uppercase;
                letter-spacing: 1px;
            }

            /* Tabs */
            .stTabs [data-baseweb="tab-list"] {
                background: rgba(15, 23, 42, 0.8);
                border-radius: 12px;
                padding: 5px;
            }

            .stTabs [data-baseweb="tab"] {
                background: transparent;
                color: #94a3b8;
                border-radius: 8px;
            }

            .stTabs [aria-selected="true"] {
                background: linear-gradient(135deg, #0066ff, #00ccff) !important;
                color: white !important;
            }

            /* Grid Overlay Effect */
            .stApp::before {
                content: '';
                position: fixed;
                top: 0;
                left: 0;
                right: 0;
                bottom: 0;
                background-image: 
                    linear-gradient(rgba(0, 102, 255, 0.03) 1px, transparent 1px),
                    linear-gradient(90deg, rgba(0, 102, 255, 0.03) 1px, transparent 1px);
                background-size: 50px 50px;
                pointer-events: none;
                z-index: -1;
            }

            /* Animated Background */
            .stApp::after {
                content: '';
                position: fixed;
                top: 0;
                left: 0;
                right: 0;
                bottom: 0;
                background: 
                    radial-gradient(circle at 20% 50%, rgba(0, 102, 255, 0.1) 0%, transparent 50%),
                    radial-gradient(circle at 80% 80%, rgba(255, 0, 102, 0.1) 0%, transparent 50%),
                    radial-gradient(circle at 40% 20%, rgba(102, 255, 102, 0.05) 0%, transparent 50%);
                animation: bgPulse 10s ease-in-out infinite;
                pointer-events: none;
                z-index: -2;
            }

            @keyframes bgPulse {
                0%, 100% { opacity: 0.5; }
                50% { opacity: 1; }
            }

            /* Text Elements */
            .stText, .stMarkdown, .stSubheader {
                color: #cbd5e1;
            }

            /* Progress Bars */
            .stProgress > div > div {
                background: linear-gradient(90deg, #0066ff, #00ccff);
            }

            /* Expanders */
            .streamlit-expanderHeader {
                background: rgba(0, 102, 255, 0.1);
                border: 1px solid rgba(0, 102, 255, 0.3);
                border-radius: 8px;
                color: #00ccff;
            }

            /* Analytics Button */
            a button {
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                border: none;
                padding: 12px 24px;
                border-radius: 12px;
                font-size: 16px;
                font-weight: 600;
                cursor: pointer;
                width: 100%;
                transition: all 0.3s ease;
                text-decoration: none !important;
            }

            a button:hover {
                transform: translateY(-3px);
                box-shadow: 0 15px 30px rgba(102, 126, 234, 0.4);
            }

            /* Header transparent */
            header[data-testid="stHeader"] {
                background-color: transparent !important;
            }
        </style>
        """
    return css

st.markdown(inject_custom_css(), unsafe_allow_html=True)

# Local Django server URL for dashboard API calls
LOCAL_URL = "http://127.0.0.1:8000"
# Endpoint for video feed
VIDEO_FEED_URL = f"{LOCAL_URL}/video_feed/"
# Endpoint for event logs (e.g., /api/logs/)
LOGS_URL = f"{LOCAL_URL}/api/logs/"
#Endpoint for the latest status (e.g., /api/latest_status/)
STATUS_API_URL = f"{LOCAL_URL}/api/latest_status/"

# Data Fetching Functions
def fetch_system_status():
    """
        Fetches the latest alert status from the Django backend API

        Query Parameters:
        - None: Request is sent to STATUS_API_URL
        - timeout: Connection limit set to 1 second
        """
    try:
        response = requests.get(STATUS_API_URL, timeout=1) # Use a short timeout
        if response.status_code == 200:
            return response.json()
        else:
            return {'status_level': 'ERROR', 'message': f'Django Status API returned {response.status_code}'}
    except requests.exceptions.ConnectionError:
        return {'status_level': 'ERROR', 'message': 'Cannot connect to Django API. Server may be down.'}
    except requests.exceptions.Timeout:
        return {'status_level': 'ERROR', 'message': 'Django Status API connection timed out.'}
    except Exception as e:
        return {'status_level': 'ERROR', 'message': f'An unknown error occurred: {e}'}

def fetch_event_logs():
    """
        Fetches the latest events from the Django backend

        Query Parameters:
        - None: Request is sent to LOGS_URL
        - Returns: Sorted pandas DataFrame of event history
        """
    try:
        response = requests.get(LOGS_URL, timeout=3)  # Prevent indefinite blocking
        if response.status_code == 200:
            data = response.json()

            # If the response is an empty list, return an empty DataFrame immediately
            if not data:
                return pd.DataFrame()

            df = pd.DataFrame(data)

            # Format datetime
            df['timestamp'] = pd.to_datetime(df['timestamp']).dt.strftime('%Y-%m-%d %H:%M:%S')

            # Construct display_url locally from snapshot_path for dashboard display
            if 'snapshot_path' in df.columns:
                 df['display_url'] = df['snapshot_path'].apply(
                     lambda p: f"{LOCAL_URL}/snapshots/{p}" if pd.notna(p) and p else None
                 )
            else:
                 # If snapshot_path is not available, set display_url to None
                 df['display_url'] = None

            return df.sort_values(by='timestamp', ascending=False) # Ensure newest is first

        else:
            st.error(f"Failed to fetch logs. Django Log API returned status code: {response.status_code}")
            return pd.DataFrame()
    except requests.exceptions.ConnectionError:
        # st.error("Cannot connect to Django API for logs.")
        return pd.DataFrame()
    except Exception as e:
        # Catch unexpected errors during pandas processing
        st.error(f"Error processing log data in Streamlit: {e}")
        return pd.DataFrame()


# Dashboard Layout

# Navigation Header
col_title, col_nav = st.columns([3, 1])
with col_title:
    st.markdown(f"""
    <div style="display: flex; align-items: center; gap: 15px;">
        <img src="{LOCAL_URL}/static/images/AlertOps logo.png" 
             style="width: 130px; height: 130px; border-radius: 10px; 
                    box-shadow: 0 0 15px rgba(0, 102, 255, 0.3); 
                    border: 1px solid rgba(0, 102, 255, 0.2);">
        <h1 style="margin: 0; 
                   font-size: 2.2rem;
                   font-weight: 700;
                   background: linear-gradient(90deg, #0066ff, #00ccff);
                   -webkit-background-clip: text;
                   -webkit-text-fill-color: transparent;
                   background-clip: text;">
            Real-Time AI Surveillance Dashboard
        </h1>
    </div>
    """, unsafe_allow_html=True)

with col_nav:
    is_lavender_active = st.session_state.theme == "Lavender"
    theme_toggle = st.toggle("Lavender Theme", value=is_lavender_active)
    new_theme = "Lavender" if theme_toggle else "Dark"

    if new_theme != st.session_state.theme:
        st.session_state.theme = new_theme
        st.rerun()

    st.markdown("<br>", unsafe_allow_html=True)  # Add some spacing
    # Button to navigate to analytics dashboard
    st.markdown("""
    <a href="http://127.0.0.1:8502" target="_self" style="text-decoration: none;">
        <button style="background: linear-gradient(135deg, #0066ff 0%, #00ccff 100%);
                       color: white;
                       border: none;
                       padding: 10px 20px;
                       border-radius: 10px;
                       font-size: 16px;
                       font-weight: 600;
                       cursor: pointer;
                       width: 100%;
                       transition: transform 0.2s;">
            View Analytics Dashboard
        </button>
    </a>
    """, unsafe_allow_html=True)

# Status Banner Placeholder
status_placeholder = st.empty()

# Create two columns for layout
col1, col2 = st.columns([2, 1])

# Column 1: Live Video Feed
with col1:
    st.header("Live Feed")

    # MJPEG stream via a plain <img> tag.
    # The camera singleton in Django means reconnects no longer open a new
    # capture device, so img is safe and avoids the iframe CSP restrictions
    # that caused "refused to connect" in the browser.
    st.markdown(
        f'<img src="{VIDEO_FEED_URL}" width="100%"'
        f' style="border-radius:10px; border:2px solid rgba(0,102,255,0.3);'
        f' box-shadow:0 0 40px rgba(0,102,255,0.2);">',
        unsafe_allow_html=True
    )

# Column 2: Event Logs
with col2:
    st.header("Recent Event Logs")

    # Event Log Table Placeholder
    log_container = st.empty()


# Main Polling Loop — rerun-based (non-blocking)
# The old `while True` + time.sleep() pattern blocked the entire Streamlit
# render thread, preventing UI interactions and causing video stream lag.
# We now store the last-polled timestamp in session_state and use st.rerun()
# so Streamlit can process events between each poll cycle.

if 'monitoring_active' not in st.session_state:
    st.session_state['monitoring_active'] = False

if 'last_poll_time' not in st.session_state:
    st.session_state['last_poll_time'] = 0

if st.button("Start/Restart System Status Monitoring"):
    st.session_state['monitoring_active'] = True
    st.session_state['last_poll_time'] = 0  # Force immediate first poll

POLL_INTERVAL = 2  # seconds between status + log refreshes

if st.session_state['monitoring_active']:
    now = time.time()
    elapsed = now - st.session_state['last_poll_time']

    if elapsed >= POLL_INTERVAL:
        # --- Fetch and display system status ---
        status_data = fetch_system_status()

        with status_placeholder.container():
            if status_data.get('status_level') == 'ALERT':
                st.markdown(f"""
<div style='background-color: #A30000; color: white; padding: 25px; border-radius: 10px; font-size: 24px; font-weight: bold; text-align: center;'>
    {status_data['message']}
</div>
""", unsafe_allow_html=True)
            elif status_data.get('status_level') in ['OK', 'IDLE']:
                st.markdown(f"""
<div style='background-color: #2D4059; color: white; padding: 25px; border-radius: 10px; font-size: 20px; font-weight: bold; text-align: center;'>
    {status_data['message']}
</div>
""", unsafe_allow_html=True)
            else:
                st.error(f" {status_data['message']}")

        # --- Fetch and display event logs ---
        logs_df = fetch_event_logs()

        with log_container.container():
            if not logs_df.empty:
                html = "<div class='table-container'><table class='custom-table'>"
                html += "<thead><tr><th>Timestamp</th><th>Label</th><th>Confidence</th><th>Snapshot Link</th></tr></thead><tbody>"
                for _, row in logs_df.iterrows():
                    conf = float(row.get('confidence', 0))
                    conf_bar = f"<div class='custom-progress-bg'><div class='custom-progress-fill' style='width: {conf*100}%;'></div></div>"
                    link = row.get('display_url') or row.get('snapshot_path')
                    link_html = f"<a href='{link}' target='_blank' class='custom-link'>View Snapshot</a>" if link else ""
                    html += f"<tr><td style='white-space:nowrap;'>{row.get('timestamp', '')}</td><td>{row.get('label', '')}</td><td style='width: 30%;'>{conf_bar}<div style='font-size: 0.8em; margin-top:2px;'>{conf:.2f}</div></td><td>{link_html}</td></tr>"
                html += "</tbody></table></div>"
                st.markdown(html, unsafe_allow_html=True)
            else:
                st.warning("No events logged yet, or API is unavailable.")

        # Record poll time and schedule next rerun
        st.session_state['last_poll_time'] = time.time()

    # Schedule next poll — sleep only the remaining time to avoid drift
    time_until_next = max(0.1, POLL_INTERVAL - (time.time() - st.session_state['last_poll_time']))
    time.sleep(time_until_next)
    st.rerun()