import streamlit as st
import pandas as pd
import os
from datetime import datetime

# ---------------- CONFIG ----------------
st.set_page_config(
    page_title="Maintenance Management System",
    layout="wide"
)

EXCEL_PATH = "machines.xlsx"

# ---------------- LOAD DATA ----------------
@st.cache_data
def load_excel():
    if not os.path.exists(EXCEL_PATH):
        st.error(f"❌ ملف Excel غير موجود: {EXCEL_PATH}")
        st.stop()

    xls = pd.ExcelFile(EXCEL_PATH, engine="openpyxl")

    required_sheets = {
        "machines": "Machines",
        "types": "Maintenance_Types",
        "map": "Machine_Maint_Map",
        "logs": "Maintenance_Log",
    }

    data = {}
    for key, sheet in required_sheets.items():
        if sheet not in xls.sheet_names:
            st.error(f"❌ الشيت غير موجود: {sheet}")
            st.info(f"📄 الشيتات الحالية: {xls.sheet_names}")
            st.stop()

        data[key] = pd.read_excel(xls, sheet)

    return data


# ---------------- APP ----------------
st.title("🛠️ Maintenance Management System")

data = load_excel()

machines = data["machines"]
types = data["types"]
map_df = data["map"]
logs = data["logs"]

# ---------------- SIDEBAR ----------------
st.sidebar.header("القائمة")

page = st.sidebar.radio(
    "اختار الصفحة",
    [
        "الماكينات",
        "أنواع الصيانة",
        "ربط الماكينات بالصيانة",
        "سجل الصيانة"
    ]
)

# ---------------- PAGES ----------------
if page == "الماكينات":
    st.subheader("📋 جدول الماكينات")
    st.dataframe(machines, use_container_width=True)

elif page == "أنواع الصيانة":
    st.subheader("🛢️ أنواع الصيانة")
    st.dataframe(types, use_container_width=True)

elif page == "ربط الماكينات بالصيانة":
    st.subheader("🔗 ربط الماكينات بأنواع الصيانة")
    st.dataframe(map_df, use_container_width=True)

elif page == "سجل الصيانة":
    st.subheader("🗒️ سجل الصيانة")

    if "Last_Maintenance_Date" in logs.columns:
        logs["Last_Maintenance_Date"] = pd.to_datetime(
            logs["Last_Maintenance_Date"],
            errors="coerce"
        )

        logs["Days_Since_Last"] = (
            datetime.now() - logs["Last_Maintenance_Date"]
        ).dt.days

    st.dataframe(logs, use_container_width=True)

# ---------------- FOOTER ----------------
st.markdown("---")
st.caption("Streamlit + Excel + GitHub | Maintenance System")
