# equipment_case.py
# =========================================
# Streamlit dashboard with INSERT form for INEL.EquipmentFaults
# Direct DB insert, Faultid is a TEXT field entered by user (example shown A013).
# Preserves original helpers/visuals.
# =========================================
import streamlit as st
import pandas as pd
import pyodbc
import matplotlib.pyplot as plt
import numpy as np
from matplotlib import colors as mcolors
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import plotly.io as pio
import base64
import uuid
from datetime import datetime
import re
import time
import json

# Initialize session state for popup
if 'show_popup' not in st.session_state:
    st.session_state.show_popup = False
if 'popup_message' not in st.session_state:
    st.session_state.popup_message = ""

    
# =========================================
# Global CSS Overrides
# =========================================
st.markdown("""
    <style>
    /* 🔹 Transparent buttons */
    div.stButton > button, div.stDownloadButton > button {
        background-color: transparent !important;
        color: white !important;
        border: 1px solid rgba(255, 255, 255, 0.25);
        border-radius: 8px;
        padding: 0.5rem 1rem;
        font-weight: bold;
        transition: all 0.3s ease;
    }
    div.stButton > button:hover, div.stDownloadButton > button:hover {
        background-color: rgba(255, 255, 255, 0.1) !important;
        color: #fff !important;
    }

    /* Ensure close button text is visible on dark popup */
    div.stButton > button:focus {
        outline: none;
        box-shadow: 0 0 0 3px rgba(255,255,255,0.06);
    }

    </style>
""", unsafe_allow_html=True)

st.markdown("""
<style>
body, h1, h2, h3, p, div {
    font-family: 'Poppins', sans-serif !important;
}
</style>
""", unsafe_allow_html=True)


# =========================================
# Streamlit Page Config
# =========================================
st.set_page_config(
    page_title="EOL Quality Dashboard",
    layout="wide",
    initial_sidebar_state="expanded"
)


# =========================================
# Video Background Function
# =========================================
def add_bg_video():
    """Add background video to the dashboard"""
    video_path = r"C:\Users\hp\Downloads\3130182-uhd_3840_2160_30fps.mp4"
    
    try:
        # Read video file and encode to base64
        with open(video_path, "rb") as video_file:
            video_bytes = video_file.read()
            video_base64 = base64.b64encode(video_bytes).decode()
        
        # Inject CSS with video background
        video_css = f"""
        <style>
        /* Video Background */
        .stApp::before {{
            content: "";
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            z-index: -2;
            background: url("data:video/mp4;base64,{video_base64}");
        }}
        
        .video-background {{
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            z-index: -2;
            object-fit: cover;
        }}

        /* Optional dark overlay */
        .stApp::after {{
            content: "";
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            z-index: -1;
            background: rgba(0, 0, 0, 0.25); /* adjust for readability */
        }}
        </style>
        
        <video autoplay muted loop class="video-background">
            <source src="data:video/mp4;base64,{video_base64}" type="video/mp4">
        </video>
        """
        
        st.markdown(video_css, unsafe_allow_html=True)
        
    except FileNotFoundError:
        st.warning("⚠️ Video file not found. Using fallback gradient background.")
        st.markdown("""
        <style>
        .stApp {
            background: linear-gradient(135deg, #22c55e 0%, #4CAF50 50%, #22c55e 100%);
            background-attachment: fixed;
        }
        </style>
        """, unsafe_allow_html=True)
    except Exception as e:
        st.error(f"Error loading video background: {str(e)}")


