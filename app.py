import streamlit as st
import pandas as pd
import os
from datetime import datetime
from git_utils import git_commit_push

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
        st.error("❌ ملف machines.xlsx غير موجود")
        st.stop()

    xls = pd.ExcelFile(EXCEL_PATH, engine="openpyxl")

    machines = pd.read_excel(xls, "Machines")
    types = pd.read_excel(xls, "Maintenance_Types")
    logs = pd.read_excel(xls, "Maintenance_Log")

    return machines, types, logs


def save_excel(machines, types, logs):
    with pd.ExcelWriter(EXCEL_PATH, engine="openpyxl", mode="w") as writer:
        machines.to_excel(writer, sheet_name="Machines", index=False)
        types.to_excel(writer, sheet_name="Maintenance_Types", index=False)
        logs.to_excel(writer, sheet_name="Maintenance_Log", index=False)

    git_commit_push("Update maintenance data")
    st.cache_data.clear()


# ---------------- APP ----------------
st.title("🛠️ Maintenance Management System")

machines, types, logs = load_excel()

# Detect columns dynamically
machine_col = machines.columns[0]
dept_col = machines.columns[1]
maint_col = types.columns[1]

# ---------------- SIDEBAR ----------------
page = st.sidebar.radio(
    "القائمة",
    ["إضافة صيانة", "عرض الماكينات", "سجل الصيانة"]
)

# ---------------- ADD MAINTENANCE ----------------
if page == "إضافة صيانة":
    st.subheader("➕ تسجيل صيانة جديدة")

    with st.form("maintenance_form"):
        machine_name = st.selectbox(
            "اسم الماكينة",
            machines[machine_col].unique()
        )

        department = machines.loc[
            machines[machine_col] == machine_name,
            dept_col
        ].values[0]

        st.text_input("القسم", department, disabled=True)

        maintenance_type = st.selectbox(
            "نوع الصيانة",
            types[maint_col].unique()
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
            logs.columns[0]: len(logs) + 1,
            logs.columns[1]: machine_name,
            logs.columns[2]: maintenance_type,
            logs.columns[3]: last_date,
            logs.columns[4]: operating_hours
        }

        logs = pd.concat([logs, pd.DataFrame([new_log])], ignore_index=True)

        save_excel(machines, types, logs)

        st.success("✅ تم تسجيل الصيانة ورفعها على GitHub")

# ---------------- MACHINES ----------------
elif page == "عرض الماكينات":
    st.subheader("📋 الماكينات")
    st.dataframe(machines, use_container_width=True)

# ---------------- LOGS ----------------
elif page == "سجل الصيانة":
    st.subheader("🗒️ سجل الصيانة")

    date_col = logs.columns[3]
    logs[date_col] = pd.to_datetime(logs[date_col], errors="coerce")
    logs["Days_Since_Last"] = (datetime.now() - logs[date_col]).dt.days

    st.dataframe(logs, use_container_width=True)

# ---------------- FOOTER ----------------
st.markdown("---")
st.caption("Excel + Streamlit + GitHub | Real Maintenance System")
