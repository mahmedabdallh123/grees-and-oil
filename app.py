import streamlit as st
import pandas as pd
import os
import requests
import base64
from datetime import datetime, timedelta
import plotly.express as px
import time
import json
from io import BytesIO

# ===============================
# ⚙ إعدادات التطبيق
# ===============================
APP_CONFIG = {
    "APP_TITLE": "سيرفيس تحضيرات بيل يارن 1 🏭",
    "APP_ICON": "⚙️",
    "EXCEL_FILE": "machines.xlsx",  # ملف Excel المحلي
    "GITHUB_REPO": "mahmedabdallh123/CARD-ANALYSIS",
    "GITHUB_FILE": "machines.xlsx",  # نفس اسم الملف المحلي
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
        background: linear-gradient(135deg, #1E3A8A 0%, #2D4F9C 100%);
        color: white;
        border-radius: 10px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    .stButton > button {
        width: 100%;
        background: linear-gradient(135deg, #1E3A8A 0%, #2D4F9C 100%);
        color: white;
        border: none;
        padding: 0.75rem;
        border-radius: 8px;
        font-weight: bold;
        font-size: 1rem;
        transition: all 0.3s;
    }
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 12px rgba(0,0,0,0.2);
    }
    .success-box {
        background-color: #d4edda;
        border: 1px solid #c3e6cb;
        border-radius: 8px;
        padding: 15px;
        margin: 10px 0;
    }
    .warning-box {
        background-color: #fff3cd;
        border: 1px solid #ffeaa7;
        border-radius: 8px;
        padding: 15px;
        margin: 10px 0;
    }
    .metric-card {
        background: white;
        padding: 20px;
        border-radius: 10px;
        box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        text-align: center;
        margin: 5px;
    }
    .machine-card {
        background: white;
        padding: 15px;
        border-radius: 8px;
        box-shadow: 0 2px 5px rgba(0,0,0,0.1);
        margin: 10px 0;
        border-left: 5px solid #1E3A8A;
    }
</style>
""", unsafe_allow_html=True)

# ===============================
# 🗄 نظام Excel البسيط
# ===============================
class ExcelSystem:
    def __init__(self):
        self.excel_file = APP_CONFIG["EXCEL_FILE"]
        self.setup_excel()
    
    def setup_excel(self):
        """إنشاء ملف Excel جديد إذا لم يكن موجوداً"""
        if not os.path.exists(self.excel_file):
            # إنشاء DataFrame فارغ
            machines_df = pd.DataFrame(columns=[
                'id', 'اسم الماكينة', 'الموديل', 'الرقم التسلسلي',
                'تاريخ التركيب', 'إجمالي ساعات التشغيل',
                'القسم', 'ملاحظات', 'نشطة', 'تاريخ الإضافة'
            ])
            
            tasks_df = pd.DataFrame(columns=[
                'id', 'معرف الماكينة', 'نوع الصيانة', 'الفترة بين الصيانة (ساعات)',
                'تاريخ آخر صيانة', 'عدد ساعات التشغيل عند آخر صيانة',
                'عدد الساعات المتبقية', 'تاريخ الصيانة القادم',
                'وصف المهمة', 'نشطة', 'تاريخ الإضافة'
            ])
            
            logs_df = pd.DataFrame(columns=[
                'id', 'معرف الماكينة', 'معرف المهمة', 'تاريخ الصيانة',
                'عدد ساعات التشغيل', 'تمت بواسطة', 'الأجزاء المستبدلة',
                'ملاحظات', 'تاريخ التسجيل'
            ])
            
            # حفظ في Excel
            with pd.ExcelWriter(self.excel_file, engine='openpyxl') as writer:
                machines_df.to_excel(writer, sheet_name='الماكينات', index=False)
                tasks_df.to_excel(writer, sheet_name='المهام', index=False)
                logs_df.to_excel(writer, sheet_name='السجل', index=False)
            
            st.success(f"✅ تم إنشاء ملف Excel جديد: {self.excel_file}")
    
    def load_sheet(self, sheet_name):
        """تحميل ورقة من Excel"""
        try:
            if os.path.exists(self.excel_file):
                df = pd.read_excel(self.excel_file, sheet_name=sheet_name)
                return df
            return pd.DataFrame()
        except:
            return pd.DataFrame()
    
    def save_sheet(self, sheet_name, df):
        """حفظ ورقة في Excel"""
        try:
            # إذا الملف موجود، نحفظ جميع الأوراق
            if os.path.exists(self.excel_file):
                with pd.ExcelFile(self.excel_file, engine='openpyxl') as xls:
                    sheet_names = xls.sheet_names
                
                with pd.ExcelWriter(self.excel_file, engine='openpyxl') as writer:
                    for sheet in sheet_names:
                        if sheet == sheet_name:
                            df.to_excel(writer, sheet_name=sheet_name, index=False)
                        else:
                            old_df = pd.read_excel(self.excel_file, sheet_name=sheet)
                            old_df.to_excel(writer, sheet_name=sheet, index=False)
            else:
                # إنشاء ملف جديد
                with pd.ExcelWriter(self.excel_file, engine='openpyxl') as writer:
                    df.to_excel(writer, sheet_name=sheet_name, index=False)
            
            return True
        except Exception as e:
            st.error(f"❌ خطأ في حفظ البيانات: {str(e)}")
            return False
    
    def add_machine(self, machine_data):
        """إضافة ماكينة جديدة"""
        machines = self.load_sheet('الماكينات')
        
        # إنشاء معرف جديد
        new_id = machines['id'].max() + 1 if not machines.empty and 'id' in machines.columns else 1
        
        # إضافة البيانات
        machine_data['id'] = new_id
        machine_data['تاريخ الإضافة'] = datetime.now().strftime('%Y-%m-%d %H:%M')
        
        new_df = pd.DataFrame([machine_data])
        machines = pd.concat([machines, new_df], ignore_index=True)
        
        # حفظ
        if self.save_sheet('الماكينات', machines):
            return True, new_id
        return False, None
    
    def add_task(self, task_data):
        """إضافة مهمة صيانة جديدة"""
        tasks = self.load_sheet('المهام')
        
        # إنشاء معرف جديد
        new_id = tasks['id'].max() + 1 if not tasks.empty and 'id' in tasks.columns else 1
        
        # إضافة البيانات
        task_data['id'] = new_id
        task_data['تاريخ الإضافة'] = datetime.now().strftime('%Y-%m-%d %H:%M')
        
        new_df = pd.DataFrame([task_data])
        tasks = pd.concat([tasks, new_df], ignore_index=True)
        
        # حفظ
        if self.save_sheet('المهام', tasks):
            return True, new_id
        return False, None
    
    def add_log(self, log_data):
        """إضافة سجل صيانة"""
        logs = self.load_sheet('السجل')
        
        # إنشاء معرف جديد
        new_id = logs['id'].max() + 1 if not logs.empty and 'id' in logs.columns else 1
        
        # إضافة البيانات
        log_data['id'] = new_id
        log_data['تاريخ التسجيل'] = datetime.now().strftime('%Y-%m-%d %H:%M')
        
        new_df = pd.DataFrame([log_data])
        logs = pd.concat([logs, new_df], ignore_index=True)
        
        # حفظ
        if self.save_sheet('السجل', logs):
            return True
        return False

# ===============================
# ☁️ نظام رفع GitHub التلقائي
# ===============================
class GitHubAutoUpload:
    def __init__(self):
        self.repo = APP_CONFIG["GITHUB_REPO"]
        self.file_name = APP_CONFIG["GITHUB_FILE"]
        self.local_file = APP_CONFIG["EXCEL_FILE"]
        
    def upload_to_github(self):
        """رفع الملف إلى GitHub تلقائياً"""
        try:
            # قراءة الملف المحلي
            with open(self.local_file, 'rb') as f:
                content = f.read()
            
            # ترميز Base64
            encoded_content = base64.b64encode(content).decode('utf-8')
            
            # إنشاء رابط GitHub
            github_url = f"https://api.github.com/repos/{self.repo}/contents/{self.file_name}"
            
            # رفع الملف
            commit_message = f"تحديث تلقائي - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            
            # محاولة تحديث الملف الموجود
            response = requests.get(github_url)
            
            data = {
                "message": commit_message,
                "content": encoded_content,
                "branch": "main"
            }
            
            # إذا الملف موجود، نضيف SHA للتحديث
            if response.status_code == 200:
                data["sha"] = response.json()["sha"]
            
            # الرفع
            headers = {
                "Accept": "application/vnd.github.v3+json"
            }
            
            response = requests.put(github_url, json=data, headers=headers)
            
            if response.status_code in [200, 201]:
                return True, "✅ تم رفع الملف إلى GitHub بنجاح!"
            else:
                return False, f"⚠️ تعذر الرفع: {response.status_code}"
                
        except Exception as e:
            return False, f"❌ خطأ: {str(e)}"
    
    def download_from_github(self):
        """تحميل الملف من GitHub"""
        try:
            github_url = f"https://raw.githubusercontent.com/{self.repo}/main/{self.file_name}"
            response = requests.get(github_url)
            
            if response.status_code == 200:
                with open(self.local_file, 'wb') as f:
                    f.write(response.content)
                return True, "✅ تم تحميل الملف من GitHub"
            else:
                return False, "⚠️ الملف غير موجود على GitHub"
        except Exception as e:
            return False, f"❌ خطأ: {str(e)}"

# ===============================
# 🔧 تهيئة الأنظمة
# ===============================
@st.cache_resource
def init_excel_system():
    return ExcelSystem()

@st.cache_resource
def init_github_uploader():
    return GitHubAutoUpload()

# تهيئة الأنظمة
excel_system = init_excel_system()
github_uploader = init_github_uploader()

# ===============================
# 📊 دوال مساعدة
# ===============================
def calculate_remaining_hours(last_date_str, interval_hours):
    """حساب الساعات المتبقية"""
    try:
        last_date = datetime.strptime(last_date_str, "%Y-%m-%d")
        current_date = datetime.now()
        
        # حساب الساعات المنقضية
        hours_passed = (current_date - last_date).total_seconds() / 3600
        
        # حساب المتبقي
        remaining = max(0, interval_hours - hours_passed)
        return remaining
    except:
        return interval_hours

def update_all_tasks():
    """تحديث جميع المهام"""
    tasks = excel_system.load_sheet('المهام')
    
    if tasks.empty:
        return tasks
    
    updated_tasks = tasks.copy()
    
    for idx, task in tasks.iterrows():
        if 'تاريخ آخر صيانة' in task and 'الفترة بين الصيانة (ساعات)' in task:
            remaining = calculate_remaining_hours(
                str(task['تاريخ آخر صيانة']),
                task['الفترة بين الصيانة (ساعات)']
            )
            updated_tasks.at[idx, 'عدد الساعات المتبقية'] = remaining
            
            # حساب التاريخ القادم
            last_date = datetime.strptime(str(task['تاريخ آخر صيانة']), "%Y-%m-%d")
            next_date = last_date + timedelta(hours=task['الفترة بين الصيانة (ساعات)'])
            updated_tasks.at[idx, 'تاريخ الصيانة القادم'] = next_date.strftime("%Y-%m-%d")
    
    # حفظ التحديثات
    excel_system.save_sheet('المهام', updated_tasks)
    return updated_tasks

# ===============================
# 🎯 التطبيق الرئيسي
# ===============================
def main():
    # عنوان التطبيق
    st.markdown(f'<h1 class="main-header">{APP_CONFIG["APP_ICON"]} {APP_CONFIG["APP_TITLE"]}</h1>', unsafe_allow_html=True)
    
    # ===============================
    # 📌 الشريط الجانبي
    # ===============================
    with st.sidebar:
        st.image("https://cdn-icons-png.flaticon.com/512/3067/3067256.png", width=80)
        
        # حالة النظام
        col1, col2 = st.columns(2)
        with col1:
            if os.path.exists(APP_CONFIG["EXCEL_FILE"]):
                file_size = os.path.getsize(APP_CONFIG["EXCEL_FILE"]) / 1024
                st.success(f"📁 {file_size:.1f} KB")
        with col2:
            st.info("☁️ GitHub")
        
        st.markdown("---")
        
        # القائمة الرئيسية
        menu = st.radio(
            "📋 القائمة الرئيسية",
            [
                "🏠 لوحة التحكم",
                "➕ إضافة ماكينة",
                "🔧 إضافة مهمة",
                "📝 تسجيل صيانة",
                "📊 عرض البيانات",
                "🔄 المزامنة"
            ]
        )
        
        st.markdown("---")
        
        # إحصائيات سريعة
        machines = excel_system.load_sheet('الماكينات')
        tasks = excel_system.load_sheet('المهام')
        logs = excel_system.load_sheet('السجل')
        
        st.markdown("**📊 الإحصائيات:**")
        col1, col2 = st.columns(2)
        with col1:
            st.metric("الماكينات", len(machines))
        with col2:
            st.metric("المهام", len(tasks))
        
        st.markdown("---")
        
        # أزرار التحكم
        if st.button("🔄 تحديث البيانات", use_container_width=True):
            st.cache_data.clear()
            st.success("تم تحديث البيانات!")
            time.sleep(1)
            st.rerun()
        
        if st.button("💾 حفظ محلي", use_container_width=True):
            st.success(f"تم الحفظ في {APP_CONFIG['EXCEL_FILE']}")
        
        if st.button("☁️ رفع لـGitHub", use_container_width=True):
            success, message = github_uploader.upload_to_github()
            if success:
                st.success(message)
            else:
                st.warning(message)
        
        st.markdown("---")
        st.caption(f"🕒 {datetime.now().strftime('%H:%M')}")
        st.caption(f"📁 {APP_CONFIG['EXCEL_FILE']}")
    
    # ===============================
    # 🏠 صفحة لوحة التحكم
    # ===============================
    if menu == "🏠 لوحة التحكم":
        st.markdown("## 📊 لوحة التحكم الرئيسية")
        
        # تحميل البيانات
        machines = excel_system.load_sheet('الماكينات')
        tasks = update_all_tasks()
        
        # عدادات
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.markdown('<div class="metric-card"><h3>🏭</h3><h4>الماكينات</h4><h2>{}</h2></div>'.format(
                len(machines)
            ), unsafe_allow_html=True)
        
        with col2:
            active_tasks = len(tasks[tasks['عدد الساعات المتبقية'] <= 0]) if not tasks.empty else 0
            st.markdown('<div class="metric-card"><h3>⚠️</h3><h4>مستحقة</h4><h2>{}</h2></div>'.format(
                active_tasks
            ), unsafe_allow_html=True)
        
        with col3:
            recent_logs = len(logs) if 'logs' in locals() and not logs.empty else 0
            st.markdown('<div class="metric-card"><h3>📝</h3><h4>السجلات</h4><h2>{}</h2></div>'.format(
                recent_logs
            ), unsafe_allow_html=True)
        
        # الماكينات الأخيرة
        st.markdown("### 🆕 أحدث الماكينات")
        
        if not machines.empty:
            recent_machines = machines.tail(3)
            
            for idx, machine in recent_machines.iterrows():
                st.markdown(f"""
                <div class="machine-card">
                    <h4>⚙️ {machine['اسم الماكينة']}</h4>
                    <p><strong>الموديل:</strong> {machine.get('الموديل', 'غير محدد')}</p>
                    <p><strong>الرقم التسلسلي:</strong> {machine.get('الرقم التسلسلي', 'غير محدد')}</p>
                    <p><strong>تاريخ الإضافة:</strong> {machine.get('تاريخ الإضافة', 'غير محدد')}</p>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.info("📝 لا توجد ماكينات مسجلة. أضف أول ماكينة!")
    
    # ===============================
    # ➕ صفحة إضافة ماكينة
    # ===============================
    elif menu == "➕ إضافة ماكينة":
        st.markdown("## ➕ إضافة ماكينة جديدة")
        
        with st.form("add_machine_form", clear_on_submit=True):
            col1, col2 = st.columns(2)
            
            with col1:
                name = st.text_input("اسم الماكينة *", placeholder="ماكينة الإنتاج رقم 1")
                model = st.text_input("الموديل", placeholder="XP-2000")
                serial = st.text_input("الرقم التسلسلي *", placeholder="SN-2024-001")
            
            with col2:
                install_date = st.date_input("تاريخ التركيب *", value=datetime.now())
                total_hours = st.number_input("ساعات التشغيل الحالية *", min_value=0.0, value=0.0, step=10.0)
                is_active = st.radio("الحالة *", ["نعم", "لا"], index=0, horizontal=True)
            
            department = st.text_input("القسم/الموقع", placeholder="قسم الإنتاج - الخط 1")
            notes = st.text_area("ملاحظات إضافية", placeholder="أي معلومات إضافية عن الماكينة...")
            
            submitted = st.form_submit_button("💾 حفظ الماكينة")
            
            if submitted:
                if not name or not serial:
                    st.error("⚠️ يرجى ملء الحقول المطلوبة (*)")
                else:
                    # جمع البيانات
                    machine_data = {
                        'اسم الماكينة': name,
                        'الموديل': model if model else "",
                        'الرقم التسلسلي': serial,
                        'تاريخ التركيب': install_date.strftime('%Y-%m-%d'),
                        'إجمالي ساعات التشغيل': total_hours,
                        'القسم': department if department else "",
                        'ملاحظات': notes if notes else "",
                        'نشطة': is_active
                    }
                    
                    # إضافة الماكينة
                    success, machine_id = excel_system.add_machine(machine_data)
                    
                    if success:
                        st.success(f"✅ تمت إضافة الماكينة '{name}' بنجاح!")
                        st.balloons()
                        
                        # رفع تلقائي لـGitHub
                        with st.spinner("جاري رفع الملف إلى GitHub..."):
                            upload_success, upload_message = github_uploader.upload_to_github()
                            if upload_success:
                                st.success(upload_message)
                            else:
                                st.warning(upload_message)
                        
                        # عرض خيار إضافة مهام
                        st.markdown("---")
                        st.markdown("### 🔧 الخطوة التالية: إضافة مهام صيانة")
                        
                        if st.button(f"إضافة مهام صيانة لهذه الماكينة", key=f"add_tasks_{machine_id}"):
                            st.session_state.add_tasks_for = machine_id
                            st.rerun()
                    else:
                        st.error("❌ فشل في إضافة الماكينة")
    
    # ===============================
    # 🔧 صفحة إضافة مهمة
    # ===============================
    elif menu == "🔧 إضافة مهمة":
        st.markdown("## 🔧 إضافة مهمة صيانة جديدة")
        
        # تحميل الماكينات
        machines = excel_system.load_sheet('الماكينات')
        
        if machines.empty:
            st.warning("⚠️ لا توجد ماكينات. أضف ماكينة أولاً!")
        else:
            # إذا كان هناك ماكينة محددة
            if 'add_tasks_for' in st.session_state:
                selected_machine_id = st.session_state.add_tasks_for
                machine_name = machines[machines['id'] == selected_machine_id]['اسم الماكينة'].iloc[0]
                st.success(f"إضافة مهام لـ: **{machine_name}**")
            else:
                # اختيار الماكينة
                machine_options = {row['id']: row['اسم الماكينة'] for idx, row in machines.iterrows()}
                selected_machine_id = st.selectbox(
                    "اختر الماكينة *",
                    options=list(machine_options.keys()),
                    format_func=lambda x: machine_options[x]
                )
                machine_name = machine_options[selected_machine_id]
            
            with st.form("add_task_form", clear_on_submit=True):
                st.markdown(f"### الماكينة: {machine_name}")
                
                col1, col2 = st.columns(2)
                
                with col1:
                    task_type = st.text_input("نوع الصيانة *", placeholder="تغيير الزيت")
                    
                    # أنواع شائعة
                    common_tasks = ["", "تغيير الزيت", "التشحيم", "تنظيف الفلاتر", 
                                  "فحص الكهرباء", "تنظيف عام", "فحص المحامل"]
                    selected_common = st.selectbox("أو اختر من القائمة", options=common_tasks)
                    
                    if selected_common:
                        task_type = selected_common
                    
                    interval = st.number_input("الفترة بين الصيانة (ساعات) *", min_value=1, value=500, step=10)
                
                with col2:
                    last_date = st.date_input("تاريخ آخر صيانة *", value=datetime.now())
                    
                    # الحصول على ساعات الماكينة
                    machine_hours = 0
                    if not machines.empty:
                        machine_data = machines[machines['id'] == selected_machine_id]
                        if not machine_data.empty:
                            machine_hours = machine_data.iloc[0].get('إجمالي ساعات التشغيل', 0)
                    
                    last_hours = st.number_input(
                        "ساعات التشغيل عند آخر صيانة *",
                        min_value=0.0,
                        value=float(machine_hours),
                        step=1.0
                    )
                
                description = st.text_area("وصف المهمة", placeholder="تفاصيل عملية الصيانة...")
                
                submitted = st.form_submit_button("💾 حفظ المهمة")
                
                if submitted:
                    if not task_type:
                        st.error("⚠️ نوع الصيانة مطلوب")
                    else:
                        # حساب الساعات المتبقية
                        remaining = calculate_remaining_hours(
                            last_date.strftime('%Y-%m-%d'),
                            interval
                        )
                        
                        # حساب التاريخ القادم
                        next_date = last_date + timedelta(hours=interval)
                        
                        # جمع بيانات المهمة
                        task_data = {
                            'معرف الماكينة': selected_machine_id,
                            'نوع الصيانة': task_type,
                            'الفترة بين الصيانة (ساعات)': interval,
                            'تاريخ آخر صيانة': last_date.strftime('%Y-%m-%d'),
                            'عدد ساعات التشغيل عند آخر صيانة': last_hours,
                            'عدد الساعات المتبقية': remaining,
                            'تاريخ الصيانة القادم': next_date.strftime('%Y-%m-%d'),
                            'وصف المهمة': description if description else "",
                            'نشطة': "نعم"
                        }
                        
                        # إضافة المهمة
                        success, task_id = excel_system.add_task(task_data)
                        
                        if success:
                            st.success(f"✅ تمت إضافة مهمة '{task_type}' بنجاح!")
                            
                            # رفع تلقائي لـGitHub
                            with st.spinner("جاري رفع التحديثات إلى GitHub..."):
                                upload_success, upload_message = github_uploader.upload_to_github()
                                if upload_success:
                                    st.success(upload_message)
                                else:
                                    st.warning(upload_message)
                            
                            # إزالة الماكينة المحددة من الجلسة
                            if 'add_tasks_for' in st.session_state:
                                del st.session_state.add_tasks_for
                        else:
                            st.error("❌ فشل في إضافة المهمة")
    
    # ===============================
    # 📝 صفحة تسجيل صيانة
    # ===============================
    elif menu == "📝 تسجيل صيانة":
        st.markdown("## 📝 تسجيل عملية صيانة")
        
        # تحميل البيانات
        machines = excel_system.load_sheet('الماكينات')
        tasks = excel_system.load_sheet('المهام')
        
        if machines.empty or tasks.empty:
            st.warning("⚠️ يجب إضافة ماكينات ومهام أولاً!")
        else:
            with st.form("log_maintenance_form", clear_on_submit=True):
                col1, col2 = st.columns(2)
                
                with col1:
                    # اختيار الماكينة
                    machine_options = {row['id']: row['اسم الماكينة'] for idx, row in machines.iterrows()}
                    machine_id = st.selectbox(
                        "اختر الماكينة *",
                        options=list(machine_options.keys()),
                        format_func=lambda x: machine_options[x]
                    )
                    
                    # اختيار المهمة لهذه الماكينة
                    machine_tasks = tasks[tasks['معرف الماكينة'] == machine_id]
                    
                    if not machine_tasks.empty:
                        task_options = {row['id']: row['نوع الصيانة'] for idx, row in machine_tasks.iterrows()}
                        task_id = st.selectbox(
                            "اختر نوع الصيانة *",
                            options=list(task_options.keys()),
                            format_func=lambda x: task_options[x]
                        )
                    else:
                        st.warning("لا توجد مهام لهذه الماكينة")
                        task_id = None
                
                with col2:
                    maintenance_date = st.date_input("تاريخ الصيانة *", value=datetime.now())
                    
                    # الحصول على ساعات الماكينة الحالية
                    current_hours = 0
                    if not machines.empty:
                        machine_data = machines[machines['id'] == machine_id]
                        if not machine_data.empty:
                            current_hours = machine_data.iloc[0].get('إجمالي ساعات التشغيل', 0)
                    
                    maintenance_hours = st.number_input(
                        "عدد ساعات التشغيل *",
                        min_value=0.0,
                        value=float(current_hours),
                        step=1.0
                    )
                    
                    technician = st.text_input("اسم الفني *", placeholder="أحمد محمد")
                
                parts_used = st.text_area("الأجزاء المستبدلة", placeholder="مثال: زيت محرك 5 لتر...")
                notes = st.text_area("ملاحظات إضافية", placeholder="أي ملاحظات عن الصيانة...")
                
                submitted = st.form_submit_button("📝 تسجيل الصيانة")
                
                if submitted:
                    if not machine_id or not task_id or not technician:
                        st.error("⚠️ يرجى ملء الحقول المطلوبة (*)")
                    else:
                        # تسجيل السجل
                        log_data = {
                            'معرف الماكينة': machine_id,
                            'معرف المهمة': task_id,
                            'تاريخ الصيانة': maintenance_date.strftime('%Y-%m-%d'),
                            'عدد ساعات التشغيل': maintenance_hours,
                            'تمت بواسطة': technician,
                            'الأجزاء المستبدلة': parts_used if parts_used else "",
                            'ملاحظات': notes if notes else ""
                        }
                        
                        if excel_system.add_log(log_data):
                            st.success("✅ تم تسجيل الصيانة بنجاح!")
                            st.balloons()
                            
                            # تحديث ساعات الماكينة
                            if maintenance_hours > current_hours:
                                machines.loc[machines['id'] == machine_id, 'إجمالي ساعات التشغيل'] = maintenance_hours
                                excel_system.save_sheet('الماكينات', machines)
                            
                            # رفع تلقائي لـGitHub
                            with st.spinner("جاري رفع التحديثات إلى GitHub..."):
                                upload_success, upload_message = github_uploader.upload_to_github()
                                if upload_success:
                                    st.success(upload_message)
                                else:
                                    st.warning(upload_message)
                        else:
                            st.error("❌ فشل في تسجيل الصيانة")
    
    # ===============================
    # 📊 صفحة عرض البيانات
    # ===============================
    elif menu == "📊 عرض البيانات":
        st.markdown("## 📊 عرض جميع البيانات")
        
        tab1, tab2, tab3 = st.tabs(["الماكينات", "المهام", "سجل الصيانة"])
        
        with tab1:
            machines = excel_system.load_sheet('الماكينات')
            if not machines.empty:
                st.dataframe(machines, use_container_width=True)
            else:
                st.info("📝 لا توجد ماكينات مسجلة")
        
        with tab2:
            tasks = excel_system.load_sheet('المهام')
            if not tasks.empty:
                st.dataframe(tasks, use_container_width=True)
            else:
                st.info("📝 لا توجد مهام مسجلة")
        
        with tab3:
            logs = excel_system.load_sheet('السجل')
            if not logs.empty:
                st.dataframe(logs, use_container_width=True)
            else:
                st.info("📝 لا توجد سجلات صيانة")
    
    # ===============================
    # 🔄 صفحة المزامنة
    # ===============================
    elif menu == "🔄 المزامنة":
        st.markdown("## 🔄 مزامنة البيانات مع GitHub")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("### 📥 تحميل من GitHub")
            st.write("استعادة البيانات من GitHub")
            
            if st.button("⬇️ تحميل الآن", use_container_width=True):
                with st.spinner("جاري التحميل..."):
                    success, message = github_uploader.download_from_github()
                    if success:
                        st.success(message)
                        st.cache_data.clear()
                        time.sleep(2)
                        st.rerun()
                    else:
                        st.warning(message)
        
        with col2:
            st.markdown("### 📤 رفع إلى GitHub")
            st.write("حفظ البيانات الحالية على GitHub")
            
            if st.button("☁️ رفع الآن", use_container_width=True):
                with st.spinner("جاري الرفع..."):
                    success, message = github_uploader.upload_to_github()
                    if success:
                        st.success(message)
                    else:
                        st.warning(message)
        
        # معلومات الملف
        st.markdown("---")
        st.markdown("### 📊 معلومات الملف")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if os.path.exists(APP_CONFIG["EXCEL_FILE"]):
                file_size = os.path.getsize(APP_CONFIG["EXCEL_FILE"]) / 1024
                st.metric("الحجم المحلي", f"{file_size:.1f} KB")
        
        with col2:
            machines = excel_system.load_sheet('الماكينات')
            st.metric("عدد الماكينات", len(machines))
        
        with col3:
            tasks = excel_system.load_sheet('المهام')
            st.metric("عدد المهام", len(tasks))
        
        # زر التحديث الكامل
        if st.button("🔄 تحديث شامل", use_container_width=True):
            st.cache_data.clear()
            
            # تحديث المهام
            update_all_tasks()
            
            # رفع إلى GitHub
            success, message = github_uploader.upload_to_github()
            
            if success:
                st.success("✅ تم التحديث الشامل بنجاح!")
            else:
                st.warning(f"⚠️ {message}")
            
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
        st.caption(f"☁️ GitHub: {APP_CONFIG['GITHUB_REPO']}")
    
    with footer_cols[2]:
        if os.path.exists(APP_CONFIG["EXCEL_FILE"]):
            mod_time = datetime.fromtimestamp(os.path.getmtime(APP_CONFIG["EXCEL_FILE"])).strftime("%H:%M")
            st.caption(f"🕒 آخر تحديث: {mod_time}")

# تشغيل التطبيق
if __name__ == "__main__":
    main()