# =========================================
# Custom CSS Styling (Transparent Glass Style + Ultra Transparent Top Bar)
# =========================================
st.markdown("""
<style>
/* Main app fully transparent */
.stApp {
    background: transparent !important;
}

/* Main content transparent glass */
.main .block-container {
    background: rgba(255, 255, 255, 0.08);
    border-radius: 20px;
    padding: 2rem;
    margin-top: 1rem;
    box-shadow: 0 8px 32px rgba(0, 0, 0, 0.2);
    border: 1px solid rgba(255, 255, 255, 0.15);
}

/* Headers */
h1, h2, h3 {
    background: transparent !important;
    color: white !important;
    text-shadow: 0 2px 6px rgba(0,0,0,0.6);
    font-weight: bold;
    text-align: center;
}

/* ============================= */
/* ULTRA TRANSPARENT TOP BAR */
/* ============================= */

/* Main header bar container - Much more transparent */
header[data-testid="stHeader"] {
    background: rgba(255, 255, 255, 0.001) !important;
    backdrop-filter: none !important;
    border: none !important;
    box-shadow: none !important;
}

/* Top toolbar - Almost invisible */
.css-18ni7ap {
    background: transparent !important;
    opacity: 0.7 !important;
}

/* Header elements - Ultra light */
.css-1avcm0n {
    background: transparent !important;
    opacity: 0.8 !important;
}

/* Navigation and menu items - Barely visible */
.css-1kyxreq {
    background: transparent !important;
    opacity: 0.7 !important;
}

/* Top bar buttons - Very transparent */
header button {
    background: rgba(255, 255, 255, 0.03) !important;
    color: rgba(255, 255, 255, 0.8) !important;
    border: 1px solid rgba(255, 255, 255, 0.1) !important;
    border-radius: 6px !important;
}

header button:hover {
    background: rgba(255, 255, 255, 0.08) !important;
    color: rgba(255, 255, 255, 0.9) !important;
}

/* Top bar text elements - Very light */
header .css-1kyxreq span,
header .css-1kyxreq p {
    color: rgba(255, 255, 255, 0.7) !important;
    text-shadow: 0 1px 2px rgba(0, 0, 0, 0.3) !important;
}

/* Streamlit menu button - Ultra light */
.css-14xtw13 {
    background: rgba(255, 255, 255, 0.03) !important;
    color: rgba(255, 255, 255, 0.7) !important;
    border: 1px solid rgba(255, 255, 255, 0.08) !important;
}

/* Top right menu area - Transparent */
.css-1rs6os {
    background: transparent !important;
    opacity: 0.8 !important;
}

/* Deploy button and other top buttons - Very light */
.css-1vbkxwb, .css-1cpxqw2 {
    background: rgba(255, 255, 255, 0.03) !important;
    color: rgba(255, 255, 255, 0.8) !important;
    border: 1px solid rgba(255, 255, 255, 0.1) !important;
    border-radius: 6px !important;
}

.css-1vbkxwb:hover, .css-1cpxqw2:hover {
    background: rgba(255, 255, 255, 0.08) !important;
    color: rgba(255, 255, 255, 0.95) !important;
}

/* Additional transparency for any missed elements */
header * {
    background: transparent !important;
}

/* Make the entire header area almost see-through */
header {
    opacity: 0.85 !important;
}
</style>
""", unsafe_allow_html=True)


# =========================================
# Run Background
# =========================================
add_bg_video()

# =========================================
# Matplotlib Global Style
# =========================================
plt.style.use('seaborn-v0_8-whitegrid')

# =========================================
# Database Connection
# =========================================
def create_connection():
    try:
        conn = pyodbc.connect(
            "DRIVER={ODBC Driver 17 for SQL Server};"
            "SERVER=mlsqlserver.database.windows.net;"
            "DATABASE=SYRMA;"
            "UID=SQLUSER;"
            "PWD=Admin@123;"
            "Connection Timeout=30;"
        )
        return conn
    except Exception as e:
        st.error(f"❌ Database connection failed: {str(e)}")
        return None

# =========================================
# Equipment lookup (friendly labels)
# =========================================
@st.cache_data(ttl=600)
def get_equipment_lookup():
    """Return list of (label, EquipmentID) tuples from INEL.Equipments."""
    query = "SELECT EquipmentID, EquipmentName, ProductionLineID FROM INEL.Equipments ORDER BY EquipmentID"
    conn = create_connection()
    if conn is None:
        return []
    try:
        df = pd.read_sql(query, conn)
        if df.empty:
            return []
        options = []
        for _, r in df.iterrows():
            eid = str(r['EquipmentID'])
            name = str(r['EquipmentName']) if not pd.isna(r['EquipmentName']) else ""
            line = str(r['ProductionLineID']) if 'ProductionLineID' in r and not pd.isna(r['ProductionLineID']) else ""
            label = f"{eid} - {name}"
            if line:
                label = f"{label} (Line:{line})"
            options.append((label, eid))
        return options
    except Exception:
        # fallback: try distinct IDs from faults table
        try:
            df2 = pd.read_sql("SELECT DISTINCT EquipmentID FROM INEL.EquipmentFaults ORDER BY EquipmentID", conn)
            return [(str(x), str(x)) for x in df2['EquipmentID'].tolist()]
        except Exception:
            return []
    finally:
        conn.close()

