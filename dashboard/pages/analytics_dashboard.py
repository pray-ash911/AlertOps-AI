# Dashboard Imports
import streamlit as st
import requests
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
import json

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
        bg_main = "#EEF2FF"      # soft indigo/lavender tint — NOT white
        bg_card = "#F8F7FF"      # very light purple card
        sidebar = "#F0F4FF"      # slightly deeper lavender sidebar
        text_main = "#1E1B4B"    # deep indigo text
        text_muted = "#6B7280"
        border = "#C7D2FE"       # indigo-tinted border
        accent = "#4F46E5"       # strong indigo accent

    css = f"""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
        
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
            margin-top: -8rem !important; /* Force content up to eliminate gap */
            padding-bottom: 2rem !important;
            max-width: 1400px !important;
        }}

        /* Sidebar */
        [data-testid="stSidebar"] {{
            background: var(--sidebar) !important;
            border-right: 1px solid var(--border) !important;
        }}
        [data-testid="stSidebar"] * {{
            color: var(--text-main) !important;
        }}

        /* Header Styles */
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

        /* Metric Card Styles */
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
        
        .weapon-card {{ border-top: 3px solid var(--danger); }}
        .crowd-card  {{ border-top: 3px solid var(--success); }}
        .total-card  {{ border-top: 3px solid var(--accent); }}

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

        /* Button Styles */
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

        /* Info Box Styles */
        .info-box {{
            background: var(--bg-card);
            padding: 1.2rem 1.5rem;
            border-radius: var(--radius);
            border: 1px solid var(--border);
            margin: 1rem 0;
            color: var(--text-main) !important;
            font-size: 0.95rem;
        }}

        /* Data Table Styles */
        .stDataFrame {{
            background: var(--bg-card);
            border: 1px solid var(--border);
            border-radius: var(--radius);
        }}
        .stDataFrame th {{
            background: var(--sidebar) !important;
            color: var(--text-main) !important;
            font-weight: 600;
            text-transform: uppercase;
        }}
        .stDataFrame td {{
            background: var(--bg-card) !important;
            color: var(--text-main) !important;
            border-bottom: 1px solid var(--border) !important;
        }}

        /* Tab Styles */
        .stTabs [data-baseweb="tab-list"] {{
            gap: 2rem;
            border-bottom: 1px solid var(--border);
            padding-bottom: 0px;
            background: transparent;
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
            background: transparent !important;
        }}

        /* Metrics Styles */
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

        /* Badge Styles */
        .alert-badge {{
            display: inline-block;
            padding: 0.4rem 0.8rem;
            border-radius: 6px;
            font-size: 0.85rem;
            font-weight: 600;
            margin-right: 0.5rem;
            margin-bottom: 0.5rem;
        }}
        .weapon-alert {{
            background-color: #fef2f2;
            color: var(--danger);
            border: 1px solid #fecaca;
        }}
        .crowd-alert {{
            background-color: #ecfdf5;
            color: var(--success);
            border: 1px solid #a7f3d0;
        }}

        /* Hourly Stat Box Styles */
        .hour-stat-box {{
            background: var(--bg-card);
            padding: 1.2rem;
            border-radius: var(--radius);
            margin-bottom: 1rem;
            border: 1px solid var(--border);
            box-shadow: 0 1px 3px rgba(0,0,0,0.02);
        }}

        /* Section Header Styles */
        .section-header {{
            font-size: 1.1rem;
            font-weight: 600;
            color: var(--text-main) !important;
            margin-bottom: 1rem;
            padding-bottom: 0.5rem;
            border-bottom: 1px solid var(--border);
        }}

        /* Radio Button Styles */
        .stRadio > div {{
            background: transparent !important;
            padding: 0;
            border: none !important;
        }}

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

# Inject the dynamic CSS logic and get theme variables
css_str, bg_main, bg_card, sidebar, text_main, text_muted, border, accent = inject_custom_css()
st.markdown(css_str, unsafe_allow_html=True)

# Page Configuration
st.set_page_config(
    page_title="AI Surveillance Analytics Dashboard",
    layout="wide",
    initial_sidebar_state="expanded",
    page_icon=""
)

# Application Constants
LOCAL_URL = "http://127.0.0.1:8000"
ANALYTICS_URL = f"{LOCAL_URL}/api/analytics/"

# Main Title and Logo Representation
st.markdown(f"""
<div style="margin-bottom: 2rem; display: flex; justify-content: space-between; align-items: flex-end;">
    <div style="display: flex; align-items: center; gap: 20px;">
        <img src="{LOCAL_URL}/static/images/AlertOps logo.png" 
             style="width: 100px; height: 100px; border-radius: 8px; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1);">
        <div>
            <h1 class="main-header" style="font-size: 2.2rem; line-height: 1;">Lift Capacity Analytics</h1>
            <div style="color: var(--text-muted); font-size: 1rem; margin-top: 6px;">Historical detection data and trends</div>
        </div>
    </div>
    <div style="margin-bottom: 0.5rem;">
        <span style="background: var(--bg-card); color: var(--success); padding: 8px 16px; border-radius: 6px; font-size: 0.85rem; font-weight: 600; border: 1px solid var(--border); box-shadow: 0 1px 2px rgba(0,0,0,0.05);">
            ● SYSTEM ONLINE
        </span>
    </div>
