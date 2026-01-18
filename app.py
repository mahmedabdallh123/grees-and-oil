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
    # 1️⃣ تأكد إن الملف موجود
    if not os.path.exists(EXCEL_PATH):
        st.error(f"❌ ملف Excel غير موجود: {EXCEL_PATH}")
        st.stop()

    # 2️⃣ افتح الملف مع تحديد engine (حل مشكلة ValueError)
    try:
        xls = pd.ExcelFile(EXCEL_PATH, engine="openpyxl")
    except Exception as e:
        st.error("❌ فشل قراءة ملف Excel")
        st.exception(e)
        st.stop()

    # 3️⃣ اقرأ الشيتات
    try:
        data = {
            "machines": pd.read_excel(xls, "الماكينات"),
            "tasks": pd.read_excel(xls, "المهام"),
            "logs": pd.read_excel(xls, "السجل"),
            "settings": pd.read_excel(xls, "الإعدادات"),
        }
    except Exception as e:
        st.error("❌ خطأ في أسماء الشيتات داخل ملف Excel")
        st.exception(e)
        st.stop()

    return data


# ---------------- APP ----------------
st.title("🛢️ Grease & Oil Management System")

data = load_excel()

# ---------------- SIDEBAR ----------------
st.sidebar.header("القائمة")

page = st.sidebar.radio(
    "اختار الصفحة",
    ["الماكينات", "المهام", "السجل", "الإعدادات"]
)

# ---------------- PAGES ----------------
if page == "الماكينات":
    st.subheader("📋 جدول الماكينات")
    st.dataframe(data["machines"], use_container_width=True)

elif page == "المهام":
    st.subheader("🛠️ جدول المهام")
    st.dataframe(data["tasks"], use_container_width=True)

elif page == "السجل":
    st.subheader("🗒️ سجل التشغيل")
    st.dataframe(data["logs"], use_container_width=True)

elif page == "الإعدادات":
    st.subheader("⚙️ الإعدادات")
    st.dataframe(data["settings"], use_container_width=True)

# ---------------- FOOTER ----------------
st.markdown("---")
st.caption("Developed for Maintenance & Reliability Engineers")