# =========================================
# DB insert helper (original)
# =========================================
def insert_equipment_fault_db(
    EquipmentID,
    FaultType,
    SeverityLevel,
    EquipmentStatus,
    FaultDate,
    ResolutionDate,
    ProductID,
    FaultStatus,
    MesaageReceviedTimestamp,
    Description,
    Faultid
):
    """Insert a row into INEL.EquipmentFaults (direct DB method)."""
    insert_sql = """
    INSERT INTO INEL.EquipmentFaults
    (EquipmentID, FaultType, SeverityLevel, EquipmentStatus, FaultDate, ResolutionDate,
     ProductID, FaultStatus, MesaageReceviedTimestamp, Description, Faultid)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """
    conn = create_connection()
    if conn is None:
        raise Exception("DB connection failed")
    try:
        cur = conn.cursor()
        cur.execute(
            insert_sql,
            (EquipmentID, FaultType, SeverityLevel, EquipmentStatus, FaultDate, ResolutionDate,
             ProductID, FaultStatus, MesaageReceviedTimestamp, Description, Faultid)
        )
        conn.commit()
    finally:
        conn.close()

# =========================================
# Visualization helpers (kept as-is)
# =========================================
def create_enhanced_gauge(value, title, max_value=3.0):
    if pd.isna(value):
        value = 0
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=value,
        number={"font": {"size": 1, "color": "rgba(0,0,0,0)"}},
        title={"text": title},
        gauge=dict(
            axis={"range": [0, max_value]},
            bar={"color": "lightblue"},
            steps=[
                {"range": [0, 0.85 * max_value], "color": "rgba(255,0,0,0.4)"},
                {"range": [0.85 * max_value, 0.95 * max_value], "color": "rgba(255,255,0,0.4)"},
                {"range": [0.95 * max_value, max_value], "color": "rgba(0,255,0,0.4)"}
            ],
            threshold={
                "line": {"color": "black", "width": 4},
                "thickness": 0.75,
                "value": value
            }
        )
    ))
    fig.add_annotation(x=0.5, y=0.35, text=f"{value:.3f}", showarrow=False,
                       font=dict(size=50, color="white"), xanchor="center", yanchor="middle")
    fig.update_layout(plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                      margin=dict(l=20, r=20, t=50, b=20), height=300, width=300)
    return fig

def create_trend_chart(data, row, test_id):
    if data.empty:
        return None
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=data['TestDate'], y=data['Value'], mode="lines+markers", name="Value"))
    if not pd.isna(row.LSL):
        fig.add_hline(y=row.LSL, line_dash="dash", line_color="red", annotation_text="LSL")
    if not pd.isna(row.HSL):
        fig.add_hline(y=row.HSL, line_dash="dash", line_color="green", annotation_text="HSL")
    if not pd.isna(row.MeanVal):
        fig.add_hline(y=row.MeanVal, line_dash="dot", line_color="orange", annotation_text="Mean")
    fig.update_layout(plot_bgcolor="rgba(0,0,0,0.2)", paper_bgcolor="rgba(0,0,0,0.6)",
                      margin=dict(l=20,r=20,t=40,b=20), height=350)
    return fig

# =========================================
# Local FaultID generator (kept as helper, but NOT used to force value in UI)
# =========================================
def get_next_faultid_local():
    conn = create_connection()
    if conn is None:
        return "A013"
    try:
        df = pd.read_sql("SELECT Faultid FROM INEL.EquipmentFaults WHERE Faultid IS NOT NULL", conn)
        nums = []
        if not df.empty:
            for v in df['Faultid'].astype(str).tolist():
                m = re.match(r'^[Aa](\d+)$', v.strip())
                if m:
                    try:
                        nums.append(int(m.group(1)))
                    except Exception:
                        continue
        if nums:
            nextn = max(nums) + 1
            return f"A{nextn:03d}" if nextn >= 100 else f"A{nextn:02d}"
        # fallback
        cnt_df = pd.read_sql("SELECT COUNT(*) AS cnt FROM INEL.EquipmentFaults", conn)
        cnt = int(cnt_df.iloc[0]['cnt']) if not cnt_df.empty else 0
        if cnt >= 12:
            return "A013"
        else:
            return f"A{(cnt+1):02d}"
    except Exception:
        return "A013"
    finally:
        conn.close()