</div>
""", unsafe_allow_html=True)

# Sidebar Configuration
st.sidebar.markdown("### Settings")
st.sidebar.markdown("---")

# Add dark/light toggle
is_dark_active = st.session_state.theme == "Dark"
theme_toggle = st.sidebar.toggle("Dark Mode", value=is_dark_active)
new_theme = "Dark" if theme_toggle else "Light"

if new_theme != st.session_state.theme:
    st.session_state.theme = new_theme
    st.rerun()

st.sidebar.markdown("---")
st.sidebar.header("Dashboard Configuration")

# Data Source Selection
data_source = st.sidebar.radio(
    "Data Source:",
    ["Live API"],
    index=0
)

# Date Range Configuration
st.sidebar.header("Analysis Period")
days_back = st.sidebar.slider(
    "Days to analyze:",
    min_value=7,
    max_value=90,
    value=30,
    step=1
)

# Event Filters
st.sidebar.header("Event Type Filter")
show_weapons = st.sidebar.checkbox("Show Weapon Detections", value=True)
show_crowd = st.sidebar.checkbox("Show Overcrowding Events", value=True)

# Chart Visualization Configuration
st.sidebar.header("Chart Settings")
chart_height = st.sidebar.slider("Chart Height", 300, 600, 400)

st.sidebar.markdown("---")
# Data Refresh Control
if st.sidebar.button("Refresh Data", use_container_width=True):
    st.rerun()

st.sidebar.markdown("---")
st.sidebar.markdown("""
<div class="info-box" style="margin-top: 2rem;">
    <strong>Dashboard Information</strong><br><br>
    • Shows long-term overcrowding trends<br>
    • Filter logs by date range<br>
    • Ensure backend connectivity
