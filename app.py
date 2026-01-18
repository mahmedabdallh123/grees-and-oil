import streamlit as st
import pandas as pd
from datetime import datetime
from github import Github
import io
import json

# ---------------- CONFIG ----------------
EXCEL_PATH = "data/maintenance_db.xlsx"

# ---------------- LOAD DATA ----------------
@st.cache_data
def load_data():
    xls = pd.ExcelFile(EXCEL_PATH)
    return {
        "machines": pd.read_excel(xls, "Machines"),
        "maint_types": pd.read_excel(xls, "Maintenance_Types"),
        "map": pd.read_excel(xls, "Machine_Maint_Map"),
        "log": pd.read_excel(xls, "Maintenance_Log")
    }

data = load_data()

# ---------------- AUTH ----------------
with open("users.json") as f:
    USERS = json.load(f)

if "user" not in st.session_state:
    st.session_state.user = None

if not st.session_state.user:
    st.title("🔐 Login")
    u = st.text_input("Username")
    p = st.text_input("Password", type="password")
    if st.button("Login"):
        if u in USERS and USERS[u]["password"] == p:
            st.session_state.user = USERS[u]
            st.rerun()
        else:
            st.error("Invalid login")
    st.stop()

role = st.session_state.user["role"]

# ---------------- FUNCTIONS ----------------
def push_to_github(file_bytes):
    g = Github(st.secrets["github"]["token"])
    repo = g.get_repo(st.secrets["github"]["repo"])
    file = repo.get_contents(EXCEL_PATH, ref="main")

    repo.update_file(
        file.path,
        "Update maintenance database",
        file_bytes,
        file.sha,
        branch="main"
    )

def save_excel_and_sync(dfs):
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        dfs["machines"].to_excel(writer, "Machines", index=False)
        dfs["maint_types"].to_excel(writer, "Maintenance_Types", index=False)
        dfs["map"].to_excel(writer, "Machine_Maint_Map", index=False)
        dfs["log"].to_excel(writer, "Maintenance_Log", index=False)

    push_to_github(buffer.getvalue())

# ---------------- UI ----------------
st.title("🛠 Maintenance Management System")

tab1, tab2, tab3 = st.tabs(["📊 Dashboard", "🔍 Machine View", "➕ Add Maintenance"])

# -------- Dashboard --------
with tab1:
    today = datetime.today()
    alerts = []

    for _, row in data["log"].iterrows():
        maint = data["maint_types"][data["maint_types"]["maint_id"] == row["maint_id"]].iloc[0]
        days_passed = (today - pd.to_datetime(row["last_maint_date"])).days
        remaining = maint["interval_days"] - days_passed

        if remaining <= 0:
            alerts.append(row["machine_id"])

    st.metric("Total Machines", len(data["machines"]))
    st.metric("Overdue Maintenance", len(set(alerts)))

# -------- Machine View --------
with tab2:
    machine = st.selectbox("Select Machine", data["machines"]["machine_name"])
    mid = data["machines"][data["machines"]["machine_name"] == machine]["machine_id"].iloc[0]

    rows = data["map"][data["map"]["machine_id"] == mid]

    result = []
    for _, r in rows.iterrows():
        maint = data["maint_types"][data["maint_types"]["maint_id"] == r["maint_id"]].iloc[0]
        logs = data["log"][(data["log"]["machine_id"] == mid) & (data["log"]["maint_id"] == r["maint_id"])]

        if not logs.empty:
            last = logs.sort_values("last_maint_date").iloc[-1]
            days_left = maint["interval_days"] - (datetime.today() - pd.to_datetime(last["last_maint_date"])).days
            count = logs.shape[0]
        else:
            days_left = maint["interval_days"]
            count = 0

        result.append({
            "Maintenance": maint["maint_name"],
            "Remaining Days": days_left,
            "Times Done": count
        })

    st.dataframe(pd.DataFrame(result))

# -------- Add Maintenance --------
with tab3:
    if role != "viewer":
        m_id = st.selectbox("Machine ID", data["machines"]["machine_id"])
        mt_id = st.selectbox("Maintenance Type", data["maint_types"]["maint_id"])
        mat = st.text_input("Material Used")
        hrs = st.number_input("Run Hours", 0)
        tech = st.text_input("Technician")

        if st.button("Save"):
            new = {
                "log_id": data["log"].shape[0] + 1,
                "machine_id": m_id,
                "maint_id": mt_id,
                "material_used": mat,
                "run_hours": hrs,
                "last_maint_date": datetime.today().strftime("%Y-%m-%d"),
                "technician": tech
            }

            data["log"] = pd.concat([data["log"], pd.DataFrame([new])])
            save_excel_and_sync(data)
            st.success("Saved & Synced with GitHub ✅")
    else:
        st.warning("Read only access")