# =========================================
# Popup helper (UPDATED: Close button INSIDE popup, styled)
# =========================================
def show_center_popup(title, message, key_suffix):
    """
    Show a centered popup. The overlay has pointer-events:none so
    Streamlit widgets (Close button) remain clickable. The popup box
    itself uses pointer-events:auto so it looks interactive while not
    blocking the Streamlit button.
    """
    state_key = f"show_popup_{key_suffix}"
    if state_key not in st.session_state:
        st.session_state[state_key] = True

    if st.session_state[state_key]:
        # Note: overlay has pointer-events:none which allows clicks to pass through,
        # but the inner box has pointer-events:auto so it captures mouse hover/selection visually.
        popup_html = f"""
        <div id="insert-popup" style="
            position:fixed;
            top:0;left:0;width:100%;height:100%;
            z-index:9998;
            display:flex;align-items:center;justify-content:center;
            pointer-events:none;
        ">
          <div style="
              background:#0b1220;
              color:white;
              padding:24px;
              border-radius:12px;
              box-shadow:0 6px 30px rgba(0,0,0,0.6);
              min-width:320px;
              max-width:720px;
              text-align:center;
              pointer-events:auto;
          ">
            <h2 style="margin:0 0 12px 0">{title}</h2>
            <p style="margin:0 0 18px 0; white-space:pre-wrap;">{message}</p>
            <!-- visual spacer where the Streamlit button will appear -->
            <div style="height:8px;"></div>
          </div>
        </div>
        """
        st.markdown(popup_html, unsafe_allow_html=True)

        # Render the real Streamlit Close button centered, visually "inside" the popup.
        # The global CSS at top already styles buttons to match the popup theme.
        popup_placeholder = st.empty()
        with popup_placeholder.container():
            # small vertical offset to align the button over the popup box visually
            st.markdown("<div style='height:8px;'></div>", unsafe_allow_html=True)
            col1, col2, col3 = st.columns([3,2,3])
            with col2:
                if st.button("Close", key=f"close_popup_{key_suffix}"):
                    st.session_state[state_key] = False
                    st.rerun()