</div>
""", unsafe_allow_html=True)


@st.cache_data(ttl=300)  # Cache for 5 minutes
# Data Fetching Function
def fetch_analytics_data():
    try:
        response = requests.get(ANALYTICS_URL, timeout=10)
        if response.status_code == 200:
            return response.json()
        else:
            st.error(f"API Error: {response.status_code}")
            return None
    except Exception as e:
        st.error(f"Connection Error: {e}")
        return None


# Data Loading Logic
if data_source == "Live API":
    with st.spinner("Fetching data from API..."):
        data = fetch_analytics_data()

    if data is None:
        st.warning("Could not connect to API. Using sample data.")
        data_source = "Sample Data"

# Sample Data Generation Fallback
if data_source == "Sample Data" or data is None:

    # Generate comprehensive sample data for visualization
    dates = pd.date_range(end=datetime.now(), periods=days_back, freq='D')
    analytics_data = []

    for i, date in enumerate(dates):
        # Create realistic patterns based on day of week

        day_of_week = date.weekday()

        if day_of_week >= 5:  # Saturday, Sunday having more events
            weapon = np.random.poisson(lam=2.5)
            crowd = np.random.poisson(lam=8)

        elif day_of_week == 4:  # Friday moderate-high activity
            weapon = np.random.poisson(lam=2.0)
            crowd = np.random.poisson(lam=6)

        else:  # Regular weekday patterns
            weapon = np.random.poisson(lam=1.2)
            crowd = np.random.poisson(lam=4)

        # Add trend patterns for recent days
        if i > days_back * 0.7:  # Recent days have more activity
            weapon = min(weapon + np.random.randint(0, 2), 5)
            crowd = min(crowd + np.random.randint(0, 3), 12)

        analytics_data.append({
            'date': date.strftime('%Y-%m-%d'),
            'weapon': int(weapon),
            'overcrowding': int(crowd),
            'total_detections': int(weapon + crowd)
        })

    # Structuring the final data dictionary
    data = {
        'daily_analytics': analytics_data,
        'hourly_analytics': [
            {
                'hour': hour,
                'weapon': max(0, int(np.random.normal(loc=1.5 if 9 <= hour <= 21 else 0.3, scale=0.5))),
                'overcrowding': max(0, int(np.random.normal(loc=4 if 9 <= hour <= 21 else 1, scale=1.5))),
                'total': 0
            }
            for hour in range(24)
        ],
        'summary': {
            'total_weapons': sum(item['weapon'] for item in analytics_data),
            'total_overcrowding': sum(item['overcrowding'] for item in analytics_data),
            'total_all': sum(item['weapon'] + item['overcrowding'] for item in analytics_data),
            'avg_daily_weapons': round(sum(item['weapon'] for item in analytics_data) / len(analytics_data), 1),
            'avg_daily_crowd': round(sum(item['overcrowding'] for item in analytics_data) / len(analytics_data), 1),
            'today_weapon': analytics_data[-1]['weapon'],
            'today_crowd': analytics_data[-1]['overcrowding'],
            'peak_hour': "14:00",
            'peak_hour_weapon': 3,
            'peak_hour_crowd': 9
        }
    }

# Data Processing for Visualization
daily_df = pd.DataFrame(data['daily_analytics'])
daily_df['date'] = pd.to_datetime(daily_df['date'])
daily_df['day_of_week'] = daily_df['date'].dt.day_name()
daily_df['week_number'] = daily_df['date'].dt.isocalendar().week
daily_df['month'] = daily_df['date'].dt.strftime('%Y-%m')

hourly_df = pd.DataFrame(data['hourly_analytics'])

# Display Data Source Verification
source_info = "Sample Data" if data_source == "Sample Data" else "Live API Data"
st.markdown(f"""
<div class="info-box">
    <strong>Data Status:</strong> {source_info} | <strong>  Period:</strong> Last {days_back} days | <strong> Last Updated:</strong> {datetime.now().strftime('%H:%M:%S')}
