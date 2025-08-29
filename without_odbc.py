import streamlit as st
import pandas as pd
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
from sqlalchemy import create_engine, text

# =========================================
# Session state for popup
# =========================================
if 'show_popup' not in st.session_state:
    st.session_state.show_popup = False
if 'popup_message' not in st.session_state:
    st.session_state.popup_message = ""

# =========================================
# Global CSS Overrides
# =========================================
st.markdown("""
    <style>
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
    video_path = r"C:\Users\hp\Downloads\3130182-uhd_3840_2160_30fps.mp4"
    try:
        with open(video_path, "rb") as video_file:
            video_bytes = video_file.read()
            video_base64 = base64.b64encode(video_bytes).decode()
        video_css = f"""
        <style>
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
        .stApp::after {{
            content: "";
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            z-index: -1;
            background: rgba(0, 0, 0, 0.25);
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
# Custom CSS Styling
# =========================================
st.markdown("""
<style>
.stApp { background: transparent !important; }
.main .block-container {
    background: rgba(255, 255, 255, 0.08);
    border-radius: 20px;
    padding: 2rem;
    margin-top: 1rem;
    box-shadow: 0 8px 32px rgba(0, 0, 0, 0.2);
    border: 1px solid rgba(255, 255, 255, 0.15);
}
h1, h2, h3 {
    background: transparent !important;
    color: white !important;
    text-shadow: 0 2px 6px rgba(0,0,0,0.6);
    font-weight: bold;
    text-align: center;
}
header[data-testid="stHeader"] {
    background: rgba(255, 255, 255, 0.001) !important;
    border: none !important;
    box-shadow: none !important;
}
header * { background: transparent !important; }
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
# Database Connection (SQLAlchemy + pytds)
# =========================================
def create_connection():
    try:
        server = "mlsqlserver.database.windows.net"
        database = "SYRMA"
        username = "SQLUSER"
        password = "Admin@123"
        conn_str = f"mssql+pytds://{username}:{password}@{server}/{database}"
        engine = create_engine(conn_str)
        return engine
    except Exception as e:
        st.error(f"❌ Database connection failed: {str(e)}")
        return None

# =========================================
# Equipment lookup
# =========================================
@st.cache_data(ttl=600)
def get_equipment_lookup():
    query = "SELECT EquipmentID, EquipmentName, ProductionLineID FROM INEL.Equipments ORDER BY EquipmentID"
    engine = create_connection()
    if engine is None: return []
    try:
        df = pd.read_sql(query, engine)
        if df.empty: return []
        options = []
        for _, r in df.iterrows():
            eid = str(r['EquipmentID'])
            name = str(r['EquipmentName']) if not pd.isna(r['EquipmentName']) else ""
            line = str(r['ProductionLineID']) if 'ProductionLineID' in r and not pd.isna(r['ProductionLineID']) else ""
            label = f"{eid} - {name}"
            if line: label = f"{label} (Line:{line})"
            options.append((label, eid))
        return options
    except Exception:
        try:
            df2 = pd.read_sql("SELECT DISTINCT EquipmentID FROM INEL.EquipmentFaults ORDER BY EquipmentID", engine)
            return [(str(x), str(x)) for x in df2['EquipmentID'].tolist()]
        except Exception:
            return []
    finally:
        engine.dispose()

# =========================================
# DB insert helper
# =========================================
def insert_equipment_fault_db(
    EquipmentID, FaultType, SeverityLevel, EquipmentStatus,
    FaultDate, ResolutionDate, ProductID, FaultStatus,
    MesaageReceviedTimestamp, Description, Faultid
):
    insert_sql = """
    INSERT INTO INEL.EquipmentFaults
    (EquipmentID, FaultType, SeverityLevel, EquipmentStatus, FaultDate, ResolutionDate,
     ProductID, FaultStatus, MesaageReceviedTimestamp, Description, Faultid)
    VALUES (:EquipmentID, :FaultType, :SeverityLevel, :EquipmentStatus, :FaultDate, :ResolutionDate,
            :ProductID, :FaultStatus, :MesaageReceviedTimestamp, :Description, :Faultid)
    """
    engine = create_connection()
    if engine is None: raise Exception("DB connection failed")
    try:
        with engine.begin() as conn:
            conn.execute(text(insert_sql), {
                "EquipmentID": EquipmentID,
                "FaultType": FaultType,
                "SeverityLevel": SeverityLevel,
                "EquipmentStatus": EquipmentStatus,
                "FaultDate": FaultDate,
                "ResolutionDate": ResolutionDate,
                "ProductID": ProductID,
                "FaultStatus": FaultStatus,
                "MesaageReceviedTimestamp": MesaageReceviedTimestamp,
                "Description": Description,
                "Faultid": Faultid
            })
    finally:
        engine.dispose()

# =========================================
# Popup helper
# =========================================
def show_center_popup(title, message, key_suffix):
    state_key = f"show_popup_{key_suffix}"
    if state_key not in st.session_state:
        st.session_state[state_key] = True
    if st.session_state[state_key]:
        popup_html = f"""
        <div id="insert-popup" style="position:fixed;top:0;left:0;width:100%;height:100%;
            z-index:9998;display:flex;align-items:center;justify-content:center;pointer-events:none;">
          <div style="background:#0b1220;color:white;padding:24px;border-radius:12px;
              box-shadow:0 6px 30px rgba(0,0,0,0.6);min-width:320px;max-width:720px;
              text-align:center;pointer-events:auto;">
            <h2 style="margin:0 0 12px 0">{title}</h2>
            <p style="margin:0 0 18px 0; white-space:pre-wrap;">{message}</p>
            <div style="height:8px;"></div>
          </div>
        </div>
        """
        st.markdown(popup_html, unsafe_allow_html=True)
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

    st.markdown("""
    <div style="padding:8px; border-radius:8px; background:rgba(255,255,255,0.02); margin-bottom:12px;">
        <h2 style="color:white; margin: 6px 0;">➕ Insert Equipment Fault</h2>
    </div>
    """, unsafe_allow_html=True)

    equip_options = get_equipment_lookup()
    labels = [l for l, _ in equip_options]
    ids = [i for _, i in equip_options]

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
            FaultDate = st.datetime_input("Fault Date & Time", value=datetime.now())
            add_resolution = st.checkbox("Add Resolution Date & Time")
            ResolutionDate = st.datetime_input("Resolution Date & Time") if add_resolution else None
            ProductID = st.selectbox("ProductID", ["", "PR1", "PR2", "PR3"])
            FaultStatus = st.selectbox("Fault Status", ["", "Open", "Closed", "InProgress", "Escalated", "True", "False"])
            MesaageReceviedTimestamp = st.datetime_input("Message Received Timestamp", value=datetime.now())

        Description = st.text_area("Description", value="", height=120)
        Faultid = st.text_input("Faultid (e.g. A013)", value=st.session_state.get('example_faultid', "A013"))
        submitted = st.form_submit_button("Insert Fault")

    if submitted:
        if not selected_equipment:
            st.error("Please select or enter an Equipment ID."); return
        if not ProductID: st.error("Please choose a ProductID."); return
        if not FaultType: st.error("Please choose Fault Type."); return
        if not FaultStatus: st.error("Please choose Fault Status."); return
        if not SeverityLevel: st.error("Please choose Severity Level."); return
        if not EquipmentStatus: st.error("Please choose Equipment Status."); return
        if not Faultid or not re.match(r'^[Aa]\d+$', Faultid.strip()):
            st.error("Faultid is required and must start with 'A' followed by digits (e.g. A013)."); return
        try:
            insert_equipment_fault_db(
                EquipmentID=selected_equipment, FaultType=FaultType, SeverityLevel=SeverityLevel,
                EquipmentStatus=EquipmentStatus, FaultDate=FaultDate, ResolutionDate=ResolutionDate,
                ProductID=ProductID, FaultStatus=FaultStatus, MesaageReceviedTimestamp=MesaageReceviedTimestamp,
                Description=Description.strip() or None, Faultid=Faultid.strip()
            )
            popup_key = str(uuid.uuid4())[:8]
            show_center_popup("Inserted", f"Fault inserted successfully with Faultid: {Faultid}", popup_key)
        except Exception as e:
            st.error(f"Insert failed: {e}")

if __name__ == "__main__":
    main()
