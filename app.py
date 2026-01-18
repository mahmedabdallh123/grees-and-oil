import streamlit as st
import pandas as pd
import requests
import base64
from datetime import datetime

# ===============================
# إعدادات GitHub
# ===============================
REPO_NAME = "mahmedabdallh123/BELYARN"
BRANCH = "main"
FILE_PATH = "l4.xlsx"

GITHUB_API_URL = f"https://api.github.com/repos/{REPO_NAME}/contents/{FILE_PATH}"

GITHUB_TOKEN = st.secrets["GITHUB_TOKEN"]

HEADERS = {
    "Authorization": f"token {GITHUB_TOKEN}",
    "Accept": "application/vnd.github.v3+json"
}

st.set_page_config(page_title="CMMS صيانة", page_icon="🏭")
st.title("🛠 نظام إدارة الصيانات (CMMS)")

# ===============================
# تحميل ملف الإكسيل من GitHub
# ===============================
@st.cache_data
def load_excel():
    url = f"https://raw.githubusercontent.com/{REPO_NAME}/{BRANCH}/{FILE_PATH}"
    return pd.read_excel(url, sheet_name="maintenance")

try:
    df = load_excel()
except Exception as e:
    st.error("❌ خطأ في تحميل ملف الإكسيل")
    st.stop()

# ===============================
# عرض البيانات الحالية
# ===============================
st.subheader("📋 بيانات الصيانات الحالية")
st.dataframe(df, use_container_width=True)

# ===============================
# فورم إضافة صيانة جديدة
# ===============================
st.subheader("➕ إضافة سجل صيانة جديد")

with st.form("maintenance_form"):
    machine_name = st.text_input("اسم الماكينة")
    department = st.text_input("القسم")
    maintenance_type = st.selectbox(
        "نوع الصيانة",
        ["دورية", "طارئة", "تصحيحية", "وقائية"]
    )
    last_change = st.date_input("تاريخ آخر تغيير")
    operating_hours = st.number_input(
        "عدد ساعات التشغيل",
        min_value=0,
        step=1
    )

    submit = st.form_submit_button("💾 حفظ الصيانة")

# ===============================
# عند الضغط على حفظ
# ===============================
if submit:
    if machine_name.strip() == "" or department.strip() == "":
        st.warning("⚠️ لازم تدخل اسم الماكينة والقسم")
    else:
        new_row = {
            "Machine_Name": machine_name,
            "Department": department,
            "Maintenance_Type": maintenance_type,
            "Last_Change_Date": last_change.strftime("%Y-%m-%d"),
            "Operating_Hours": operating_hours
        }

        df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)

        # ===============================
        # رفع الملف إلى GitHub
        # ===============================
        response = requests.get(GITHUB_API_URL, headers=HEADERS)
        sha = response.json()["sha"]

        with open("l4.xlsx", "wb") as f:
            df.to_excel(f, sheet_name="maintenance", index=False)

        with open("l4.xlsx", "rb") as f:
            content = base64.b64encode(f.read()).decode("utf-8")

        data = {
            "message": f"Add maintenance record for {machine_name}",
            "content": content,
            "sha": sha,
            "branch": BRANCH
        }

        upload = requests.put(
            GITHUB_API_URL,
            headers=HEADERS,
            json=data
        )

        if upload.status_code in [200, 201]:
            st.success("✅ تم حفظ الصيانة ورفعها على GitHub")
            st.cache_data.clear()
            st.experimental_rerun()
        else:
            st.error("❌ فشل رفع الملف على GitHub")