</div>
""", unsafe_allow_html=True)

# Key Performance Indicators Section
st.markdown('<h2 class="sub-header">Key Performance Indicators</h2>', unsafe_allow_html=True)

col1, col2, col3, col4, col5, col6 = st.columns(6)

with col1:
    total_weapons = data['summary']['total_weapons']
    st.markdown(f"""
    <div class="metric-card weapon-card">
        <div class="metric-value">{total_weapons}</div>
        <div class="metric-label">Total Weapons Detected</div>
        <div style="font-size: 0.8rem; color: #94a3b8; margin-top: 0.5rem;">
            Avg: {data['summary']['avg_daily_weapons']}/day
        </div>
    </div>
    """, unsafe_allow_html=True)

with col2:
    total_crowd = data['summary']['total_overcrowding']
    st.markdown(f"""
    <div class="metric-card crowd-card">
        <div class="metric-value">{total_crowd}</div>
        <div class="metric-label">Overcrowding Events</div>
        <div style="font-size: 0.8rem; color: #94a3b8; margin-top: 0.5rem;">
            Avg: {data['summary']['avg_daily_crowd']}/day
        </div>
    </div>
    """, unsafe_allow_html=True)

with col3:
    total_all = data['summary']['total_all']
    st.markdown(f"""
    <div class="metric-card total-card">
        <div class="metric-value">{total_all}</div>
        <div class="metric-label">Total Security Events</div>
        <div style="font-size: 0.8rem; color: #94a3b8; margin-top: 0.5rem;">
            Combined detection count
        </div>
    </div>
    """, unsafe_allow_html=True)

with col4:
    today_weapon = data['summary']['today_weapon']
    st.markdown(f"""
    <div class="metric-card weapon-card">
        <div class="metric-value">{today_weapon}</div>
        <div class="metric-label">Today's Weapons</div>
        <div style="font-size: 0.8rem; color: #94a3b8; margin-top: 0.5rem;">
            Current day detection
        </div>
    </div>
    """, unsafe_allow_html=True)

with col5:
    today_crowd = data['summary']['today_crowd']
    st.markdown(f"""
    <div class="metric-card crowd-card">
        <div class="metric-value">{today_crowd}</div>
        <div class="metric-label">Today's Crowd Events</div>
        <div style="font-size: 0.8rem; color: #94a3b8; margin-top: 0.5rem;">
            Current day events
        </div>
    </div>
    """, unsafe_allow_html=True)

with col6:
    peak_hour = data['summary']['peak_hour']
    st.markdown(f"""
    <div class="metric-card total-card">
        <div class="metric-value">{peak_hour}</div>
        <div class="metric-label">Peak Activity Hour</div>
        <div style="font-size: 0.8rem; color: #94a3b8; margin-top: 0.5rem;">
            Weapons: {data['summary'].get('peak_hour_weapon', 0)} | Crowd: {data['summary'].get('peak_hour_crowd', 0)}
        </div>
    </div>
    """, unsafe_allow_html=True)

# Daily Trends Analysis Section
st.markdown('<h2 class="sub-header">Daily Trends Analysis</h2>', unsafe_allow_html=True)

tab1, tab2, tab3 = st.tabs(["Daily Chart", "Comparison View", "Statistics"])

with tab1:
    # Daily Trends Bar Chart
    fig_daily = go.Figure()

    if show_weapons and 'weapon' in daily_df.columns:
        fig_daily.add_trace(go.Bar(
            x=daily_df['date'],
            y=daily_df['weapon'],
            name='Weapon Detections',
            marker_color='#ef4444',
            opacity=0.8,
            hovertemplate='Date: %{x}<br>Weapons: %{y}<extra></extra>'
        ))

    if show_crowd and 'overcrowding' in daily_df.columns:
        fig_daily.add_trace(go.Bar(
            x=daily_df['date'],
            y=daily_df['overcrowding'],
            name='Overcrowding Events',
            marker_color='#0f4c81',
            opacity=0.8,
            hovertemplate='Date: %{x}<br>Crowd Events: %{y}<extra></extra>'
        ))

    fig_daily.update_layout(
        title=f"Daily Detection Trends (Last {days_back} Days)",
        xaxis_title="Date",
        yaxis_title="Number of Events",
        template="plotly_white",
        height=chart_height,
        barmode='group',
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
            bgcolor='rgba(255, 255, 255, 0)',
            bordercolor='rgba(229, 231, 235, 0)',
            font=dict(color=text_main)
        ),
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        font=dict(color=text_main, family="Inter, sans-serif"),
        title_font=dict(color=text_main, size=18)
    )

    # Configure Grid Layout
    fig_daily.update_xaxes(
        showgrid=True,
        gridwidth=1,
        gridcolor=border,
        linecolor=border
    )
    fig_daily.update_yaxes(
        showgrid=True,
        gridwidth=1,
        gridcolor=border,
        linecolor=border
    )

    st.plotly_chart(fig_daily, use_container_width=True)

with tab2:
    col1, col2 = st.columns(2)

    with col1:

        # Area Chart Visualization
        fig_area = go.Figure()

        if show_weapons and 'weapon' in daily_df.columns:
            fig_area.add_trace(go.Scatter(
                x=daily_df['date'],
                y=daily_df['weapon'],
                mode='lines',
                name='Weapons',
                stackgroup='one',
                line=dict(color='#ef4444', width=0),
                fillcolor='rgba(239, 68, 68, 0.4)',
                hovertemplate='Date: %{x}<br>Weapons: %{y}<extra></extra>'
            ))

        if show_crowd and 'overcrowding' in daily_df.columns:
            fig_area.add_trace(go.Scatter(
                x=daily_df['date'],
                y=daily_df['overcrowding'],
                mode='lines',
                name='Overcrowding',
                stackgroup='one',
                line=dict(color='#0f4c81', width=0),
                fillcolor='rgba(15, 76, 129, 0.4)',
                hovertemplate='Date: %{x}<br>Crowd Events: %{y}<extra></extra>'
            ))

        fig_area.update_layout(
            title="Stacked Daily Events",
            xaxis_title="Date",
            yaxis_title="Number of Events",
            template="plotly_white",
            height=chart_height - 50,
            showlegend=True,
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
            font=dict(color=text_main),
            title_font=dict(color=text_main, size=16),
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="right",
                x=1,
                bgcolor='rgba(0,0,0,0)',
                font=dict(color=text_main)
            )
        )
        
        fig_area.update_xaxes(gridcolor=border, linecolor=border)
        fig_area.update_yaxes(gridcolor=border, linecolor=border)

        st.plotly_chart(fig_area, use_container_width=True)

    with col2:

        # Comparison Bar Chart
        fig_bar = go.Figure()

        # Focusing on the last 14 days
        recent_df = daily_df.tail(14)

        if show_weapons:
            fig_bar.add_trace(go.Bar(
                x=recent_df['date'],
                y=recent_df['weapon'],
                name='Weapons',
                marker_color='red',
                opacity=0.8,
                hovertemplate='Date: %{x}<br>Weapons: %{y}<extra></extra>'
            ))

        if show_crowd:
            fig_bar.add_trace(go.Bar(
                x=recent_df['date'],
                y=recent_df['overcrowding'],
                name='Overcrowding',
                marker_color='blue',
                opacity=0.8,
                hovertemplate='Date: %{x}<br>Crowd Events: %{y}<extra></extra>'
            ))

        fig_bar.update_layout(
            title="Recent 14 Days Comparison",
            xaxis_title="Date",
            yaxis_title="Count",
            barmode='group',
            template="plotly_white",
            height=chart_height - 50,
            showlegend=True,
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
            font=dict(color=text_main),
            title_font=dict(color=text_main),
            legend=dict(font=dict(color=text_main))
        )
        
        fig_bar.update_xaxes(gridcolor=border, linecolor=border)
        fig_bar.update_yaxes(gridcolor=border, linecolor=border)

        st.plotly_chart(fig_bar, use_container_width=True)

with tab3:
    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown("Weapon Statistics")
        if 'weapon' in daily_df.columns:
            st.metric("Average Daily", f"{daily_df['weapon'].mean():.2f}")
            st.metric("Maximum Daily", f"{daily_df['weapon'].max():.0f}")
            st.metric("Minimum Daily", f"{daily_df['weapon'].min():.0f}")
            st.metric("Standard Deviation", f"{daily_df['weapon'].std():.2f}")
            st.metric("Days with Weapons", f"{(daily_df['weapon'] > 0).sum():.0f}")

    with col2:
        st.markdown("Crowd Statistics")
        if 'overcrowding' in daily_df.columns:
            st.metric("Average Daily", f"{daily_df['overcrowding'].mean():.2f}")
            st.metric("Maximum Daily", f"{daily_df['overcrowding'].max():.0f}")
            st.metric("Minimum Daily", f"{daily_df['overcrowding'].min():.0f}")
            st.metric("Standard Deviation", f"{daily_df['overcrowding'].std():.2f}")
            st.metric("Days with Crowd Events", f"{(daily_df['overcrowding'] > 0).sum():.0f}")

    with col3:
        st.markdown("Combined Statistics")
        if 'total_detections' in daily_df.columns:
            st.metric("Total Events", f"{daily_df['total_detections'].sum():.0f}")
            st.metric("Average Total Daily", f"{daily_df['total_detections'].mean():.2f}")
            correlation = daily_df['weapon'].corr(
                daily_df['overcrowding']) if 'weapon' in daily_df.columns and 'overcrowding' in daily_df.columns else 0
            st.metric("Weapon-Crowd Correlation", f"{correlation:.3f}")
            st.metric("Highest Alert Day", f"{daily_df['total_detections'].max():.0f}")
            st.metric("Alert-Free Days", f"{(daily_df['total_detections'] == 0).sum():.0f}")

# Hourly Activity Patterns Section
st.markdown('<h2 class="sub-header">Hourly Activity Patterns</h2>', unsafe_allow_html=True)

col1, col2 = st.columns([2, 1])

with col1:
    # Hourly Analysis Chart with Dual Axis
    fig_hourly = go.Figure()

    # Adding secondary axis support
    fig_hourly = make_subplots(specs=[[{"secondary_y": True}]])

    if show_weapons:
        fig_hourly.add_trace(
            go.Bar(
                x=hourly_df['hour'],
                y=hourly_df['weapon'],
                name='Weapons',
                marker_color='red',
                opacity=0.7,
                hovertemplate='Hour: %{x}:00<br>Weapons: %{y}<extra></extra>'
            ),
            secondary_y=False,
        )

    if show_crowd:
        fig_hourly.add_trace(
            go.Bar(
                x=hourly_df['hour'],
                y=hourly_df['overcrowding'],
                name='Overcrowding',
                marker_color='blue',
                opacity=0.7,
                hovertemplate='Hour: %{x}:00<br>Crowd Events: %{y}<extra></extra>'
            ),
            secondary_y=True,
        )

    # X-Axis Configuration
    fig_hourly.update_xaxes(
        title_text="Hour of Day",
        tickmode='array',
        tickvals=list(range(0, 24, 2)),
        ticktext=[f"{h:02d}:00" for h in range(0, 24, 2)],
        gridcolor=border,
        linecolor=border,
        title_font=dict(color=text_main),
        tickfont=dict(color=text_main)
    )

    # Y-Axis Configuration
    fig_hourly.update_yaxes(
        title_text="Weapon Detections",
        secondary_y=False,
        title_font=dict(color=text_main),
        gridcolor=border,
        linecolor=border,
        tickfont=dict(color=text_main)
    )

    fig_hourly.update_yaxes(
        title_text="Overcrowding Events",
        secondary_y=True,
        title_font=dict(color=text_main),
        gridcolor=border,
        linecolor=border,
        tickfont=dict(color=text_main)
    )

    fig_hourly.update_layout(
        title="Hourly Distribution of Events",
        barmode='overlay',
        height=chart_height,
        template="plotly_white",
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
            bgcolor='rgba(0,0,0,0)',
            font=dict(color=text_main)
        ),
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        font=dict(color=text_main),
        title_font=dict(color=text_main)
    )

    st.plotly_chart(fig_hourly, use_container_width=True)

with col2:
    # Top Weapon Hours Display
    if show_weapons and 'weapon' in hourly_df.columns:
        st.markdown(f'<h3 class="left-align" style="color: var(--danger);">Top Weapon Hours</h3>', unsafe_allow_html=True)
        top_weapon_hours = hourly_df.nlargest(3, 'weapon')[['hour', 'weapon']]
        for idx, row in top_weapon_hours.iterrows():
            col_left, col_right = st.columns([2, 1])
            with col_left:
                st.markdown(f"<p style='font-weight: 600; color: var(--danger); margin: 0;'>{int(row['hour']):02d}:00</p>",
                            unsafe_allow_html=True)
            with col_right:
                st.markdown(
                    f"<p style='font-weight: 700; color: var(--danger); text-align: right; margin: 0;'>{int(row['weapon'])}</p>",
                    unsafe_allow_html=True)
            st.markdown(f"<div style='height: 1px; background-color: {border}; margin: 0.5rem 0;'></div>",
                        unsafe_allow_html=True)

    # Top Crowd Hours Display
    if show_crowd and 'overcrowding' in hourly_df.columns:
        st.markdown(f'<h3 class="left-align" style="color: var(--success);">Top Crowd Hours</h3>', unsafe_allow_html=True)
        top_crowd_hours = hourly_df.nlargest(3, 'overcrowding')[['hour', 'overcrowding']]
        for idx, row in top_crowd_hours.iterrows():
            col_left, col_right = st.columns([2, 1])
            with col_left:
                st.markdown(f"<p style='font-weight: 600; color: var(--success); margin: 0;'>{int(row['hour']):02d}:00</p>",
                            unsafe_allow_html=True)
            with col_right:
                st.markdown(
                    f"<p style='font-weight: 700; color: var(--success); text-align: right; margin: 0;'>{int(row['overcrowding'])}</p>",
                    unsafe_allow_html=True)
            st.markdown(f"<div style='height: 1px; background-color: {border}; margin: 0.5rem 0;'></div>",
                        unsafe_allow_html=True)

    # Hourly Activity Summary
    st.markdown(f'<h3 class="left-align" style="color: {accent};">Hourly Summary</h3>', unsafe_allow_html=True)

    if show_weapons:
        avg_weapons_hourly = hourly_df['weapon'].mean()
        col_left, col_right = st.columns([2, 1])
        with col_left:
            st.markdown(f"<p style='margin: 0; color: {text_main};'>Avg Weapons/Hour</p>", unsafe_allow_html=True)
        with col_right:
            st.markdown(
                f"<p style='margin: 0; font-weight: 600; text-align: right; color: var(--danger);'>{avg_weapons_hourly:.2f}</p>",
                unsafe_allow_html=True)
        st.markdown(f"<div style='height: 1px; background-color: {border}; margin: 0.5rem 0;'></div>",
                    unsafe_allow_html=True)

    if show_crowd:
        avg_crowd_hourly = hourly_df['overcrowding'].mean()
        col_left, col_right = st.columns([2, 1])
        with col_left:
            st.markdown(f"<p style='margin: 0; color: {text_main};'>Avg Crowd Events/Hour</p>", unsafe_allow_html=True)
        with col_right:
            st.markdown(
                f"<p style='margin: 0; font-weight: 600; text-align: right; color: var(--success);'>{avg_crowd_hourly:.2f}</p>",
                unsafe_allow_html=True)
        st.markdown(f"<div style='height: 1px; background-color: {border}; margin: 0.5rem 0;'></div>",
                    unsafe_allow_html=True)

# Weekly and Monthly Pattern Analysis
st.markdown('<h2 class="sub-header">Weekly And Monthly Patterns</h2>', unsafe_allow_html=True)

col1, col2 = st.columns(2)

with col1:
    # Weekly Data Aggregation
    weekly_stats = daily_df.groupby('day_of_week').agg({
        'weapon': 'mean',
        'overcrowding': 'mean',
        'total_detections': 'mean'
    }).reindex(['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'])

    fig_weekly = go.Figure()

    if show_weapons:
        fig_weekly.add_trace(go.Bar(
            x=weekly_stats.index,
            y=weekly_stats['weapon'],
            name='Avg Weapons',
            marker_color='red',
            opacity=0.7,
            hovertemplate='Day: %{x}<br>Avg Weapons: %{y:.2f}<extra></extra>'
        ))

    if show_crowd:
        fig_weekly.add_trace(go.Bar(
            x=weekly_stats.index,
            y=weekly_stats['overcrowding'],
            name='Avg Crowd Events',
            marker_color='blue',
            opacity=0.7,
            hovertemplate='Day: %{x}<br>Avg Crowd Events: %{y:.2f}<extra></extra>'
        ))

    fig_weekly.update_layout(
        title="Average Events by Day of Week",
        xaxis_title="Day",
        yaxis_title="Average Count",
        barmode='group',
        template="plotly_white",
        height=chart_height - 100,
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        font=dict(color=text_main),
        title_font=dict(color=text_main)
    )
    
    fig_weekly.update_xaxes(gridcolor=border, linecolor=border)
    fig_weekly.update_yaxes(gridcolor=border, linecolor=border)

    st.plotly_chart(fig_weekly, use_container_width=True)

with col2:
    # Monthly Data Aggregation

    if len(daily_df) > 30:
        monthly_stats = daily_df.groupby('month').agg({
            'weapon': 'sum',
            'overcrowding': 'sum',
            'total_detections': 'sum'
        }).reset_index()

        fig_monthly = go.Figure()

        if show_weapons:
            fig_monthly.add_trace(go.Bar(
                x=monthly_stats['month'],
                y=monthly_stats['weapon'],
                name='Total Weapons',
                marker_color='red',
                opacity=0.7,
                hovertemplate='Month: %{x}<br>Total Weapons: %{y}<extra></extra>'
            ))

        if show_crowd:
            fig_monthly.add_trace(go.Bar(
                x=monthly_stats['month'],
                y=monthly_stats['overcrowding'],
                name='Total Crowd Events',
                marker_color='blue',
                opacity=0.7,
                hovertemplate='Month: %{x}<br>Total Crowd Events: %{y}<extra></extra>'
            ))

        fig_monthly.update_layout(
            title="Monthly Totals",
            xaxis_title="Month",
            yaxis_title="Total Count",
            barmode='group',
            template="plotly_white",
            height=chart_height - 100,
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
            font=dict(color=text_main),
            title_font=dict(color=text_main)
        )
        
        fig_monthly.update_xaxes(gridcolor=border, linecolor=border)
        fig_monthly.update_yaxes(gridcolor=border, linecolor=border)

        st.plotly_chart(fig_monthly, use_container_width=True)
    else:

        # Event Distribution Pie Chart Fallback
        st.markdown("### Event Distribution")

        # Calculate summary statistics
        total_weapons = data['summary']['total_weapons']
        total_crowd = data['summary']['total_overcrowding']

        fig_pie = go.Figure(data=[go.Pie(
            labels=['Weapon Detections', 'Overcrowding Events'],
            values=[total_weapons, total_crowd],
            hole=.3,
            marker_colors=['#ef4444', '#3b82f6'],
            textinfo='label+percent',
            hovertemplate='%{label}: %{value} events<extra></extra>'
        )])

        fig_pie.update_layout(
            height=chart_height - 100,
            showlegend=False,
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
            font=dict(color=text_main)
        )

        st.plotly_chart(fig_pie, use_container_width=True)

# Recent Events and Export Section
st.markdown('<h2 class="sub-header">Recent Events and Data</h2>', unsafe_allow_html=True)

tab1, tab2 = st.tabs(["Recent Events", "Export Data"])

with tab1:
    # Recent Events Table
    if 'recent_events' in data and data['recent_events']:
        recent_events_df = pd.DataFrame(data['recent_events'])

        # Prepare DataFrame for Display
        display_df = recent_events_df.copy()
        if 'timestamp' in display_df.columns:
            display_df['timestamp'] = pd.to_datetime(display_df['timestamp'])
            display_df['Date'] = display_df['timestamp'].dt.strftime('%Y-%m-%d')
            display_df['Time'] = display_df['timestamp'].dt.strftime('%H:%M:%S')

        # Filter and Rename Columns
        columns_to_show = []
        if 'Date' in display_df.columns:
            columns_to_show.append('Date')
        if 'Time' in display_df.columns:
            columns_to_show.append('Time')
        if 'type__name' in display_df.columns:
            columns_to_show.append('type__name')
        if 'confidence_value' in display_df.columns:
            columns_to_show.append('confidence_value')
        if 'status' in display_df.columns:
            columns_to_show.append('status')

        if columns_to_show:
            display_df = display_df[columns_to_show]
            display_df.columns = [col.replace('type__name', 'Event Type')
                                  .replace('confidence_value', 'Confidence/Count')
                                  .replace('status', 'Status') for col in display_df.columns]

            st.dataframe(
                display_df,
                use_container_width=True,
                height=300,
                column_config={
                    "Event Type": st.column_config.TextColumn(
                        "Event Type",
                        help="Type of security event"
                    ),
                    "Confidence/Count": st.column_config.NumberColumn(
                        "Confidence/Count",
                        format="%.2f",
                        help="Confidence score for weapons or count for overcrowding"
                    )
                }
            )
    else:
        st.info("No recent events data available. Events will appear here as they are detected.")

with tab2:
    col1, col2 = st.columns([2, 1])

    with col1:
        st.markdown("### Raw Data Preview")
        st.dataframe(
            daily_df[['date', 'weapon', 'overcrowding', 'total_detections', 'day_of_week']],
            use_container_width=True,
            height=250
        )

    with col2:
        st.markdown("### Export Options")

        # Convert DataFrames to CSV for Download
        daily_csv = daily_df.to_csv(index=False)
        hourly_csv = hourly_df.to_csv(index=False)

        st.download_button(
            label="Download Daily Data (CSV)",
            data=daily_csv,
            file_name=f"surveillance_daily_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv",
            use_container_width=True
        )

        st.download_button(
            label="Download Hourly Data (CSV)",
            data=hourly_csv,
            file_name=f"surveillance_hourly_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv",
            use_container_width=True
        )

        # Export Full Data as JSON
        json_data = json.dumps(data, indent=2)
        st.download_button(
            label="Download Full Data (JSON)",
            data=json_data,
            file_name=f"surveillance_full_{datetime.now().strftime('%Y%m%d')}.json",
            mime="application/json",
            use_container_width=True
        )

# Dashboard Footer
st.markdown("---")
col1, col2, col3 = st.columns([1, 2, 1])

with col1:
    st.markdown(
        f"<div style='color: var(--text-muted);'><strong>Last Updated:</strong> {datetime.now().strftime('%H:%M:%S')}</div>",
        unsafe_allow_html=True)

with col2:
    st.markdown(
        f"<div style='color: var(--text-muted); text-align: center;'><strong>AI Surveillance Analytics Dashboard</strong> - Real-time weapon and overcrowding detection monitoring</div>",
        unsafe_allow_html=True)

with col3:
    if st.button("Refresh Now", use_container_width=True):
        st.rerun()

# Bottom Spacing
st.markdown("<br><br>", unsafe_allow_html=True)