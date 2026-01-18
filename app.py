import streamlit as st
import pandas as pd
from datetime import datetime
import io
from github import Github

# ================== CONFIG ==================
EXCEL_PATH = "data/machines.xlsx"

st.set_page_config(page_title="Maintenance System", layout="wide")

# ================== LOAD DATA ==================
@st.cache_data
def load_excel():
    xls = pd.ExcelFile(EXCEL_PATH)
    return {
        "machines": pd.read_excel(xls, "الماكينات"),
        "tasks": pd.read_excel(xls, "المهام"),
        "logs": pd.read_excel(xls, "السجل"),
        "settings": pd.read_excel(xls, "الإعدادات")
    }

data = load_excel()

# ================== SAVE & SYNC ==================
def save_and_push(dfs):
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        dfs["machines"].to_excel(writer, sheet_name="الماكينات", index=False)
        dfs["tasks"].to_excel(writer, sheet_name="المهام", index=False)
        dfs["logs"].to_excel(writer, sheet_name="السجل", index=False)
        dfs["settings"].to_excel(writer, sheet_name="الإعدادات", index=False)

    g = Github(st.secrets["github"]["token"])
    repo = g.get_repo(st.secrets["github"]["repo"])
    file = repo.get_contents(EXCEL_PATH, ref="main")

    repo.update_file(
        path=file.path,
        message="Auto update maintenance data",
        content=buffer.getvalue(),
        sha=file.sha,
        branch="main"
    )

# ================== HEADER ==================
st.title("🛠️ نظام إدارة الصيانة")

# ================== DASHBOARD ==================
st.subheader("📊 Dashboard")

col1, col2, col3 = st.columns(3)

total_machines = data["machines"].shape[0]
active_tasks = data["tasks"][data["tasks"]["نشطة"] == "نعم"].shape[0]

overdue = data["tasks"][data["tasks"]["عدد الساعات المتبقية"] <= 0].shape[0]

col1.metric("عدد الماكينات", total_machines)
col2.metric("الصيانات النشطة", active_tasks)
col3.metric("صيانات متأخرة", overdue)

st.divider()

# ================== MACHINE VIEW ==================
st.subheader("🔍 عرض ماكينة")

machine_name = st.selectbox(
    "اختر الماكينة",
    data["machines"]["اسم الماكينة"]
)

machine = data["machines"][data["machines"]["اسم الماكينة"] == machine_name].iloc[0]
machine_id = machine["id"]

st.info(f"""
**الموديل:** {machine['الموديل']}  
**الرقم التسلسلي:** {machine['الرقم التسلسلي']}  
**إجمالي ساعات التشغيل:** {machine['إجمالي ساعات التشغيل']}
""")

tasks = data["tasks"][
    (data["tasks"]["معرف الماكينة"] == machine_id) &
    (data["tasks"]["نشطة"] == "نعم")
]

result = []

for _, task in tasks.iterrows():
    count = data["logs"][
        (data["logs"]["معرف الماكينة"] == machine_id) &
        (data["logs"]["معرف المهمة"] == task["id"])
    ].shape[0]

    status = "🟢 تمام"
    if task["عدد الساعات المتبقية"] <= 0:
        status = "🔴 متأخرة"
    elif task["عدد الساعات المتبقية"] <= 50:
        status = "🟠 قربت"

    result.append({
        "نوع الصيانة": task["نوع الصيانة"],
        "آخر صيانة": task["تاريخ آخر صيانة"],
        "الساعات المتبقية": task["عدد الساعات المتبقية"],
        "عدد مرات التنفيذ": count,
        "الحالة": status
    })

st.dataframe(pd.DataFrame(result), use_container_width=True)

# ================== ADD MAINTENANCE ==================
st.divider()
st.subheader("➕ تسجيل صيانة جديدة")

with st.form("add_maintenance"):
    task_id = st.selectbox(
        "اختر نوع الصيانة",
        tasks["id"],
        format_func=lambda x: tasks[tasks["id"] == x]["نوع الصيانة"].values[0]
    )

    run_hours = st.number_input("عدد ساعات التشغيل الحالية", min_value=0)
    tech = st.text_input("تمت بواسطة")
    parts = st.text_input("الأجزاء المستبدلة")
    notes = st.text_area("ملاحظات")

    submit = st.form_submit_button("💾 حفظ")

    if submit:
        new_log = {
            "id": data["logs"].shape[0] + 1,
            "معرف الماكينة": machine_id,
            "معرف المهمة": task_id,
            "تاريخ الصيانة": datetime.now().strftime("%Y-%m-%d"),
            "عدد ساعات التشغيل": run_hours,
            "تمت بواسطة": tech,
            "الأجزاء المستبدلة": parts,
            "ملاحظات": notes,
            "تاريخ التسجيل": datetime.now().strftime("%Y-%m-%d")
        }

        data["logs"] = pd.concat([data["logs"], pd.DataFrame([new_log])])

        idx = data["tasks"][data["tasks"]["id"] == task_id].index[0]
        interval = data["tasks"].loc[idx, "الفترة بين الصيانة (ساعات)"]

        data["tasks"].loc[idx, "تاريخ آخر صيانة"] = datetime.now().strftime("%Y-%m-%d")
        data["tasks"].loc[idx, "عدد ساعات التشغيل عند آخر صيانة"] = run_hours
        data["tasks"].loc[idx, "عدد الساعات المتبقية"] = interval

        save_and_push(data)
        st.success("✅ تم تسجيل الصيانة وتحديث GitHub")
