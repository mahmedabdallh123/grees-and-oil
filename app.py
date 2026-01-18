import streamlit as st
import pandas as pd
import os

# ---------------- CONFIG ----------------
st.set_page_config(
    page_title="Grease & Oil Management",
    layout="wide"
)

EXCEL_PATH = "machines.xlsx"

# ---------------- LOAD DATA ----------------
@st.cache_data
def load_excel():
    if not os.path.exists(EXCEL_PATH):
        st.error(f"❌ ملف Excel غير موجود: {EXCEL_PATH}")
        st.stop()

    try:
        xls = pd.ExcelFile(EXCEL_PATH, engine="openpyxl")
    except Exception as e:
        st.error("❌ فشل قراءة ملف Excel")
        st.exception(e)
        st.stop()

    # ✅ عرض أسماء الشيتات الموجودة (للتأكد)
    available_sheets = xls.sheet_names

    # خريطة أسماء الشيتات (عدّل الاسم لو حابب)
    sheet_map = {
        "machines": ["Machines", "الماكينات"],
        "tasks": ["Maintenance_Types", "المهام"],
        "logs": ["Maintenance_Log", "السجل"],
        "settings": ["Settings", "الإعدادات"]
    }

    data = {}

    for key, possible_names in sheet_map.items():
        found = None
        for name in possible_names:
            if name in available_sheets:
                found = name
                break

        if not found:
            st.error(f"❌ لم يتم العثور على شيت {possible_names}")
            st.info(f"📄 الشيتات الموجودة حاليًا: {available_sheets}")
            st.stop()

        data[key] = pd.read_excel(xls, found)

    return data


# ---------------- APP ----------------
st.title("🛢️ Grease & Oil Management System")

data = load_excel()

# ---------------- SIDEBAR ----------------
st.sidebar.header("القائمة")

page = st.sidebar.radio(
    "اختار الصفحة",
    ["الماكينات", "أنواع الصيانة", "سجل الصيانة", "الإعدادات"]
)

# ---------------- PAGES ----------------
if page == "الماكينات":
    st.subheader("📋 الماكينات")
    st.dataframe(data["machines"], use_container_width=True)

elif page == "أنواع الصيانة":
    st.subheader("🛠️ أنواع الصيانة")
    st.dataframe(data["tasks"], use_container_width=True)

elif page == "سجل الصيانة":
    st.subheader("🗒️ سجل الصيانة")
    st.dataframe(data["logs"], use_container_width=True)

elif page == "الإعدادات":
    st.subheader("⚙️ الإعدادات")
    st.dataframe(data["settings"], use_container_width=True)

# ---------------- FOOTER ----------------
st.markdown("---")
st.caption("Maintenance Management System | Streamlit + Excel + GitHub")
