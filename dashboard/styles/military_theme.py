"""Dark military theme CSS for Streamlit BVR Combat Dashboard."""

from __future__ import annotations

import streamlit as st


def inject_css() -> None:
    """Inject the dark military theme CSS into Streamlit."""
    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;700&family=Rajdhani:wght@400;600;700&display=swap');

        :root {
            --bg-primary: #080C14;
            --bg-secondary: #0D1321;
            --bg-card: #111827;
            --accent-blue: #00D4FF;
            --accent-red: #FF3B3B;
            --accent-green: #00FF88;
            --accent-amber: #FFB020;
            --text-primary: #EAF0FF;
            --text-secondary: #8892A8;
            --border: rgba(255,255,255,0.06);
        }

        .stApp {
            background: var(--bg-primary);
            color: var(--text-primary);
            font-family: 'Rajdhani', sans-serif;
        }

        h1, h2, h3 {
            color: var(--accent-blue) !important;
            font-family: 'Rajdhani', sans-serif;
            font-weight: 700;
            letter-spacing: 1px;
            text-transform: uppercase;
        }

        h1 {
            background: linear-gradient(90deg, #00D4FF 0%, #0066FF 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            font-size: 2.2rem !important;
        }

        .stTabs [data-baseweb="tab-list"] {
            gap: 8px;
            background: var(--bg-secondary);
            border-radius: 12px;
            padding: 6px;
        }

        .stTabs [data-baseweb="tab-list"] button {
            background: transparent;
            border-radius: 8px;
            font-family: 'Rajdhani', sans-serif;
            font-weight: 600;
            font-size: 1rem;
            letter-spacing: 0.5px;
            color: var(--text-secondary);
            padding: 8px 20px;
            transition: all 0.3s ease;
        }

        .stTabs [data-baseweb="tab-list"] button:hover {
            background: rgba(0, 212, 255, 0.08);
            color: var(--text-primary);
        }

        .stTabs [data-baseweb="tab-list"] button[aria-selected="true"] {
            background: rgba(0, 212, 255, 0.15);
            border: 1px solid rgba(0, 212, 255, 0.3);
            color: var(--accent-blue);
            box-shadow: 0 0 15px rgba(0, 212, 255, 0.1);
        }

        /* Metric cards */
        [data-testid="stMetricValue"] {
            font-family: 'JetBrains Mono', monospace;
            font-size: 2rem !important;
            color: var(--accent-green) !important;
        }

        [data-testid="stMetricLabel"] {
            font-family: 'Rajdhani', sans-serif;
            color: var(--text-secondary) !important;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 1px;
        }

        /* DataFrames */
        .stDataFrame {
            border: 1px solid var(--border);
            border-radius: 8px;
        }

        /* Sidebar */
        [data-testid="stSidebar"] {
            background: var(--bg-secondary);
            border-right: 1px solid var(--border);
        }

        [data-testid="stSidebar"] h1, [data-testid="stSidebar"] h2,
        [data-testid="stSidebar"] h3 {
            color: var(--accent-amber) !important;
        }

        /* Buttons */
        .stButton > button {
            background: linear-gradient(135deg, #0066FF, #00D4FF);
            color: white;
            border: none;
            border-radius: 8px;
            font-family: 'Rajdhani', sans-serif;
            font-weight: 700;
            letter-spacing: 1px;
            text-transform: uppercase;
            transition: all 0.3s ease;
        }

        .stButton > button:hover {
            box-shadow: 0 0 20px rgba(0, 212, 255, 0.3);
            transform: translateY(-1px);
        }

        /* Spinners */
        .stSpinner > div {
            border-color: var(--accent-blue) transparent transparent transparent !important;
        }

        code, pre { background: rgba(255,255,255,0.04) !important; }
        </style>
        """,
        unsafe_allow_html=True,
    )
