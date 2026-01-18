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
        st.error("❌ ملف machines.xlsx غير موجود في الريبو")
        st.stop()

    xls = pd.ExcelFile(EXCEL_PATH, engine="openpyxl")

    return {
        "machines": pd.read_excel(xls, "Machines"),
        "types": pd.read_excel(xls, "Maintenance_Types"),
        "logs": pd.read_excel(xls, "Maintenance_Log"),
    }

def save_excel(machines, types, logs):
    with pd.ExcelWriter(EXCEL_PATH, engine="openpyxl", mode="w") as writer:
        machines.to_excel(writer, sheet_name="Machines", index=False)
        types.to_excel(writer, sheet_name="Maintenance_Types", index=False)
        logs.to_excel(writer, sheet_name="Maintenance_Log", index=False)

    st.cache_data.clear()

# ---------------- APP ----------------
st.title("🛠️ Maintenance Management System")

data = load_excel()

machines = data["machines"]
types = data["types"]
logs = data["logs"]

# ---------------- SIDEBAR ----------------
page = st.sidebar.radio(
    "القائمة",
    ["إضافة صيانة", "عرض الماكينات", "سجل الصيانة"]
)

# ---------------- ADD MAINTENANCE ----------------
if page == "إضافة صيانة":
    st.subheader("➕ تسجيل صيانة جديدة")

    with st.form("add_maintenance_form"):

        machine_name = st.selectbox(
            "اسم الماكينة",
            machines["Machine_Name"].unique()
        )

        department = machines.loc[
            machines["Machine_Name"] == machine_name,
            "Department"
        ].values[0]

        st.text_input("القسم", department, disabled=True)

        maintenance_type = st.selectbox(
            "نوع الصيانة",
            types["Maintenance_Name"].unique()
        )

        last_date = st.date_input("تاريخ آخر صيانة")

        operating_hours = st.number_input(
            "عدد ساعات التشغيل",
            min_value=0,
            step=1
        )

        submit = st.form_submit_button("💾 حفظ الصيانة")

    if submit:
        new_log = {
            "Log_ID": len(logs) + 1,
            "Machine_Name": machine_name,
            "Maintenance_Name": maintenance_type,
            "Last_Date": last_date,
            "Operating_Hours": operating_hours
        }

        logs = pd.concat([logs, pd.DataFrame([new_log])], ignore_index=True)

        save_excel(machines, types, logs)

        st.success("✅ تم تسجيل الصيانة بنجاح")

# ---------------- MACHINES VIEW ----------------
elif page == "عرض الماكينات":
    st.subheader("📋 الماكينات")
    st.dataframe(machines, use_container_width=True)

# ---------------- LOGS VIEW ----------------
elif page == "سجل الصيانة":
    st.subheader("🗒️ سجل الصيانة")

    logs["Last_Date"] = pd.to_datetime(logs["Last_Date"], errors="coerce")
    logs["Days_Since_Last"] = (datetime.now() - logs["Last_Date"]).dt.days

    st.dataframe(logs, use_container_width=True)

# ---------------- FOOTER ----------------
st.markdown("---")
st.caption("Maintenance System | Streamlit + Excel + GitHub")