# =========================================
# Main App
# =========================================
def main():
    add_bg_video()
    st.markdown("<div class='main-header'><h1> EOL Quality Dashboard</h1></div>", unsafe_allow_html=True)
    # 🔹 Inject CSS (for main-header styling)
    st.markdown("""
        <style>
        .main-header {
            margin-top: -130px;      /* moves title up */
            text-align: center;
            color: white;
            text-shadow: 0 2px 6px rgba(0,0,0,0.6);
            font-size: 2rem;
            font-weight: 800;
        }
        </style>
    """, unsafe_allow_html=True)

    # Insert Equipment Fault form
    st.markdown("""
    <div style="padding:8px; border-radius:8px; background:rgba(255,255,255,0.02); margin-bottom:12px;">
        <h2 style="color:white; margin: 6px 0;">➕ Insert Equipment Fault</h2>
    </div>
    """, unsafe_allow_html=True)

    equip_options = get_equipment_lookup()
    labels = [l for l, _ in equip_options]
    ids = [i for _, i in equip_options]

    # store a sensible example in session (not used to force value)
    if 'example_faultid' not in st.session_state:
        st.session_state['example_faultid'] = "A013"

    with st.form("insert_fault_form_main"):
        col1, col2 = st.columns([2,2])
        with col1:
            if labels:
                sel_idx = st.selectbox("Equipment", ["--select--"] + labels, index=0)
                selected_equipment = None
                if sel_idx != "--select--":
                    sel_index = labels.index(sel_idx)
                    selected_equipment = ids[sel_index]
            else:
                selected_equipment = st.text_input("Equipment ID (manual)")

            FaultType = st.selectbox("Fault Type", ["", "Breakdown", "Under Maintenance", "No Power", "No Raw Material", "OverHeating"])
            SeverityLevel = st.selectbox("Severity Level", ["", "High", "Medium", "Low"])
            EquipmentStatus = st.selectbox("Equipment Status", ["", "Running", "Stopped", "Under Maintenance"])
        with col2:
            try:
                FaultDate = st.datetime_input("Fault Date & Time", value=datetime.now())
            except Exception:
                date_val = st.date_input("Fault Date", value=datetime.now().date())
                time_val = st.time_input("Fault Time", value=datetime.now().time())
                FaultDate = datetime.combine(date_val, time_val)

            add_resolution = st.checkbox("Add Resolution Date & Time")
            if add_resolution:
                try:
                    ResolutionDate = st.datetime_input("Resolution Date & Time", value=None)
                except Exception:
                    date_val2 = st.date_input("Resolution Date", value=None)
                    time_val2 = st.time_input("Resolution Time", value=None)
                    ResolutionDate = datetime.combine(date_val2, time_val2) if date_val2 and time_val2 else None
            else:
                ResolutionDate = None

            ProductID = st.selectbox("ProductID", ["", "PR1", "PR2", "PR3"])
            FaultStatus = st.selectbox("Fault Status", ["", "Open", "Closed", "InProgress", "Escalated", "True", "False"])
            try:
                MesaageReceviedTimestamp = st.datetime_input("Message Received Timestamp", value=datetime.now())
            except Exception:
                MesaageReceviedTimestamp = datetime.now()

        Description = st.text_area("Description", value="", height=120)

        # USER-ENTERED Faultid (text). Example shown as placeholder & default value A013.
        Faultid = st.text_input(
            "Faultid (text) - enter exactly as in table (e.g. A013)",
            value=st.session_state.get('example_faultid', "A013"),
            placeholder="e.g. A013"
        )

        submitted = st.form_submit_button("Insert Fault")

    if submitted:
        selected_equipment_val = selected_equipment if isinstance(selected_equipment, str) else selected_equipment

        # validations
        if not selected_equipment_val:
            st.error("Please select or enter an Equipment ID.")
            return
        if ProductID == "" or ProductID is None:
            st.error("Please choose a ProductID (PR1 / PR2 / PR3).")
            return
        if FaultType == "" or FaultType is None:
            st.error("Please choose Fault Type.")
            return
        if FaultStatus == "" or FaultStatus is None:
            st.error("Please choose Fault Status.")
            return
        if SeverityLevel == "" or SeverityLevel is None:
            st.error("Please choose Severity Level.")
            return
        if EquipmentStatus == "" or EquipmentStatus is None:
            st.error("Please choose Equipment Status.")
            return
        if not Faultid or not re.match(r'^[Aa]\d+$', Faultid.strip()):
            st.error("Faultid is required and must start with 'A' followed by digits (e.g. A013).")
            return

        # pass values to DB (ResolutionDate will be None if user didn't add it)
        resolution_dt = ResolutionDate if ResolutionDate else None
        description = Description.strip() or None
        fid = Faultid.strip()

        try:
            insert_equipment_fault_db(
                EquipmentID=selected_equipment_val,
                FaultType=FaultType,
                SeverityLevel=SeverityLevel,
                EquipmentStatus=EquipmentStatus,
                FaultDate=FaultDate,
                ResolutionDate=resolution_dt,
                ProductID=ProductID,
                FaultStatus=FaultStatus,
                MesaageReceviedTimestamp=MesaageReceviedTimestamp,
                Description=description,
                Faultid=fid
            )

            # Generate a unique key for this popup instance
            popup_key = str(uuid.uuid4())[:8]
            show_center_popup("Inserted", f"Fault inserted successfully with Faultid: {fid}", popup_key)

            # update example in session to next numeric suggestion (non-enforced)
            m = re.match(r'^[Aa](\d+)$', fid)
            if m:
                try:
                    nxtn = int(m.group(1)) + 1
                    # keep same digit width if present (preserve leading zeros)
                    width = len(m.group(1))
                    st.session_state['example_faultid'] = f"A{nxtn:0{width}d}"
                except Exception:
                    st.session_state['example_faultid'] = get_next_faultid_local()
            else:
                st.session_state['example_faultid'] = get_next_faultid_local()

        except Exception as e:
            st.error(f"Insert failed: {e}")


if __name__ == "__main__":
    main()
