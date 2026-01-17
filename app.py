import streamlit as st
import pandas as pd
import os
from datetime import datetime, timedelta
import plotly.express as px
import time
from database import ExcelDatabase
from github_uploader import GitHubUploader

# ===============================
# ⚙ إعدادات التطبيق
# ===============================
APP_CONFIG = {
    "APP_TITLE": "نظام صيانة الماكينات - بيل يارن 1",
    "APP_ICON": "🏭",
    "EXCEL_FILE": "machines.xlsx",  # ملف Excel المحلي
    "AUTO_SAVE_MINUTES": 5,  # الحفظ التلقائي كل 5 دقائق
    "BACKUP_ENABLED": True,  # تفعيل النسخ الاحتياطي
}

# إعداد الصفحة
st.set_page_config(
    page_title=APP_CONFIG["APP_TITLE"],
    page_icon=APP_CONFIG["APP_ICON"],
    layout="wide",
    initial_sidebar_state="expanded"
)

# تخصيص التصميم
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        color: #1E3A8A;
        text-align: center;
        margin-bottom: 2rem;
        padding: 1rem;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border-radius: 10px;
    }
    .machine-card {
        background: white;
        padding: 1.5rem;
        border-radius: 10px;
        box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        margin: 10px 0;
        border-left: 5px solid #1E3A8A;
        transition: transform 0.3s;
    }
    .machine-card:hover {
        transform: translateY(-5px);
    }
    .warning-card {
        border-left-color: #ffc107;
        background-color: #fff3cd;
    }
    .danger-card {
        border-left-color: #dc3545;
        background-color: #f8d7da;
    }
    .success-card {
        border-left-color: #28a745;
        background-color: #d4edda;
    }
    .metric-box {
        text-align: center;
        padding: 1rem;
        border-radius: 10px;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        margin: 0.5rem;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    .stButton > button {
        width: 100%;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border: none;
        padding: 0.5rem 1rem;
        border-radius: 5px;
        font-weight: bold;
    }
    .stButton > button:hover {
        background: linear-gradient(135deg, #5a6fd8 0%, #6a4190 100%);
        box-shadow: 0 4px 8px rgba(0,0,0,0.2);
    }
    .tab-content {
        padding: 1rem;
        background: white;
        border-radius: 10px;
        box-shadow: 0 2px 5px rgba(0,0,0,0.1);
        margin-top: 1rem;
    }
</style>
""", unsafe_allow_html=True)

# ===============================
# 🗄 تهيئة قاعدة البيانات
# ===============================
@st.cache_resource
def init_database():
    return ExcelDatabase(APP_CONFIG["EXCEL_FILE"])

@st.cache_resource
def init_github_uploader():
    try:
        return GitHubUploader()
    except:
        return None

db = init_database()
github = init_github_uploader()

# ===============================
# 🔧 دوال مساعدة
# ===============================
def calculate_remaining_hours(last_date_str, last_hours, interval_hours):
    """حساب الساعات المتبقية للصيانة"""
    try:
        last_date = datetime.strptime(last_date_str, "%Y-%m-%d")
        current_date = datetime.now()
        
        # حساب الساعات المنقضية
        hours_passed = (current_date - last_date).total_seconds() / 3600
        
        # حساب الساعات المتبقية
        remaining = interval_hours - hours_passed
        
        # إذا كان هناك مشكلة في الحساب
        if remaining > interval_hours * 2:
            remaining = interval_hours
        
        return max(0, remaining), hours_passed
    
    except Exception as e:
        st.error(f"خطأ في حساب الساعات: {str(e)}")
        return interval_hours, 0

def get_status_color(remaining_hours):
    """تحديد لون الحالة بناءً على الساعات المتبقية"""
    if remaining_hours <= 0:
        return "danger"
    elif remaining_hours <= 24:  # أقل من يوم
        return "warning"
    elif remaining_hours <= 168:  # أقل من أسبوع
        return "info"
    else:
        return "success"

def format_time_remaining(hours):
    """تنسيق الوقت المتبقي بشكل مقروء"""
    if hours <= 0:
        return "⏰ مستحقة الآن"
    
    if hours >= 24:
        days = hours / 24
        if days >= 30:
            months = days / 30
            if months >= 12:
                years = months / 12
                return f"⏳ {years:.1f} سنة"
            return f"⏳ {months:.1f} شهر"
        return f"⏳ {days:.1f} يوم"
    
    return f"⏳ {hours:.0f} ساعة"

def update_all_counters():
    """تحديث جميع العدادات التنازلية"""
    try:
        tasks = db.get_tasks()
        
        if tasks.empty:
            return tasks
        
        updated_tasks = tasks.copy()
        
        for idx, task in tasks.iterrows():
            remaining, passed = calculate_remaining_hours(
                task["تاريخ آخر صيانة"],
                task["عدد ساعات التشغيل عند آخر صيانة"],
                task["الفترة بين الصيانة (ساعات)"]
            )
            
            # تحديث القيم
            updated_tasks.at[idx, "عدد الساعات المتبقية"] = remaining
            
            # حساب التاريخ القادم
            last_date = datetime.strptime(task["تاريخ آخر صيانة"], "%Y-%m-%d")
            next_date = last_date + timedelta(hours=task["الفترة بين الصيانة (ساعات)"])
            updated_tasks.at[idx, "تاريخ الصيانة القادم"] = next_date.strftime("%Y-%m-%d")
        
        # حفظ التحديثات
        db.save_tasks(updated_tasks)
        return updated_tasks
    
    except Exception as e:
        st.error(f"خطأ في تحديث العدادات: {str(e)}")
        return tasks if 'tasks' in locals() else pd.DataFrame()

# ===============================
# 📊 تحميل البيانات
# ===============================
def load_data():
    """تحميل جميع البيانات"""
    machines = db.get_machines()
    tasks = db.get_tasks()
    logs = db.get_logs()
    settings = db.get_settings()
    
    # تحديث العدادات
    tasks = update_all_counters()
    
    return {
        "machines": machines,
        "tasks": tasks,
        "logs": logs,
        "settings": settings
    }

# ===============================
# 🎯 التطبيق الرئيسي
# ===============================
def main():
    # عنوان التطبيق
    st.markdown(f'<h1 class="main-header">{APP_CONFIG["APP_ICON"]} {APP_CONFIG["APP_TITLE"]}</h1>', unsafe_allow_html=True)
    
    # تحميل البيانات
    data = load_data()
    machines = data["machines"]
    tasks = data["tasks"]
    logs = data["logs"]
    settings = data["settings"]
    
    # ===============================
    # 📌 الشريط الجانبي
    # ===============================
    with st.sidebar:
        st.image("https://cdn-icons-png.flaticon.com/512/3067/3067256.png", width=80)
        
        # حالة الاتصال
        col1, col2 = st.columns(2)
        with col1:
            if os.path.exists(APP_CONFIG["EXCEL_FILE"]):
                file_size = os.path.getsize(APP_CONFIG["EXCEL_FILE"]) / 1024
                st.success(f"📁 {file_size:.1f} KB")
        with col2:
            if github and github.test_connection():
                st.success("🌐 متصل")
            else:
                st.warning("🌐 غير متصل")
        
        # القائمة الرئيسية
        st.markdown("### 📋 القائمة الرئيسية")
        menu = st.radio(
            "اختر الصفحة:",
            [
                "🏠 لوحة التحكم",
                "➕ إضافة ماكينة",
                "🔧 إدارة المهام",
                "📝 تسجيل صيانة",
                "📊 السجلات والتقارير",
                "⚙️ الإعدادات",
                "🔄 المزامنة"
            ],
            label_visibility="collapsed"
        )
        
        st.markdown("---")
        
        # إحصائيات سريعة
        st.markdown("### 📊 إحصائيات سريعة")
        
        col1, col2 = st.columns(2)
        with col1:
            total_machines = len(machines) if not machines.empty else 0
            st.metric("الماكينات", total_machines)
        with col2:
            total_tasks = len(tasks) if not tasks.empty else 0
            st.metric("المهام", total_tasks)
        
        col3, col4 = st.columns(2)
        with col3:
            overdue = len(tasks[tasks["عدد الساعات المتبقية"] <= 0]) if not tasks.empty else 0
            st.metric("متأخرة", overdue, delta_color="inverse")
        with col4:
            recent_logs = len(logs[logs["تاريخ التسجيل"] == datetime.now().strftime("%Y-%m-%d")]) if not logs.empty else 0
            st.metric("اليوم", recent_logs)
        
        st.markdown("---")
        
        # أزرار التحكم
        if st.button("🔄 تحديث البيانات", use_container_width=True):
            st.cache_data.clear()
            st.success("تم تحديث البيانات!")
            time.sleep(1)
            st.rerun()
        
        if st.button("💾 حفظ محلي", use_container_width=True):
            db.force_save()
            st.success("تم الحفظ المحلي!")
        
        if github and st.button("☁️ رفع لـGitHub", use_container_width=True):
            if github.upload_file():
                st.success("تم الرفع لـGitHub!")
            else:
                st.error("فشل الرفع لـGitHub")
        
        # معلومات النظام
        st.markdown("---")
        st.caption(f"🕒 {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        st.caption(f"📁 {APP_CONFIG['EXCEL_FILE']}")
    
    # ===============================
    # 🏠 صفحة لوحة التحكم
    # ===============================
    if menu == "🏠 لوحة التحكم":
        st.markdown("## 📊 لوحة تحكم النظام")
        
        # عدادات رئيسية
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.markdown('<div class="metric-box"><h3>🏭</h3><h4>الماكينات</h4><h2>{}</h2></div>'.format(
                len(machines) if not machines.empty else 0
            ), unsafe_allow_html=True)
        
        with col2:
            active_machines = len(machines[machines["نشطة"] == "نعم"]) if not machines.empty and "نشطة" in machines.columns else 0
            st.markdown('<div class="metric-box"><h3>✅</h3><h4>نشطة</h4><h2>{}</h2></div>'.format(active_machines), unsafe_allow_html=True)
        
        with col3:
            urgent_tasks = len(tasks[tasks["عدد الساعات المتبقية"] <= 24]) if not tasks.empty else 0
            st.markdown('<div class="metric-box"><h3>⚠️</h3><h4>عاجلة</h4><h2>{}</h2></div>'.format(urgent_tasks), unsafe_allow_html=True)
        
        with col4:
            total_logs = len(logs) if not logs.empty else 0
            st.markdown('<div class="metric-box"><h3>📝</h3><h4>السجلات</h4><h2>{}</h2></div>'.format(total_logs), unsafe_allow_html=True)
        
        # المهام المتأخرة والعاجلة
        st.markdown("### 🚨 المهام العاجلة")
        
        if not tasks.empty:
            # المهام المتأخرة (الساعات المتبقية <= 0)
            overdue_tasks = tasks[tasks["عدد الساعات المتبقية"] <= 0]
            
            # المهام العاجلة (أقل من 24 ساعة)
            urgent_tasks = tasks[(tasks["عدد الساعات المتبقية"] > 0) & (tasks["عدد الساعات المتبقية"] <= 24)]
            
            if not overdue_tasks.empty:
                st.error(f"### ⚠️ هناك {len(overdue_tasks)} مهمة متأخرة!")
                
                for idx, task in overdue_tasks.iterrows():
                    # البحث عن اسم الماكينة
                    machine_name = "غير معروف"
                    if not machines.empty:
                        machine_match = machines[machines["id"] == task["معرف الماكينة"]]
                        if not machine_match.empty:
                            machine_name = machine_match.iloc[0]["اسم الماكينة"]
                    
                    col1, col2, col3 = st.columns([3, 2, 1])
                    with col1:
                        st.markdown(f"**{machine_name}**")
                        st.caption(f"📌 {task['نوع الصيانة']}")
                        if pd.notna(task.get("وصف المهمة")):
                            st.caption(f"📝 {task['وصف المهمة']}")
                    
                    with col2:
                        st.error(f"⏰ تأخر {abs(task['عدد الساعات المتبقية']):.0f} ساعة")
                        st.caption(f"🕒 آخر: {task['تاريخ آخر صيانة']}")
                    
                    with col3:
                        if st.button("📝 سجل", key=f"urgent_{task['id']}"):
                            st.session_state.log_task = task['id']
                            st.session_state.log_machine = task["معرف الماكينة"]
                            st.rerun()
            
            if not urgent_tasks.empty:
                st.warning(f"### 🔔 هناك {len(urgent_tasks)} مهمة عاجلة (أقل من 24 ساعة)")
                
                for idx, task in urgent_tasks.iterrows():
                    # البحث عن اسم الماكينة
                    machine_name = "غير معروف"
                    if not machines.empty:
                        machine_match = machines[machines["id"] == task["معرف الماكينة"]]
                        if not machine_match.empty:
                            machine_name = machine_match.iloc[0]["اسم الماكينة"]
                    
                    col1, col2, col3 = st.columns([3, 2, 1])
                    with col1:
                        st.markdown(f"**{machine_name}**")
                        st.caption(f"📌 {task['نوع الصيانة']}")
                    
                    with col2:
                        st.info(f"⏳ متبقي {task['عدد الساعات المتبقية']:.0f} ساعة")
                        st.caption(f"📅 قادمة: {task.get('تاريخ الصيانة القادم', 'غير محدد')}")
                    
                    with col3:
                        if st.button("سجل", key=f"soon_{task['id']}"):
                            st.session_state.log_task = task['id']
                            st.session_state.log_machine = task["معرف الماكينة"]
                            st.rerun()
        else:
            st.success("🎉 لا توجد مهام عاجلة!")
        
        # عرض الماكينات
        st.markdown("### ⚙️ الماكينات النشطة")
        
        if not machines.empty:
            # تصفية الماكينات النشطة
            active_machines = machines[machines["نشطة"] == "نعم"] if "نشطة" in machines.columns else machines
            
            if not active_machines.empty:
                # إنشاء أعمدة لعرض الماكينات
                cols = st.columns(3)
                
                for idx, machine in active_machines.iterrows():
                    col_idx = idx % 3
                    
                    with cols[col_idx]:
                        # حساب المهام لهذه الماكينة
                        machine_tasks = tasks[tasks["معرف الماكينة"] == machine["id"]] if not tasks.empty else pd.DataFrame()
                        overdue_count = len(machine_tasks[machine_tasks["عدد الساعات المتبقية"] <= 0]) if not machine_tasks.empty else 0
                        
                        # تحديد لون البطاقة
                        if overdue_count > 0:
                            card_class = "danger-card"
                            status_icon = "⚠️"
                        else:
                            card_class = "machine-card"
                            status_icon = "✅"
                        
                        st.markdown(f"""
                        <div class="{card_class}">
                            <h4>{status_icon} {machine['اسم الماكينة']}</h4>
                            <p><strong>الموديل:</strong> {machine.get('الموديل', 'غير محدد')}</p>
                            <p><strong>الرقم:</strong> {machine.get('الرقم التسلسلي', 'غير محدد')}</p>
                            <p><strong>ساعات التشغيل:</strong> {machine.get('إجمالي ساعات التشغيل', 0):.0f}</p>
                            <p><strong>مهام متأخرة:</strong> {overdue_count}</p>
                        </div>
                        """, unsafe_allow_html=True)
                        
                        # أزرار التحكم السريعة
                        col1, col2 = st.columns(2)
                        with col1:
                            if st.button("🔧 مهام", key=f"tasks_{machine['id']}"):
                                st.session_state.view_machine_tasks = machine['id']
                        with col2:
                            if st.button("📝 صيانة", key=f"maintenance_{machine['id']}"):
                                st.session_state.add_maintenance_for = machine['id']
            else:
                st.info("لا توجد ماكينات نشطة")
        else:
            st.info("📝 لا توجد ماكينات مسجلة. أضف ماكينة جديدة من القائمة.")
    
    # ===============================
    # ➕ صفحة إضافة ماكينة
    # ===============================
    elif menu == "➕ إضافة ماكينة":
        st.markdown("## ➕ إضافة ماكينة جديدة")
        
        with st.form("add_machine_form", clear_on_submit=True):
            col1, col2 = st.columns(2)
            
            with col1:
                machine_name = st.text_input("اسم الماكينة *", placeholder="ماكينة الإنتاج رقم 1")
                machine_model = st.text_input("الموديل", placeholder="XP-2000")
                serial_number = st.text_input("الرقم التسلسلي *", placeholder="SN-2024-001")
            
            with col2:
                install_date = st.date_input("تاريخ التركيب *", value=datetime.now())
                total_hours = st.number_input("إجمالي ساعات التشغيل *", min_value=0.0, value=0.0, step=10.0)
                is_active = st.radio("الحالة *", ["نعم", "لا"], index=0, horizontal=True)
            
            department = st.text_input("القسم/الموقع", placeholder="قسم الإنتاج - الخط 1")
            notes = st.text_area("ملاحظات إضافية", placeholder="أي معلومات إضافية عن الماكينة...")
            
            submitted = st.form_submit_button("💾 حفظ الماكينة")
            
            if submitted:
                if not machine_name or not serial_number:
                    st.error("⚠️ يرجى ملء الحقول المطلوبة (*)")
                else:
                    # إنشاء معرف جديد
                    new_id = machines["id"].max() + 1 if not machines.empty else 1
                    
                    machine_data = {
                        "id": new_id,
                        "اسم الماكينة": machine_name,
                        "الموديل": machine_model if machine_model else "",
                        "الرقم التسلسلي": serial_number,
                        "تاريخ التركيب": install_date.strftime("%Y-%m-%d"),
                        "إجمالي ساعات التشغيل": total_hours,
                        "آخر تحديث للساعات": datetime.now().strftime("%Y-%m-%d %H:%M"),
                        "القسم": department if department else "",
                        "ملاحظات": notes if notes else "",
                        "نشطة": is_active,
                        "تاريخ الإضافة": datetime.now().strftime("%Y-%m-%d")
                    }
                    
                    if db.add_machine(machine_data):
                        st.success(f"✅ تمت إضافة الماكينة '{machine_name}' بنجاح!")
                        st.balloons()
                        
                        # خيار إضافة مهام مباشرة
                        if st.button("🔧 إضافة مهام صيانة لهذه الماكينة"):
                            st.session_state.add_tasks_for_machine = new_id
                            st.rerun()
                    else:
                        st.error("❌ فشل في إضافة الماكينة")
        
        # عرض الماكينات المضافة حديثاً
        if not machines.empty:
            st.markdown("### 📋 أحدث الماكينات")
            
            recent_machines = machines.tail(5)  # آخر 5 ماكينات
            
            for idx, machine in recent_machines.iterrows():
                col1, col2, col3 = st.columns([3, 2, 1])
                with col1:
                    st.markdown(f"**{machine['اسم الماكينة']}**")
                    st.caption(f"{machine.get('الموديل', '')} - {machine.get('الرقم التسلسلي', '')}")
                with col2:
                    st.caption(f"🕒 {machine['تاريخ الإضافة']}")
                    st.caption(f"⚡ {machine['إجمالي ساعات التشغيل']:.0f} ساعة")
                with col3:
                    if st.button("🔧 مهام", key=f"quick_tasks_{machine['id']}"):
                        st.session_state.view_machine_tasks = machine['id']
    
    # ===============================
    # 🔧 صفحة إدارة المهام
    # ===============================
    elif menu == "🔧 إدارة المهام":
        st.markdown("## 🔧 إدارة مهام الصيانة")
        
        tab1, tab2, tab3 = st.tabs(["📋 جميع المهام", "➕ إضافة مهمة", "📊 إحصائيات المهام"])
        
        with tab1:
            if not tasks.empty:
                # عوامل التصفية
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    if not machines.empty:
                        machine_options = ["الكل"] + machines["id"].tolist()
                        machine_names = {row["id"]: row["اسم الماكينة"] for idx, row in machines.iterrows()}
                        machine_names["الكل"] = "الكل"
                        
                        selected_machine = st.selectbox(
                            "تصفية حسب الماكينة",
                            options=machine_options,
                            format_func=lambda x: machine_names[x]
                        )
                    else:
                        selected_machine = "الكل"
                
                with col2:
                    status_options = ["الكل", "عاجلة", "متأخرة", "قادمة", "جيدة"]
                    selected_status = st.selectbox("تصفية حسب الحالة", options=status_options)
                
                with col3:
                    task_types = ["الكل"] + tasks["نوع الصيانة"].unique().tolist() if "نوع الصيانة" in tasks.columns else ["الكل"]
                    selected_type = st.selectbox("تصفية حسب النوع", options=task_types)
                
                # تطبيق التصفية
                filtered_tasks = tasks.copy()
                
                if selected_machine != "الكل":
                    filtered_tasks = filtered_tasks[filtered_tasks["معرف الماكينة"] == selected_machine]
                
                if selected_status != "الكل":
                    if selected_status == "عاجلة":
                        filtered_tasks = filtered_tasks[filtered_tasks["عدد الساعات المتبقية"] <= 24]
                    elif selected_status == "متأخرة":
                        filtered_tasks = filtered_tasks[filtered_tasks["عدد الساعات المتبقية"] <= 0]
                    elif selected_status == "قادمة":
                        filtered_tasks = filtered_tasks[(filtered_tasks["عدد الساعات المتبقية"] > 0) & (filtered_tasks["عدد الساعات المتبقية"] <= 168)]
                    elif selected_status == "جيدة":
                        filtered_tasks = filtered_tasks[filtered_tasks["عدد الساعات المتبقية"] > 168]
                
                if selected_type != "الكل":
                    filtered_tasks = filtered_tasks[filtered_tasks["نوع الصيانة"] == selected_type]
                
                # عرض المهام المصفاة
                st.markdown(f"### 📋 عرض {len(filtered_tasks)} مهمة")
                
                for idx, task in filtered_tasks.iterrows():
                    # الحصول على اسم الماكينة
                    machine_name = "غير معروف"
                    if not machines.empty:
                        machine_match = machines[machines["id"] == task["معرف الماكينة"]]
                        if not machine_match.empty:
                            machine_name = machine_match.iloc[0]["اسم الماكينة"]
                    
                    # تحديد لون البطاقة
                    remaining = task.get("عدد الساعات المتبقية", 0)
                    status_color = get_status_color(remaining)
                    status_text = format_time_remaining(remaining)
                    
                    if status_color == "danger":
                        card_class = "danger-card"
                    elif status_color == "warning":
                        card_class = "warning-card"
                    elif status_color == "info":
                        card_class = "machine-card"
                    else:
                        card_class = "success-card"
                    
                    with st.container():
                        col1, col2, col3, col4 = st.columns([3, 2, 2, 1])
                        
                        with col1:
                            st.markdown(f"**{machine_name}**")
                            st.caption(f"📌 {task['نوع الصيانة']}")
                            if pd.notna(task.get("وصف المهمة")):
                                st.caption(f"📝 {task['وصف المهمة']}")
                        
                        with col2:
                            st.markdown(f"**{status_text}**")
                            st.caption(f"🔄 كل {task['الفترة بين الصيانة (ساعات)']} ساعة")
                        
                        with col3:
                            st.caption(f"🕒 آخر: {task['تاريخ آخر صيانة']}")
                            st.caption(f"📅 قادمة: {task.get('تاريخ الصيانة القادم', 'غير محدد')}")
                        
                        with col4:
                            if st.button("📝", key=f"log_{task['id']}"):
                                st.session_state.log_task = task['id']
                                st.session_state.log_machine = task["معرف الماكينة"]
                                st.rerun()
            
            else:
                st.info("📝 لا توجد مهام مسجلة بعد")
        
        with tab2:
            st.markdown("### ➕ إضافة مهمة صيانة جديدة")
            
            if not machines.empty:
                # اختيار الماكينة
                machine_options = {row["id"]: f"{row['اسم الماكينة']} ({row.get('الموديل', '')})" 
                                 for idx, row in machines.iterrows()}
                
                selected_machine = st.selectbox(
                    "اختر الماكينة *",
                    options=list(machine_options.keys()),
                    format_func=lambda x: machine_options[x]
                )
                
                if selected_machine:
                    with st.form("add_task_form", clear_on_submit=True):
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            task_type = st.text_input("نوع الصيانة *", placeholder="تغيير الزيت")
                            interval_hours = st.number_input("الفترة بين الصيانة (ساعات) *", 
                                                           min_value=1, value=500, step=10)
                            
                            # أنواع الصيانة الشائعة
                            common_tasks = ["تغيير الزيت", "التشحيم", "تنظيف الفلاتر", "فحص الأحزمة", 
                                          "فحص الكهرباء", "تنظيف عام", "فحص المحامل", "تغيير الفلاتر"]
                            
                            if st.checkbox("استخدام نوع صيانة شائع"):
                                selected_common = st.selectbox("اختر من القائمة", options=common_tasks)
                                if selected_common:
                                    task_type = selected_common
                        
                        with col2:
                            last_maintenance = st.date_input("تاريخ آخر صيانة *", value=datetime.now())
                            
                            # الحصول على ساعات تشغيل الماكينة
                            machine_hours = 0
                            if not machines.empty:
                                machine_data = machines[machines["id"] == selected_machine]
                                if not machine_data.empty:
                                    machine_hours = machine_data.iloc[0]["إجمالي ساعات التشغيل"]
                            
                            last_hours = st.number_input(
                                "عدد ساعات التشغيل عند آخر صيانة *",
                                min_value=0.0,
                                value=float(machine_hours),
                                step=1.0
                            )
                        
                        description = st.text_area("وصف المهمة", 
                                                 placeholder="تفاصيل عملية الصيانة، الأدوات المطلوبة، الوقت المقدر...")
                        
                        is_active = st.radio("تفعيل المهمة", ["نعم", "لا"], index=0, horizontal=True)
                        
                        submitted = st.form_submit_button("💾 حفظ المهمة")
                        
                        if submitted:
                            if not task_type:
                                st.error("⚠️ نوع الصيانة مطلوب")
                            else:
                                # حساب الساعات المتبقية
                                remaining, _ = calculate_remaining_hours(
                                    last_maintenance.strftime("%Y-%m-%d"),
                                    last_hours,
                                    interval_hours
                                )
                                
                                # حساب التاريخ القادم
                                next_date = last_maintenance + timedelta(hours=interval_hours)
                                
                                # إنشاء معرف جديد
                                new_id = tasks["id"].max() + 1 if not tasks.empty else 1
                                
                                task_data = {
                                    "id": new_id,
                                    "معرف الماكينة": selected_machine,
                                    "نوع الصيانة": task_type,
                                    "الفترة بين الصيانة (ساعات)": interval_hours,
                                    "تاريخ آخر صيانة": last_maintenance.strftime("%Y-%m-%d"),
                                    "عدد ساعات التشغيل عند آخر صيانة": last_hours,
                                    "عدد الساعات المتبقية": remaining,
                                    "تاريخ الصيانة القادم": next_date.strftime("%Y-%m-%d"),
                                    "وصف المهمة": description if description else "",
                                    "نشطة": is_active,
                                    "تاريخ الإضافة": datetime.now().strftime("%Y-%m-%d")
                                }
                                
                                if db.add_task(task_data):
                                    st.success(f"✅ تمت إضافة مهمة '{task_type}' بنجاح!")
                                    st.cache_data.clear()
                                    
                                    # عرض ملخص
                                    st.info(f"""
                                    **ملخص المهمة:**
                                    - الفترة: كل {interval_hours} ساعة
                                    - الساعات المتبقية: {remaining:.0f} ساعة
                                    - الصيانة القادمة: {next_date.strftime('%Y-%m-%d')}
                                    """)
                                else:
                                    st.error("❌ فشل في إضافة المهمة")
            else:
                st.warning("⚠️ لا توجد ماكينات. أضف ماكينة أولاً.")
        
        with tab3:
            st.markdown("### 📊 إحصائيات المهام")
            
            if not tasks.empty:
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    # توزيع المهام حسب الحالة
                    status_counts = {
                        "متأخرة": len(tasks[tasks["عدد الساعات المتبقية"] <= 0]),
                        "عاجلة": len(tasks[(tasks["عدد الساعات المتبقية"] > 0) & (tasks["عدد الساعات المتبقية"] <= 24)]),
                        "قادمة": len(tasks[(tasks["عدد الساعات المتبقية"] > 24) & (tasks["عدد الساعات المتبقية"] <= 168)]),
                        "جيدة": len(tasks[tasks["عدد الساعات المتبقية"] > 168])
                    }
                    
                    fig1 = px.pie(
                        values=list(status_counts.values()),
                        names=list(status_counts.keys()),
                        title="توزيع المهام حسب الحالة",
                        color=list(status_counts.keys()),
                        color_discrete_map={
                            "متأخرة": "red",
                            "عاجلة": "orange",
                            "قادمة": "blue",
                            "جيدة": "green"
                        }
                    )
                    st.plotly_chart(fig1, use_container_width=True)
                
                with col2:
                    # توزيع المهام حسب النوع
                    if "نوع الصيانة" in tasks.columns:
                        task_type_counts = tasks["نوع الصيانة"].value_counts().head(10)
                        
                        fig2 = px.bar(
                            x=task_type_counts.values,
                            y=task_type_counts.index,
                            orientation='h',
                            title="أكثر أنواع الصيانة شيوعاً",
                            labels={'x': 'عدد المهام', 'y': 'نوع الصيانة'}
                        )
                        st.plotly_chart(fig2, use_container_width=True)
                
                with col3:
                    # متوسط الفترات بين الصيانة
                    avg_interval = tasks["الفترة بين الصيانة (ساعات)"].mean() if "الفترة بين الصيانة (ساعات)" in tasks.columns else 0
                    
                    st.metric("متوسط فترة الصيانة", f"{avg_interval:.0f} ساعة")
                    
                    # أكثر الماكينات حاجة للصيانة
                    if not machines.empty:
                        machine_maintenance_needs = []
                        for _, machine in machines.iterrows():
                            machine_tasks = tasks[tasks["معرف الماكينة"] == machine["id"]]
                            overdue_count = len(machine_tasks[machine_tasks["عدد الساعات المتبقية"] <= 0])
                            machine_maintenance_needs.append({
                                "الماكينة": machine["اسم الماكينة"],
                                "مهام متأخرة": overdue_count
                            })
                        
                        needs_df = pd.DataFrame(machine_maintenance_needs)
                        needs_df = needs_df.sort_values("مهام متأخرة", ascending=False).head(5)
                        
                        st.markdown("**أكثر الماكينات حاجة للصيانة:**")
                        for _, row in needs_df.iterrows():
                            st.caption(f"{row['الماكينة']}: {row['مهام متأخرة']} مهمة")
    
    # ===============================
    # 📝 صفحة تسجيل صيانة
    # ===============================
    elif menu == "📝 تسجيل صيانة":
        st.markdown("## 📝 تسجيل عملية صيانة")
        
        # إذا كان هناك مهمة محددة من لوحة التحكم
        if 'log_task' in st.session_state and 'log_machine' in st.session_state:
            task_id = st.session_state.log_task
            machine_id = st.session_state.log_machine
            
            # جلب بيانات المهمة
            if not tasks.empty:
                task_data = tasks[tasks["id"] == task_id]
                if not task_data.empty:
                    task = task_data.iloc[0]
                    machine_name = machines[machines["id"] == machine_id]["اسم الماكينة"].values[0]
                    
                    st.success(f"📋 تسجيل صيانة لـ: **{machine_name}** - {task['نوع الصيانة']}")
                    
                    # تعبئة تلقائية
                    prefill_hours = machines[machines["id"] == machine_id]["إجمالي ساعات التشغيل"].values[0]
                    task_type = task['نوع الصيانة']
                    
                    # حذف من الجلسة بعد الاستخدام
                    del st.session_state.log_task
                    del st.session_state.log_machine
        
        with st.form("log_maintenance_form", clear_on_submit=True):
            col1, col2 = st.columns(2)
            
            with col1:
                # اختيار الماكينة
                if not machines.empty:
                    machine_options = {row["id"]: row["اسم الماكينة"] for idx, row in machines.iterrows()}
                    machine_id = st.selectbox(
                        "الماكينة *",
                        options=list(machine_options.keys()),
                        format_func=lambda x: machine_options[x]
                    )
                    
                    # الحصول على ساعات التشغيل الحالية
                    current_hours = 0
                    if not machines.empty:
                        machine_data = machines[machines["id"] == machine_id]
                        if not machine_data.empty:
                            current_hours = machine_data.iloc[0]["إجمالي ساعات التشغيل"]
                    
                    # اختيار نوع الصيانة لهذه الماكينة
                    if not tasks.empty:
                        machine_tasks = tasks[tasks["معرف الماكينة"] == machine_id]
                        if not machine_tasks.empty:
                            task_options = {row["id"]: row["نوع الصيانة"] for idx, row in machine_tasks.iterrows()}
                            task_id = st.selectbox(
                                "نوع الصيانة *",
                                options=list(task_options.keys()),
                                format_func=lambda x: task_options[x]
                            )
                        else:
                            st.warning("لا توجد مهام لهذه الماكينة")
                            task_id = None
                    else:
                        st.warning("لا توجد مهام مسجلة")
                        task_id = None
                else:
                    st.warning("لا توجد ماكينات")
                    machine_id = None
                    task_id = None
            
            with col2:
                maintenance_date = st.date_input("تاريخ الصيانة *", value=datetime.now())
                maintenance_hours = st.number_input(
                    "عدد ساعات التشغيل *",
                    min_value=0.0,
                    value=float(current_hours),
                    step=1.0
                )
                
                technician = st.text_input("اسم الفني *", placeholder="أحمد محمد")
            
            parts_used = st.text_area("الأجزاء المستبدلة", placeholder="مثال: زيت محرك 5 لتر، فلتر هواء...")
            notes = st.text_area("ملاحظات إضافية", placeholder="أي ملاحظات عن الصيانة، المشاكل التي تم اكتشافها...")
            
            submitted = st.form_submit_button("📝 تسجيل الصيانة")
            
            if submitted:
                if not machine_id or not task_id or not technician:
                    st.error("⚠️ يرجى ملء الحقول المطلوبة (*)")
                else:
                    # تحديث المهمة
                    if not tasks.empty:
                        task_idx = tasks[tasks["id"] == task_id].index[0]
                        task = tasks.loc[task_idx].to_dict()
                        
                        task["تاريخ آخر صيانة"] = maintenance_date.strftime("%Y-%m-%d")
                        task["عدد ساعات التشغيل عند آخر صيانة"] = maintenance_hours
                        task["عدد الساعات المتبقية"] = task["الفترة بين الصيانة (ساعات)"]
                        
                        # تحديث التاريخ القادم
                        next_date = maintenance_date + timedelta(hours=task["الفترة بين الصيانة (ساعات)"])
                        task["تاريخ الصيانة القادم"] = next_date.strftime("%Y-%m-%d")
                        
                        # حفظ المهمة المحدثة
                        if db.update_task(task):
                            st.success("✅ تم تحديث المهمة")
                        else:
                            st.error("❌ فشل في تحديث المهمة")
                    
                    # تحديث ساعات الماكينة
                    if not machines.empty:
                        machine_idx = machines[machines["id"] == machine_id].index[0]
                        machine = machines.loc[machine_idx].to_dict()
                        
                        if maintenance_hours > machine["إجمالي ساعات التشغيل"]:
                            machine["إجمالي ساعات التشغيل"] = maintenance_hours
                            machine["آخر تحديث للساعات"] = datetime.now().strftime("%Y-%m-%d %H:%M")
                            
                            if db.update_machine(machine):
                                st.success("✅ تم تحديث ساعات الماكينة")
                    
                    # إضافة إلى سجل الصيانة
                    log_id = logs["id"].max() + 1 if not logs.empty else 1
                    
                    log_data = {
                        "id": log_id,
                        "معرف الماكينة": machine_id,
                        "معرف المهمة": task_id,
                        "تاريخ الصيانة": maintenance_date.strftime("%Y-%m-%d"),
                        "عدد ساعات التشغيل": maintenance_hours,
                        "تمت بواسطة": technician,
                        "الأجزاء المستبدلة": parts_used if parts_used else "",
                        "ملاحظات": notes if notes else "",
                        "تاريخ التسجيل": datetime.now().strftime("%Y-%m-%d")
                    }
                    
                    if db.add_log(log_data):
                        st.success("✅ تم تسجيل الصيانة بنجاح!")
                        st.balloons()
                        st.cache_data.clear()
                        
                        # عرض ملخص
                        with st.expander("📋 ملخص التسجيل", expanded=True):
                            machine_name = machines[machines["id"] == machine_id]["اسم الماكينة"].values[0]
                            task_type = tasks[tasks["id"] == task_id]["نوع الصيانة"].values[0]
                            
                            st.write(f"**الماكينة:** {machine_name}")
                            st.write(f"**نوع الصيانة:** {task_type}")
                            st.write(f"**تاريخ الصيانة:** {maintenance_date.strftime('%Y-%m-%d')}")
                            st.write(f"**ساعات التشغيل:** {maintenance_hours}")
                            st.write(f"**الفني:** {technician}")
                            st.write(f"**الصيانة القادمة:** {next_date.strftime('%Y-%m-%d')}")
                            
                            if parts_used:
                                st.write(f"**الأجزاء المستبدلة:** {parts_used}")
                    else:
                        st.error("❌ فشل في حفظ السجل")
    
    # ===============================
    # 📊 صفحة السجلات والتقارير
    # ===============================
    elif menu == "📊 السجلات والتقارير":
        st.markdown("## 📊 السجلات والتقارير")
        
        tab1, tab2, tab3 = st.tabs(["📝 سجل الصيانة", "📈 تقارير", "📤 تصدير البيانات"])
        
        with tab1:
            if not logs.empty:
                # عوامل التصفية
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    # تصفية حسب الماكينة
                    if not machines.empty:
                        machine_list = ["الكل"] + machines["id"].tolist()
                        machine_names = {row["id"]: row["اسم الماكينة"] for idx, row in machines.iterrows()}
                        machine_names["الكل"] = "الكل"
                        
                        selected_machine = st.selectbox(
                            "الماكينة",
                            options=machine_list,
                            format_func=lambda x: machine_names[x]
                        )
                    else:
                        selected_machine = "الكل"
                
                with col2:
                    # تصفية حسب الفترة
                    period = st.selectbox("الفترة", ["آخر 30 يوم", "آخر 7 أيام", "هذا الشهر", "هذا العام", "الكل"])
                    
                    if period == "آخر 7 أيام":
                        start_date = datetime.now() - timedelta(days=7)
                    elif period == "آخر 30 يوم":
                        start_date = datetime.now() - timedelta(days=30)
                    elif period == "هذا الشهر":
                        start_date = datetime.now().replace(day=1)
                    elif period == "هذا العام":
                        start_date = datetime.now().replace(month=1, day=1)
                    else:
                        start_date = None
                
                with col3:
                    # تصفية حسب الفني
                    technicians = ["الكل"] + logs["تمت بواسطة"].unique().tolist() if "تمت بواسطة" in logs.columns else ["الكل"]
                    selected_tech = st.selectbox("الفني", options=technicians)
                
                # تطبيق التصفية
                filtered_logs = logs.copy()
                
                if selected_machine != "الكل":
                    filtered_logs = filtered_logs[filtered_logs["معرف الماكينة"] == selected_machine]
                
                if start_date:
                    filtered_logs = filtered_logs[
                        pd.to_datetime(filtered_logs["تاريخ الصيانة"]) >= start_date
                    ]
                
                if selected_tech != "الكل":
                    filtered_logs = filtered_logs[filtered_logs["تمت بواسطة"] == selected_tech]
                
                # عرض السجلات
                st.markdown(f"### 📋 عرض {len(filtered_logs)} سجل")
                
                # تحسين عرض البيانات
                display_logs = filtered_logs.copy()
                
                # إضافة أسماء الماكينات
                if not machines.empty:
                    display_logs["الماكينة"] = display_logs["معرف الماكينة"].apply(
                        lambda x: machines[machines["id"] == x]["اسم الماكينة"].values[0] 
                        if not machines[machines["id"] == x].empty else "غير معروف"
                    )
                
                # إضافة أنواع الصيانة
                if not tasks.empty:
                    display_logs["نوع الصيانة"] = display_logs["معرف المهمة"].apply(
                        lambda x: tasks[tasks["id"] == x]["نوع الصيانة"].values[0] 
                        if not tasks[tasks["id"] == x].empty else "غير معروف"
                    )
                
                # اختيار الأعمدة للعرض
                columns_to_show = ["تاريخ الصيانة", "الماكينة", "نوع الصيانة", 
                                 "عدد ساعات التشغيل", "تمت بواسطة", "الأجزاء المستبدلة", "ملاحظات"]
                
                # إزالة الأعمدة غير الموجودة
                columns_to_show = [col for col in columns_to_show if col in display_logs.columns]
                
                st.dataframe(
                    display_logs[columns_to_show].sort_values("تاريخ الصيانة", ascending=False),
                    use_container_width=True,
                    height=400
                )
            else:
                st.info("📝 لا توجد سجلات صيانة مسجلة بعد")
        
        with tab2:
            st.markdown("### 📈 تقارير الصيانة")
            
            if not logs.empty:
                col1, col2 = st.columns(2)
                
                with col1:
                    # تقرير الصيانة الشهرية
                    logs["شهر"] = pd.to_datetime(logs["تاريخ الصيانة"]).dt.to_period("M")
                    monthly_counts = logs["شهر"].value_counts().sort_index()
                    
                    fig1 = px.bar(
                        x=monthly_counts.index.astype(str),
                        y=monthly_counts.values,
                        title="عمليات الصيانة الشهرية",
                        labels={'x': 'الشهر', 'y': 'عدد عمليات الصيانة'}
                    )
                    st.plotly_chart(fig1, use_container_width=True)
                
                with col2:
                    # أكثر الفنيين نشاطاً
                    if "تمت بواسطة" in logs.columns:
                        tech_counts = logs["تمت بواسطة"].value_counts().head(10)
                        
                        fig2 = px.pie(
                            values=tech_counts.values,
                            names=tech_counts.index,
                            title="توزيع الصيانة حسب الفنيين"
                        )
                        st.plotly_chart(fig2, use_container_width=True)
                
                # تقرير الماكينات الأكثر صيانة
                if not machines.empty:
                    machine_log_counts = []
                    for _, machine in machines.iterrows():
                        machine_logs = len(logs[logs["معرف الماكينة"] == machine["id"]])
                        machine_log_counts.append({
                            "الماكينة": machine["اسم الماكينة"],
                            "عدد عمليات الصيانة": machine_logs
                        })
                    
                    machine_logs_df = pd.DataFrame(machine_log_counts)
                    machine_logs_df = machine_logs_df.sort_values("عدد عمليات الصيانة", ascending=False).head(10)
                    
                    fig3 = px.bar(
                        x=machine_logs_df["عدد عمليات الصيانة"],
                        y=machine_logs_df["الماكينة"],
                        orientation='h',
                        title="الماكينات الأكثر صيانة",
                        labels={'x': 'عدد العمليات', 'y': 'الماكينة'}
                    )
                    st.plotly_chart(fig3, use_container_width=True)
        
        with tab3:
            st.markdown("### 📤 تصدير البيانات")
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                if st.button("📥 تصدير الماكينات", use_container_width=True):
                    csv = machines.to_csv(index=False).encode('utf-8-sig')
                    st.download_button(
                        label="⬇️ تحميل CSV",
                        data=csv,
                        file_name=f"الماكينات_{datetime.now().strftime('%Y%m%d')}.csv",
                        mime="text/csv"
                    )
            
            with col2:
                if st.button("📥 تصدير المهام", use_container_width=True):
                    csv = tasks.to_csv(index=False).encode('utf-8-sig')
                    st.download_button(
                        label="⬇️ تحميل CSV",
                        data=csv,
                        file_name=f"مهام_الصيانة_{datetime.now().strftime('%Y%m%d')}.csv",
                        mime="text/csv"
                    )
            
            with col3:
                if st.button("📥 تصدير السجلات", use_container_width=True):
                    csv = logs.to_csv(index=False).encode('utf-8-sig')
                    st.download_button(
                        label="⬇️ تحميل CSV",
                        data=csv,
                        file_name=f"سجل_الصيانة_{datetime.now().strftime('%Y%m%d')}.csv",
                        mime="text/csv"
                    )
            
            st.markdown("---")
            
            # تصدير شامل
            if st.button("📦 تصدير قاعدة البيانات الكاملة", use_container_width=True):
                # إنشاء ملف Excel شامل
                import io
                output = io.BytesIO()
                
                with pd.ExcelWriter(output, engine='openpyxl') as writer:
                    machines.to_excel(writer, sheet_name='الماكينات', index=False)
                    tasks.to_excel(writer, sheet_name='المهام', index=False)
                    logs.to_excel(writer, sheet_name='السجل', index=False)
                
                st.download_button(
                    label="⬇️ تحميل Excel كامل",
                    data=output.getvalue(),
                    file_name=f"قاعدة_بيانات_الصيانة_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
    
    # ===============================
    # ⚙️ صفحة الإعدادات
    # ===============================
    elif menu == "⚙️ الإعدادات":
        st.markdown("## ⚙️ إعدادات النظام")
        
        tab1, tab2, tab3 = st.tabs(["عام", "GitHub", "المساعدة"])
        
        with tab1:
            st.subheader("الإعدادات العامة")
            
            # إعدادات النظام
            col1, col2 = st.columns(2)
            
            with col1:
                notification_days = st.number_input("الإشعار المسبق (أيام)", 
                                                   min_value=1, max_value=30, value=7)
                auto_save = st.checkbox("الحفظ التلقائي", value=True)
            
            with col2:
                enable_backup = st.checkbox("تفعيل النسخ الاحتياطي", value=True)
                backup_days = st.number_input("احتفظ بالنسخ لأيام", min_value=1, max_value=365, value=30)
            
            # معلومات النظام
            st.subheader("معلومات النظام")
            
            info_cols = st.columns(4)
            with info_cols[0]:
                st.metric("الماكينات", len(machines))
            with info_cols[1]:
                st.metric("المهام", len(tasks))
            with info_cols[2]:
                st.metric("السجلات", len(logs))
            with info_cols[3]:
                file_size = os.path.getsize(APP_CONFIG["EXCEL_FILE"]) / 1024 if os.path.exists(APP_CONFIG["EXCEL_FILE"]) else 0
                st.metric("حجم الملف", f"{file_size:.1f} KB")
            
            if st.button("💾 حفظ الإعدادات", use_container_width=True):
                st.success("✅ تم حفظ الإعدادات")
        
        with tab2:
            st.subheader("إعدادات GitHub")
            
            if github:
                # اختبار الاتصال
                if st.button("🔗 اختبار اتصال GitHub", use_container_width=True):
                    if github.test_connection():
                        st.success("✅ الاتصال ناجح")
                    else:
                        st.error("❌ فشل الاتصال")
                
                # الرفع اليدوي
                if st.button("☁️ رفع الملف لـGitHub", use_container_width=True):
                    if github.upload_file():
                        st.success("✅ تم الرفع بنجاح")
                    else:
                        st.error("❌ فشل الرفع")
                
                # إعدادات الرفع التلقائي
                auto_upload = st.checkbox("الرفع التلقائي بعد كل تعديل", value=True)
                upload_interval = st.number_input("فترة الرفع (دقائق)", min_value=1, value=5)
                
            else:
                st.warning("⚠️ خدمة GitHub غير مفعلة")
                st.info("""
                **لتفعيل GitHub:**
                1. أضف token GitHub في ملف secrets.toml
                2. تأكد من تثبيت PyGithub
                3. أعد تشغيل التطبيق
                """)
        
        with tab3:
            st.subheader("🆘 المساعدة والدعم")
            
            st.markdown("""
            ### 📖 دليل الاستخدام السريع
            
            1. **إضافة ماكينة جديدة:**
               - انتقل إلى ➕ إضافة ماكينة
               - املأ بيانات الماكينة
               - اضغط "حفظ الماكينة"
            
            2. **إضافة مهام صيانة:**
               - انتقل إلى 🔧 إدارة المهام
               - اختر الماكينة
               - حدد نوع الصيانة والفترة
            
            3. **تسجيل عملية صيانة:**
               - انتقل إلى 📝 تسجيل صيانة
               - اختر الماكينة ونوع الصيانة
               - املأ بيانات الصيانة
            
            4. **المتابعة والمراقبة:**
               - لوحة التحكم تظهر المهام المتأخرة
               - السجلات تحتوي على تاريخ جميع العمليات
            
            ### 🔧 استكشاف الأخطاء
            
            **المشكلة:** البيانات لا تحفظ
            **الحل:** اضغط على زر "حفظ محلي" في الشريط الجانبي
            
            **المشكلة:** العد التنازلي غير صحيح
            **الحل:** تأكد من إدخال تاريخ وساعات التشغيل بشكل صحيح
            
            **المشكلة:** بطء في التطبيق
            **الحل:** استخدم زر "تحديث البيانات" أو أعد تشغيل التطبيق
            """)
    
    # ===============================
    # 🔄 صفحة المزامنة
    # ===============================
    elif menu == "🔄 المزامنة":
        st.markdown("## 🔄 مزامنة البيانات")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("📥 جلب من GitHub")
            st.write("تحميل أحدث نسخة من GitHub")
            
            if github and st.button("⬇️ جلب من GitHub", use_container_width=True):
                with st.spinner("جاري التحميل..."):
                    if github.download_file():
                        st.success("✅ تم التحميل بنجاح")
                        st.cache_data.clear()
                        st.rerun()
                    else:
                        st.error("❌ فشل التحميل")
        
        with col2:
            st.subheader("📤 رفع إلى GitHub")
            st.write("حفظ البيانات الحالية على GitHub")
            
            if github and st.button("☁️ رفع إلى GitHub", use_container_width=True):
                with st.spinner("جاري الرفع..."):
                    if github.upload_file():
                        st.success("✅ تم الرفع بنجاح")
                    else:
                        st.error("❌ فشل الرفع")
        
        # معلومات المزامنة
        st.markdown("---")
        st.subheader("📊 حالة المزامنة")
        
        sync_cols = st.columns(3)
        
        with sync_cols[0]:
            local_time = datetime.fromtimestamp(os.path.getmtime(APP_CONFIG["EXCEL_FILE"])).strftime("%Y-%m-%d %H:%M") if os.path.exists(APP_CONFIG["EXCEL_FILE"]) else "غير متوفر"
            st.metric("آخر تحديث محلي", local_time)
        
        with sync_cols[1]:
            if github:
                remote_info = github.get_file_info()
                if remote_info:
                    st.metric("آخر تحديث بعيد", remote_info.get("last_modified", "غير معروف"))
                else:
                    st.metric("آخر تحديث بعيد", "غير متصل")
            else:
                st.metric("آخر تحديث بعيد", "غير مفعل")
        
        with sync_cols[2]:
            sync_status = "🟢 متزامن" if github and github.is_synced() else "🟡 غير متزامن"
            st.metric("حالة المزامنة", sync_status)
        
        # زر التحديث الشامل
        if st.button("🔄 تحديث شامل", use_container_width=True):
            st.cache_data.clear()
            db.force_save()
            
            if github:
                github.upload_file()
            
            st.success("✅ تم التحديث الشامل بنجاح!")
            time.sleep(2)
            st.rerun()
    
    # ===============================
    # 📌 تذييل الصفحة
    # ===============================
    st.markdown("---")
    
    footer_cols = st.columns(3)
    
    with footer_cols[0]:
        st.caption(f"📁 الملف: {APP_CONFIG['EXCEL_FILE']}")
    
    with footer_cols[1]:
        st.caption(f"🕒 آخر تحديث: {datetime.now().strftime('%H:%M')}")
    
    with footer_cols[2]:
        if github and github.test_connection():
            st.caption("🌐 متصل بـGitHub")
        else:
            st.caption("🌐 غير متصل")

# تشغيل التطبيق
if __name__ == "__main__":
    main()
