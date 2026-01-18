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
    xls = pd.ExcelFile(EXCEL_PATH, engine="openpyxl")

    return {
        "machines": pd.read_excel(xls, "Machines"),
        "types": pd.read_excel(xls, "Maintenance_Types"),
        "map": pd.read_excel(xls, "Machine_Maint_Map"),
        "logs": pd.read_excel(xls, "Maintenance_Log"),
    }

def save_excel(machines, types, map_df, logs):
    with pd.ExcelWriter(EXCEL_PATH, engine="openpyxl", mode="w") as writer:
        machines.to_excel(writer, sheet_name="Machines", index=False)
        types.to_excel(writer, sheet_name="Maintenance_Types", index=False)
        map_df.to_excel(writer, sheet_name="Machine_Maint_Map", index=False)
        logs.to_excel(writer, sheet_name="Maintenance_Log", index=False)

    st.cache_data.clear()

# ---------------- APP ----------------
st.title("🛠️ Maintenance Management System")

data = load_excel()

machines = data["machines"]
types = data["types"]
map_df = data["map"]
logs = data["logs"]

# ---------------- SIDEBAR ----------------
page = st.sidebar.radio(
    "القائمة",
    [
        "إضافة صيانة",
        "عرض الماكينات",
        "سجل الصيانة"
    ]
)

# ---------------- ADD MAINTENANCE ----------------
if page == "إضافة صيانة":
    st.subheader("➕ تسجيل صيانة جديدة")

    with st.form("maintenance_form"):
        machine_name = st.text_input("اسم الماكينة")
        department = st.text_input("القسم")
        maint_type = st.selectbox(
            "نوع الصيانة",
            types["Maintenance_Type"].unique()
        )
        last_date = st.date_input("تاريخ آخر صيانة")
        operating_hours = st.number_input(
            "عدد ساعات التشغيل",
            min_value=0,
            step=1
        )

        submit = st.form_submit_button("💾 حفظ")

    if submit:
        if machine_name == "":
            st.error("❌ اسم الماكينة مطلوب")
        else:
            # إضافة ماكينة لو مش موجودة
            if machine_name not in machines["Machine_Name"].values:
                machines.loc[len(machines)] = [
                    len(machines) + 1,
                    machine_name,
                    department
                ]

            # تسجيل الصيانة
            logs.loc[len(logs)] = [
                machine_name,
                maint_type,
                last_date,
                operating_hours
            ]

            save_excel(machines, types, map_df, logs)

            st.success("✅ تم تسجيل الصيانة بنجاح")

# ---------------- MACHINES VIEW ----------------
elif page == "عرض الماكينات":
    st.subheader("📋 الماكينات")
    st.dataframe(machines, use_container_width=True)

# ---------------- LOGS VIEW ----------------
elif page == "سجل الصيانة":
    st.subheader("🗒️ سجل الصيانة")

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
st.caption("Maintenance System | Streamlit + Excel + GitHub")
