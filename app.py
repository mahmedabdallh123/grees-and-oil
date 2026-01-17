import streamlit as st
import pandas as pd
import os
import requests
import base64
from datetime import datetime, timedelta
import time
from io import BytesIO
import json

# ===============================
# ⚙ إعدادات التطبيق
# ===============================
APP_CONFIG = {
    "APP_TITLE": "سيرفيس تحضيرات بيل يارن 1 🏭",
    "APP_ICON": "⚙️",
    "EXCEL_FILE": "machines.xlsx",
    "GITHUB_REPO": "mahmedabdallh123/grees-and-oil",
    "GITHUB_TOKEN": "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"
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
    }
    .success-box {
        background-color: #d4edda;
        border: 1px solid #c3e6cb;
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
    .form-box {
        background: white;
        padding: 25px;
        border-radius: 10px;
        box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        margin: 20px 0;
    }
</style>
""", unsafe_allow_html=True)

# ===============================
# 🗄 نظام Excel + GitHub المتكامل
# ===============================
class GitHubExcelDB:
    def __init__(self, file_path="machines.xlsx"):
        self.file_path = file_path
        self.token = APP_CONFIG["GITHUB_TOKEN"]
        self.repo = APP_CONFIG["GITHUB_REPO"]
        self.headers = {
            "Authorization": f"token {self.token}",
            "Accept": "application/vnd.github.v3+json"
        }
        self.setup_database()
    
    def github_api_call(self, method, url, data=None):
        """استدعاء GitHub API"""
        try:
            if method == "GET":
                response = requests.get(url, headers=self.headers)
            elif method == "PUT":
                response = requests.put(url, headers=self.headers, json=data)
            elif method == "POST":
                response = requests.post(url, headers=self.headers, json=data)
            
            if response.status_code in [200, 201]:
                return True, response.json()
            else:
                return False, f"خطأ API: {response.status_code} - {response.text}"
        except Exception as e:
            return False, f"خطأ اتصال: {str(e)}"
    
    def download_from_github(self):
        """تحميل الملف من GitHub"""
        try:
            url = f"https://api.github.com/repos/{self.repo}/contents/{self.file_path}"
            success, result = self.github_api_call("GET", url)
            
            if success:
                content = result.get("content", "")
                if content:
                    # فك التشفير base64
                    file_content = base64.b64decode(content)
                    
                    # حفظ محلياً
                    with open(self.file_path, "wb") as f:
                        f.write(file_content)
                    
                    return True, "✅ تم تحميل الملف من GitHub"
                else:
                    return False, "الملف فارغ على GitHub"
            else:
                return False, result
        except Exception as e:
            return False, f"خطأ في التحميل: {str(e)}"
    
    def upload_to_github(self, commit_message=None):
        """رفع الملف إلى GitHub"""
        try:
            if not os.path.exists(self.file_path):
                return False, "الملف المحلي غير موجود"
            
            # قراءة الملف
            with open(self.file_path, "rb") as f:
                content = f.read()
            
            # تحويل إلى base64
            encoded_content = base64.b64encode(content).decode("utf-8")
            
            # بناء رسالة الحفظ
            if not commit_message:
                commit_message = f"تحديث تلقائي - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            
            # بيانات الرفع
            data = {
                "message": commit_message,
                "content": encoded_content,
                "branch": "main"
            }
            
            # الحصول على SHA إذا الملف موجود
            url = f"https://api.github.com/repos/{self.repo}/contents/{self.file_path}"
            
            # محاولة الحصول على SHA
            try:
                response = requests.get(url, headers=self.headers)
                if response.status_code == 200:
                    existing_data = response.json()
                    data["sha"] = existing_data.get("sha", "")
            except:
                pass
            
            # الرفع
            success, result = self.github_api_call("PUT", url, data)
            
            if success:
                # الحصول على الرابط للعرض
                file_url = f"https://github.com/{self.repo}/blob/main/{self.file_path}"
                raw_url = f"https://raw.githubusercontent.com/{self.repo}/main/{self.file_path}"
                
                return True, {
                    "message": "✅ تم رفع الملف إلى GitHub بنجاح!",
                    "view_url": file_url,
                    "raw_url": raw_url
                }
            else:
                return False, result
                
        except Exception as e:
            return False, f"خطأ في الرفع: {str(e)}"
    
    def sync_with_github(self):
        """مزامنة مع GitHub (تنزيل أولاً ثم رفع)"""
        try:
            # محاولة التحميل من GitHub أولاً
            download_success, download_msg = self.download_from_github()
            
            if not download_success:
                # إذا الملف غير موجود على GitHub، نرفع الملف المحلي
                st.warning(f"⚠️ {download_msg} - سيتم رفع الملف المحلي")
            
            # رفع التحديثات
            upload_success, upload_result = self.upload_to_github()
            
            if upload_success:
                return True, upload_result
            else:
                return False, upload_result
                
        except Exception as e:
            return False, f"خطأ في المزامنة: {str(e)}"
    
    def setup_database(self):
        """إعداد قاعدة البيانات مع المزامنة"""
        try:
            # محاولة تحميل من GitHub أولاً
            if not os.path.exists(self.file_path):
                download_success, download_msg = self.download_from_github()
                
                if not download_success:
                    # إنشاء قاعدة بيانات جديدة
                    self.create_new_database()
                    
                    # رفع القاعدة الجديدة إلى GitHub
                    self.upload_to_github("إنشاء قاعدة بيانات جديدة")
                    
                    st.success("✅ تم إنشاء قاعدة بيانات جديدة ومزامنتها مع GitHub")
                else:
                    st.success(f"✅ {download_msg}")
            else:
                # المزامنة التلقائية
                self.auto_sync()
                
        except Exception as e:
            st.error(f"❌ خطأ في إعداد قاعدة البيانات: {str(e)}")
    
    def create_new_database(self):
        """إنشاء قاعدة بيانات جديدة"""
        try:
            # إنشاء DataFrames فارغة
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
            
            # حفظ محلياً
            with pd.ExcelWriter(self.file_path, engine='openpyxl') as writer:
                machines_df.to_excel(writer, sheet_name='الماكينات', index=False)
                tasks_df.to_excel(writer, sheet_name='المهام', index=False)
                logs_df.to_excel(writer, sheet_name='السجل', index=False)
            
            return True
            
        except Exception as e:
            st.error(f"❌ خطأ في إنشاء قاعدة البيانات: {str(e)}")
            return False
    
    def auto_sync(self):
        """مزامنة تلقائية كل 5 دقائق"""
        if 'last_sync' not in st.session_state:
            st.session_state.last_sync = datetime.now()
        
        # حساب الوقت منذ آخر مزامنة
        time_since_last_sync = datetime.now() - st.session_state.last_sync
        
        # إذا مرت 5 دقائق، قم بالمزامنة
        if time_since_last_sync.total_seconds() > 300:  # 300 ثانية = 5 دقائق
            with st.spinner("جاري المزامنة التلقائية مع GitHub..."):
                success, result = self.sync_with_github()
                if success:
                    st.session_state.last_sync = datetime.now()
                    # لا نعرض رسالة النجاح لتجنب الإزعاج
                else:
                    st.warning(f"⚠️ فشلت المزامنة التلقائية: {result}")
    
    def load_sheet(self, sheet_name):
        """تحميل ورقة من Excel"""
        try:
            if os.path.exists(self.file_path):
                df = pd.read_excel(self.file_path, sheet_name=sheet_name)
                return df
            return pd.DataFrame()
        except:
            return pd.DataFrame()
    
    def save_all_sheets(self, machines_df, tasks_df, logs_df, commit_message=None):
        """حفظ جميع الأوراق مع المزامنة"""
        try:
            # حفظ محلياً
            with pd.ExcelWriter(self.file_path, engine='openpyxl') as writer:
                machines_df.to_excel(writer, sheet_name='الماكينات', index=False)
                tasks_df.to_excel(writer, sheet_name='المهام', index=False)
                logs_df.to_excel(writer, sheet_name='السجل', index=False)
            
            # مزامنة مع GitHub
            if commit_message is None:
                commit_message = f"تحديث بيانات - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            
            success, result = self.upload_to_github(commit_message)
            
            if success:
                return True, result
            else:
                st.warning(f"⚠️ تم الحفظ محلياً فقط: {result}")
                return False, "تم الحفظ محلياً فقط"
            
        except Exception as e:
            st.error(f"❌ خطأ في حفظ الملف: {str(e)}")
            return False, str(e)
    
    def add_machine(self, machine_data):
        """إضافة ماكينة مع المزامنة"""
        try:
            # تحميل البيانات الحالية
            machines = self.load_sheet('الماكينات')
            tasks = self.load_sheet('المهام')
            logs = self.load_sheet('السجل')
            
            # إنشاء معرف جديد
            if machines.empty or 'id' not in machines.columns:
                new_id = 1
            else:
                max_id = machines['id'].max()
                if pd.isna(max_id):
                    new_id = 1
                else:
                    new_id = int(max_id) + 1
            
            # إضافة البيانات
            machine_data['id'] = new_id
            machine_data['تاريخ الإضافة'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            new_row = pd.DataFrame([machine_data])
            machines = pd.concat([machines, new_row], ignore_index=True)
            
            # حفظ ومزامنة
            commit_msg = f"إضافة ماكينة جديدة: {machine_data.get('اسم الماكينة', 'ماكينة')}"
            success, result = self.save_all_sheets(machines, tasks, logs, commit_msg)
            
            if success:
                return True, new_id, result
            return False, None, result
            
        except Exception as e:
            st.error(f"❌ خطأ في إضافة الماكينة: {str(e)}")
            return False, None, str(e)
    
    def add_task(self, task_data):
        """إضافة مهمة مع المزامنة"""
        try:
            # تحميل البيانات الحالية
            machines = self.load_sheet('الماكينات')
            tasks = self.load_sheet('المهام')
            logs = self.load_sheet('السجل')
            
            # إنشاء معرف جديد
            if tasks.empty or 'id' not in tasks.columns:
                new_id = 1
            else:
                max_id = tasks['id'].max()
                if pd.isna(max_id):
                    new_id = 1
                else:
                    new_id = int(max_id) + 1
            
            # إضافة البيانات
            task_data['id'] = new_id
            task_data['تاريخ الإضافة'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            new_row = pd.DataFrame([task_data])
            tasks = pd.concat([tasks, new_row], ignore_index=True)
            
            # حفظ ومزامنة
            commit_msg = f"إضافة مهمة صيانة: {task_data.get('نوع الصيانة', 'مهمة')}"
            success, result = self.save_all_sheets(machines, tasks, logs, commit_msg)
            
            if success:
                return True, new_id, result
            return False, None, result
            
        except Exception as e:
            st.error(f"❌ خطأ في إضافة المهمة: {str(e)}")
            return False, None, str(e)
    
    def add_log(self, log_data):
        """إضافة سجل مع المزامنة"""
        try:
            # تحميل البيانات الحالية
            machines = self.load_sheet('الماكينات')
            tasks = self.load_sheet('المهام')
            logs = self.load_sheet('السجل')
            
            # إنشاء معرف جديد
            if logs.empty or 'id' not in logs.columns:
                new_id = 1
            else:
                max_id = logs['id'].max()
                if pd.isna(max_id):
                    new_id = 1
                else:
                    new_id = int(max_id) + 1
            
            # إضافة البيانات
            log_data['id'] = new_id
            log_data['تاريخ التسجيل'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            new_row = pd.DataFrame([log_data])
            logs = pd.concat([logs, new_row], ignore_index=True)
            
            # حفظ ومزامنة
            commit_msg = f"تسجيل صيانة - الفني: {log_data.get('تمت بواسطة', 'فني')}"
            success, result = self.save_all_sheets(machines, tasks, logs, commit_msg)
            
            if success:
                return True, result
            return False, result
            
        except Exception as e:
            st.error(f"❌ خطأ في إضافة السجل: {str(e)}")
            return False, str(e)

# ===============================
# 🔧 تهيئة الأنظمة
# ===============================
@st.cache_resource
def init_database():
    return GitHubExcelDB(APP_CONFIG["EXCEL_FILE"])

# إنشاء قاعدة البيانات
db = init_database()

# ===============================
# 📊 دوال مساعدة
# ===============================
def calculate_remaining_hours(last_date_str, interval_hours):
    """حساب الساعات المتبقية"""
    try:
        last_date = datetime.strptime(str(last_date_str), "%Y-%m-%d")
        current_date = datetime.now()
        hours_passed = (current_date - last_date).total_seconds() / 3600
        remaining = max(0, interval_hours - hours_passed)
        return remaining
    except:
        return interval_hours

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
            else:
                st.warning("📁 لا يوجد ملف")
        with col2:
            st.info("☁️ GitHub")
        
        st.markdown("---")
        
        # القائمة الرئيسية
        menu = st.radio(
            "📋 اختر الصفحة:",
            [
                "🏠 الرئيسية",
                "➕ إضافة ماكينة",
                "🔧 إضافة مهمة",
                "📝 تسجيل صيانة",
                "🔄 إدارة GitHub"
            ]
        )
        
        st.markdown("---")
        
        # تحميل البيانات لعرض الإحصائيات
        machines = db.load_sheet('الماكينات')
        tasks = db.load_sheet('المهام')
        
        st.markdown("**📊 الإحصائيات:**")
        col1, col2 = st.columns(2)
        with col1:
            st.metric("الماكينات", len(machines) if not machines.empty else 0)
        with col2:
            st.metric("المهام", len(tasks) if not tasks.empty else 0)
        
        # زر المزامنة السريع
        st.markdown("---")
        if st.button("🔄 مزامنة سريعة مع GitHub", use_container_width=True):
            with st.spinner("جاري المزامنة..."):
                success, result = db.sync_with_github()
                if success:
                    st.success(result.get("message", "تمت المزامنة"))
                    
                    # عرض الروابط
                    if "view_url" in result:
                        st.markdown(f"[📎 عرض الملف]({result['view_url']})")
                else:
                    st.error(result)
        
        st.markdown("---")
        
        # أزرار التحكم
        if st.button("🔄 تحديث التطبيق", use_container_width=True):
            st.cache_data.clear()
            st.success("تم التحديث!")
            time.sleep(1)
            st.rerun()
        
        st.markdown("---")
        st.caption(f"🕒 {datetime.now().strftime('%H:%M')}")
        st.caption(f"📁 {APP_CONFIG['EXCEL_FILE']}")
    
    # ===============================
    # 🏠 صفحة الرئيسية
    # ===============================
    if menu == "🏠 الرئيسية":
        st.markdown("## 🎯 نظام إدارة صيانة الماكينات")
        
        # معلومات النظام
        st.markdown("""
        <div class="success-box">
        <h3>✅ النظام يعمل بنجاح مع GitHub!</h3>
        <p><strong>الميزات المتاحة:</strong></p>
        <ol>
            <li><strong>إضافة ماكينة جديدة</strong> - مع حفظ تلقائي على GitHub</li>
            <li><strong>إضافة مهام صيانة</strong> - لكل ماكينة مع المزامنة</li>
            <li><strong>تسجيل عمليات الصيانة</strong> - مع حفظ فوري على السحابة</li>
            <li><strong>إدارة كاملة مع GitHub</strong> - رفع وتحميل تلقائي</li>
        </ol>
        <p>جميع التعديلات تحفظ تلقائياً على GitHub عند الضغط على زر الحفظ</p>
        </div>
        """, unsafe_allow_html=True)
        
        # عدادات سريعة
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.markdown('<div class="metric-card"><h3>🏭</h3><h4>الماكينات</h4><h2>{}</h2></div>'.format(
                len(machines) if not machines.empty else 0
            ), unsafe_allow_html=True)
        
        with col2:
            st.markdown('<div class="metric-card"><h3>🔧</h3><h4>المهام</h4><h2>{}</h2></div>'.format(
                len(tasks) if not tasks.empty else 0
            ), unsafe_allow_html=True)
        
        with col3:
            logs = db.load_sheet('السجل')
            st.markdown('<div class="metric-card"><h3>📝</h3><h4>السجلات</h4><h2>{}</h2></div>'.format(
                len(logs) if not logs.empty else 0
            ), unsafe_allow_html=True)
        
        # حالة المزامنة
        st.markdown("### 🔄 حالة المزامنة مع GitHub")
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("📥 تحميل من GitHub", use_container_width=True):
                with st.spinner("جاري التحميل..."):
                    success, message = db.download_from_github()
                    if success:
                        st.success(message)
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error(message)
        
        with col2:
            if st.button("📤 رفع إلى GitHub", use_container_width=True):
                with st.spinner("جاري الرفع..."):
                    success, result = db.upload_to_github()
                    if success:
                        st.success(result["message"])
                        
                        # عرض الروابط
                        st.markdown(f"[📎 عرض الملف على GitHub]({result['view_url']})")
                    else:
                        st.error(result)
    
    # ===============================
    # ➕ صفحة إضافة ماكينة
    # ===============================
    elif menu == "➕ إضافة ماكينة":
        st.markdown("## ➕ إضافة ماكينة جديدة")
        
        # تحقق إذا كان هناك ماكينة مضافة مسبقاً لتظهر خيار إضافة المهام
        if 'last_added_machine' in st.session_state:
            machine_id = st.session_state.last_added_machine
            machine_name = st.session_state.last_machine_name
            
            st.success(f"✅ تمت إضافة الماكينة '{machine_name}' بنجاح!")
            st.markdown("---")
            st.markdown("### 🔧 الخطوة التالية")
            
            col1, col2 = st.columns(2)
            with col1:
                if st.button("إضافة مهام لهذه الماكينة", use_container_width=True):
                    st.session_state.add_tasks_for = machine_id
                    st.session_state.add_tasks_name = machine_name
                    st.rerun()
            with col2:
                if st.button("إضافة ماكينة جديدة", use_container_width=True):
                    if 'last_added_machine' in st.session_state:
                        del st.session_state.last_added_machine
                    if 'last_machine_name' in st.session_state:
                        del st.session_state.last_machine_name
                    st.rerun()
            
            st.markdown("---")
        
        st.markdown('<div class="form-box">', unsafe_allow_html=True)
        st.markdown("### 📝 بيانات الماكينة")
        
        with st.form("add_machine_form", clear_on_submit=True):
            col1, col2 = st.columns(2)
            
            with col1:
                name = st.text_input("اسم الماكينة *", placeholder="ماكينة الإنتاج رقم 1")
                model = st.text_input("الموديل", placeholder="XP-2000")
                serial = st.text_input("الرقم التسلسلي *", placeholder="SN-2024-001")
            
            with col2:
                install_date = st.date_input("تاريخ التركيب *", value=datetime.now())
                total_hours = st.number_input("ساعات التشغيل الحالية *", 
                                            min_value=0.0, value=0.0, step=10.0)
                is_active = st.radio("الحالة *", ["نعم", "لا"], index=0, horizontal=True)
            
            department = st.text_input("القسم/الموقع", placeholder="قسم الإنتاج - الخط 1")
            notes = st.text_area("ملاحظات إضافية")
            
            submitted = st.form_submit_button("💾 حفظ الماكينة على GitHub")
        
        st.markdown('</div>', unsafe_allow_html=True)
        
        # معالجة تقديم النموذج
        if 'submitted' in locals() and submitted:
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
                with st.spinner("جاري حفظ الماكينة ومزامنتها مع GitHub..."):
                    success, machine_id, result = db.add_machine(machine_data)
                    
                    if success:
                        st.success(f"✅ تمت إضافة الماكينة '{name}' بنجاح!")
                        st.balloons()
                        
                        # حفظ في الجلسة لعرض خيار إضافة المهام
                        st.session_state.last_added_machine = machine_id
                        st.session_state.last_machine_name = name
                        
                        # عرض رابط GitHub
                        if isinstance(result, dict) and "view_url" in result:
                            st.markdown(f"**🔗 تم الرفع إلى:** [{result['view_url']}]({result['view_url']})")
                        
                        # تحديث الصفحة
                        st.rerun()
                    else:
                        st.error(f"❌ فشل في إضافة الماكينة: {result}")
    
    # ===============================
    # 🔧 صفحة إضافة مهمة
    # ===============================
    elif menu == "🔧 إضافة مهمة":
        st.markdown("## 🔧 إضافة مهمة صيانة")
        
        # تحميل الماكينات
        machines = db.load_sheet('الماكينات')
        
        if machines.empty:
            st.warning("⚠️ لا توجد ماكينات. أضف ماكينة أولاً!")
        else:
            # إذا كان هناك ماكينة محددة من صفحة إضافة الماكينة
            if 'add_tasks_for' in st.session_state:
                selected_machine_id = st.session_state.add_tasks_for
                machine_name = st.session_state.get('add_tasks_name', "غير معروف")
                st.success(f"إضافة مهام لـ: **{machine_name}**")
            else:
                # اختيار الماكينة
                machine_options = {}
                for idx, row in machines.iterrows():
                    if 'id' in row and 'اسم الماكينة' in row:
                        machine_options[row['id']] = row['اسم الماكينة']
                
                if machine_options:
                    selected_machine_id = st.selectbox(
                        "اختر الماكينة *",
                        options=list(machine_options.keys()),
                        format_func=lambda x: machine_options[x]
                    )
                    machine_name = machine_options[selected_machine_id]
                else:
                    st.error("❌ لا توجد ماكينات صالحة")
                    return
            
            st.markdown('<div class="form-box">', unsafe_allow_html=True)
            st.markdown(f"### الماكينة: {machine_name}")
            
            with st.form("add_task_form", clear_on_submit=True):
                col1, col2 = st.columns(2)
                
                with col1:
                    task_type = st.text_input("نوع الصيانة *", placeholder="تغيير الزيت")
                    
                    # أنواع شائعة
                    common_tasks = ["تغيير الزيت", "التشحيم", "تنظيف الفلاتر", 
                                  "فحص الكهرباء", "تنظيف عام", "فحص المحامل",
                                  "تغيير الفلاتر", "فحص الأحزمة"]
                    
                    selected_common = st.selectbox(
                        "أو اختر من القائمة",
                        options=[""] + common_tasks
                    )
                    
                    if selected_common:
                        task_type = selected_common
                    
                    interval = st.number_input("الفترة بين الصيانة (ساعات) *", 
                                             min_value=1, value=500, step=10)
                
                with col2:
                    last_date = st.date_input("تاريخ آخر صيانة *", value=datetime.now())
                    
                    # الحصول على ساعات الماكينة
                    machine_hours = 0
                    if not machines.empty:
                        machine_row = machines[machines['id'] == selected_machine_id]
                        if not machine_row.empty and 'إجمالي ساعات التشغيل' in machine_row.columns:
                            machine_hours = machine_row.iloc[0].get('إجمالي ساعات التشغيل', 0)
                    
                    last_hours = st.number_input(
                        "ساعات التشغيل عند آخر صيانة *",
                        min_value=0.0,
                        value=float(machine_hours),
                        step=1.0
                    )
                
                description = st.text_area("وصف المهمة", 
                                         placeholder="تفاصيل عملية الصيانة...")
                
                submitted = st.form_submit_button("💾 حفظ المهمة على GitHub")
            
            st.markdown('</div>', unsafe_allow_html=True)
            
            # معالجة تقديم النموذج
            if 'submitted' in locals() and submitted:
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
                        'معرف الماكينة': int(selected_machine_id),
                        'نوع الصيانة': task_type,
                        'الفترة بين الصيانة (ساعات)': int(interval),
                        'تاريخ آخر صيانة': last_date.strftime('%Y-%m-%d'),
                        'عدد ساعات التشغيل عند آخر صيانة': float(last_hours),
                        'عدد الساعات المتبقية': float(remaining),
                        'تاريخ الصيانة القادم': next_date.strftime('%Y-%m-%d'),
                        'وصف المهمة': description if description else "",
                        'نشطة': "نعم"
                    }
                    
                    # إضافة المهمة
                    with st.spinner("جاري حفظ المهمة ومزامنتها مع GitHub..."):
                        success, task_id, result = db.add_task(task_data)
                        
                        if success:
                            st.success(f"✅ تمت إضافة مهمة '{task_type}' بنجاح!")
                            
                            # عرض رابط GitHub
                            if isinstance(result, dict) and "view_url" in result:
                                st.markdown(f"**🔗 تم الرفع إلى:** [{result['view_url']}]({result['view_url']})")
                            
                            # خيار إضافة المزيد
                            col1, col2 = st.columns(2)
                            with col1:
                                if st.button("إضافة مهمة أخرى لنفس الماكينة"):
                                    st.rerun()
                            with col2:
                                if st.button("الذهاب لإضافة ماكينة جديدة"):
                                    if 'add_tasks_for' in st.session_state:
                                        del st.session_state.add_tasks_for
                                    if 'add_tasks_name' in st.session_state:
                                        del st.session_state.add_tasks_name
                                    st.rerun()
                        else:
                            st.error(f"❌ فشل في إضافة المهمة: {result}")
    
    # ===============================
    # 📝 صفحة تسجيل صيانة
    # ===============================
    elif menu == "📝 تسجيل صيانة":
        st.markdown("## 📝 تسجيل عملية صيانة")
        
        # تحميل البيانات
        machines = db.load_sheet('الماكينات')
        tasks = db.load_sheet('المهام')
        
        if machines.empty or tasks.empty:
            st.warning("⚠️ يجب إضافة ماكينات ومهام أولاً!")
        else:
            st.markdown('<div class="form-box">', unsafe_allow_html=True)
            
            with st.form("log_maintenance_form", clear_on_submit=True):
                col1, col2 = st.columns(2)
                
                with col1:
                    # اختيار الماكينة
                    machine_options = {}
                    for idx, row in machines.iterrows():
                        if 'id' in row and 'اسم الماكينة' in row:
                            machine_options[row['id']] = row['اسم الماكينة']
                    
                    if machine_options:
                        machine_id = st.selectbox(
                            "اختر الماكينة *",
                            options=list(machine_options.keys()),
                            format_func=lambda x: machine_options[x]
                        )
                        
                        # اختيار المهمة لهذه الماكينة
                        machine_tasks = tasks[tasks['معرف الماكينة'] == machine_id]
                        
                        if not machine_tasks.empty:
                            task_options = {}
                            for idx, row in machine_tasks.iterrows():
                                if 'id' in row and 'نوع الصيانة' in row:
                                    task_options[row['id']] = row['نوع الصيانة']
                            
                            if task_options:
                                task_id = st.selectbox(
                                    "اختر نوع الصيانة *",
                                    options=list(task_options.keys()),
                                    format_func=lambda x: task_options[x]
                                )
                            else:
                                st.warning("لا توجد مهام مسجلة لهذه الماكينة")
                                task_id = None
                        else:
                            st.warning("لا توجد مهام لهذه الماكينة")
                            task_id = None
                    else:
                        st.error("❌ لا توجد ماكينات صالحة")
                        machine_id = None
                        task_id = None
                
                with col2:
                    maintenance_date = st.date_input("تاريخ الصيانة *", value=datetime.now())
                    
                    # الحصول على ساعات الماكينة الحالية
                    current_hours = 0
                    if machine_id and not machines.empty:
                        machine_row = machines[machines['id'] == machine_id]
                        if not machine_row.empty and 'إجمالي ساعات التشغيل' in machine_row.columns:
                            current_hours = machine_row.iloc[0].get('إجمالي ساعات التشغيل', 0)
                    
                    maintenance_hours = st.number_input(
                        "عدد ساعات التشغيل *",
                        min_value=0.0,
                        value=float(current_hours),
                        step=1.0
                    )
                    
                    technician = st.text_input("اسم الفني *", placeholder="أحمد محمد")
                
                parts_used = st.text_area("الأجزاء المستبدلة", 
                                        placeholder="مثال: زيت محرك 5 لتر، فلتر هواء...")
                notes = st.text_area("ملاحظات إضافية", 
                                   placeholder="أي ملاحظات عن الصيانة...")
                
                submitted = st.form_submit_button("📝 تسجيل الصيانة على GitHub")
            
            st.markdown('</div>', unsafe_allow_html=True)
            
            # معالجة تقديم النموذج
            if 'submitted' in locals() and submitted:
                if not machine_id or not task_id or not technician:
                    st.error("⚠️ يرجى ملء الحقول المطلوبة (*)")
                else:
                    # تسجيل السجل
                    log_data = {
                        'معرف الماكينة': int(machine_id),
                        'معرف المهمة': int(task_id),
                        'تاريخ الصيانة': maintenance_date.strftime('%Y-%m-%d'),
                        'عدد ساعات التشغيل': float(maintenance_hours),
                        'تمت بواسطة': technician,
                        'الأجزاء المستبدلة': parts_used if parts_used else "",
                        'ملاحظات': notes if notes else ""
                    }
                    
                    with st.spinner("جاري تسجيل الصيانة ومزامنتها مع GitHub..."):
                        success, result = db.add_log(log_data)
                        
                        if success:
                            st.success("✅ تم تسجيل الصيانة بنجاح!")
                            st.balloons()
                            
                            # عرض رابط GitHub
                            if isinstance(result, dict) and "view_url" in result:
                                st.markdown(f"**🔗 تم الرفع إلى:** [{result['view_url']}]({result['view_url']})")
                        else:
                            st.error(f"❌ فشل في تسجيل الصيانة: {result}")
    
    # ===============================
    # 🔄 صفحة إدارة GitHub
    # ===============================
    elif menu == "🔄 إدارة GitHub":
        st.markdown("## 🔄 إدارة المزامنة مع GitHub")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown('<div class="form-box">', unsafe_allow_html=True)
            st.markdown("### 📤 رفع الملف إلى GitHub")
            
            commit_message = st.text_input(
                "رسالة الحفظ على GitHub",
                value=f"تحديث يدوي - {datetime.now().strftime('%Y-%m-%d %H:%M')}",
                placeholder="أدخل رسالة توضح التغييرات..."
            )
            
            if st.button("☁️ رفع الآن إلى GitHub", use_container_width=True):
                with st.spinner("جاري الرفع إلى GitHub..."):
                    success, result = db.upload_to_github(commit_message)
                    if success:
                        st.success(result["message"])
                        
                        # عرض المعلومات
                        st.markdown("**🔗 الروابط:**")
                        st.markdown(f"1. [📎 عرض الملف على GitHub]({result['view_url']})")
                        st.markdown(f"2. [⬇️ تحميل الملف مباشرة]({result['raw_url']})")
                    else:
                        st.error(f"❌ {result}")
            st.markdown('</div>', unsafe_allow_html=True)
        
        with col2:
            st.markdown('<div class="form-box">', unsafe_allow_html=True)
            st.markdown("### 📥 تحميل من GitHub")
            st.write("سحب أحدث نسخة من GitHub واستبدال الملف المحلي")
            
            if st.button("⬇️ تحميل من GitHub", use_container_width=True):
                with st.spinner("جاري التحميل من GitHub..."):
                    success, message = db.download_from_github()
                    if success:
                        st.success(message)
                        
                        # إعادة تحميل البيانات
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error(f"❌ {message}")
            
            st.markdown("### 🔄 مزامنة كاملة")
            st.write("تحميل من GitHub ثم رفع التحديثات")
            
            if st.button("🔄 مزامنة كاملة", use_container_width=True):
                with st.spinner("جاري المزامنة الكاملة..."):
                    success, result = db.sync_with_github()
                    if success:
                        st.success(result["message"])
                        
                        # عرض الروابط
                        if "view_url" in result:
                            st.markdown(f"[📎 عرض الملف على GitHub]({result['view_url']})")
                    else:
                        st.error(f"❌ {result}")
            
            st.markdown('</div>', unsafe_allow_html=True)
        
        # معلومات الملف
        st.markdown("---")
        st.markdown("### 📊 معلومات الملف")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if os.path.exists(APP_CONFIG["EXCEL_FILE"]):
                file_size = os.path.getsize(APP_CONFIG["EXCEL_FILE"]) / 1024
                st.metric("الحجم المحلي", f"{file_size:.1f} KB")
            else:
                st.metric("الحجم المحلي", "غير موجود")
        
        with col2:
            machines = db.load_sheet('الماكينات')
            st.metric("الماكينات", len(machines))
        
        with col3:
            logs = db.load_sheet('السجل')
            st.metric("السجلات", len(logs))
        
        # رابط GitHub
        st.markdown("---")
        st.markdown("### 🔗 رابط المستودع على GitHub:")
        
        repo_url = f"https://github.com/{APP_CONFIG['GITHUB_REPO']}"
        st.markdown(f"[{repo_url}]({repo_url})")
        
        # معلومات إضافية
        st.markdown("---")
        st.markdown("**ℹ️ ملاحظات:**")
        st.markdown("""
        1. جميع عمليات الإضافة والتعديل تحفظ تلقائياً على GitHub
        2. يتم رفع الملف مع كل عملية إضافة جديدة
        3. يمكنك تحميل آخر نسخة من GitHub في أي وقت
        4. النظام يحتفظ بنسخة محلية لسرعة الوصول
        """)

# تشغيل التطبيق
if __name__ == "__main__":
    main()
