import streamlit as st
import pandas as pd
import numpy as np
import json
import os
import io
import requests
import shutil
import re
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
import plotly.graph_objects as go
import plotly.express as px
from base64 import b64decode
import uuid
import warnings
warnings.filterwarnings('ignore')

# ===============================
# ⚙ إعدادات التطبيق
# ===============================
APP_CONFIG = {
    "APP_TITLE": "نظام إدارة صيانة الماكينات - توقيت التشحيم وتغيير الزيت",
    "APP_ICON": "⚙️",
    
    # إعدادات GitHub
    "REPO_NAME": "mahmedabdallh123/BELYARN",
    "BRANCH": "main",
    "FILE_PATH": "oil.xlsx",
    "LOCAL_FILE": "oil.xlsx",
    
    # إعدادات الأمان
    "MAX_ACTIVE_USERS": 5,
    "SESSION_DURATION_MINUTES": 60,
    
    # إعدادات الواجهة
    "SHOW_TECH_SUPPORT_TO_ALL": True,
    "CUSTOM_TABS": ["🏭 لوحة القيادة", "➕ إضافة ماكينة", "📊 إدارة الصيانة", "⏰ المؤقتات التنازلية", "📈 التقارير والإحصائيات", "⚙️ الإعدادات"],
    
    # أنواع الصيانة الافتراضية
    "DEFAULT_MAINTENANCE_TYPES": [
        {"id": "oil_change", "name": "تغيير الزيت", "unit": "ساعات", "default_interval": 1000},
        {"id": "greasing", "name": "التشحيم", "unit": "ساعات", "default_interval": 500},
        {"id": "filter_change", "name": "تغيير الفلتر", "unit": "ساعات", "default_interval": 2000},
        {"id": "inspection", "name": "فحص دوري", "unit": "أيام", "default_interval": 30},
        {"id": "calibration", "name": "معايرة", "unit": "أشهر", "default_interval": 6}
    ],
    
    # إعدادات الإشعارات
    "WARNING_DAYS_BEFORE": 7,
    "CRITICAL_DAYS_BEFORE": 3,
    
    # ألوان الحالة
    "COLORS": {
        "normal": "#28a745",
        "warning": "#ffc107",
        "critical": "#dc3545",
        "overdue": "#6c757d"
    }
}

# ===============================
# 🗂 إعدادات الملفات
# ===============================
USERS_FILE = "users.json"
STATE_FILE = "state.json"
MACHINES_FILE = "machines_data.json"
SESSION_DURATION = timedelta(minutes=APP_CONFIG["SESSION_DURATION_MINUTES"])
MAX_ACTIVE_USERS = APP_CONFIG["MAX_ACTIVE_USERS"]

# إنشاء رابط GitHub تلقائياً
GITHUB_EXCEL_URL = f"https://github.com/{APP_CONFIG['REPO_NAME'].split('/')[0]}/{APP_CONFIG['REPO_NAME'].split('/')[1]}/raw/{APP_CONFIG['BRANCH']}/{APP_CONFIG['FILE_PATH']}"

# ===============================
# 🔐 إدارة المستخدمين والجلسات
# ===============================
def load_users():
    """تحميل بيانات المستخدمين"""
    if not os.path.exists(USERS_FILE):
        default_users = {
            "admin": {
                "password": "admin123", 
                "role": "admin", 
                "created_at": datetime.now().isoformat(),
                "permissions": ["all"]
            }
        }
        with open(USERS_FILE, "w", encoding="utf-8") as f:
            json.dump(default_users, f, indent=4, ensure_ascii=False)
        return default_users
    
    try:
        with open(USERS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {
            "admin": {
                "password": "admin123", 
                "role": "admin", 
                "created_at": datetime.now().isoformat(),
                "permissions": ["all"]
            }
        }

def save_users(users):
    """حفظ بيانات المستخدمين"""
    try:
        with open(USERS_FILE, "w", encoding="utf-8") as f:
            json.dump(users, f, indent=4, ensure_ascii=False)
        return True
    except:
        return False

def load_state():
    """تحميل حالة الجلسات"""
    if not os.path.exists(STATE_FILE):
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump({}, f, indent=4, ensure_ascii=False)
        return {}
    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {}

def save_state(state):
    """حفظ حالة الجلسات"""
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=4, ensure_ascii=False)

def cleanup_sessions(state):
    """تنظيف الجلسات المنتهية"""
    now = datetime.now()
    changed = False
    for user, info in list(state.items()):
        if info.get("active") and "login_time" in info:
            try:
                login_time = datetime.fromisoformat(info["login_time"])
                if now - login_time > SESSION_DURATION:
                    info["active"] = False
                    info.pop("login_time", None)
                    changed = True
            except:
                info["active"] = False
                changed = True
    if changed:
        save_state(state)
    return state

# ===============================
# 🏭 إدارة بيانات الماكينات
# ===============================
def load_machines_data():
    """تحميل بيانات الماكينات من JSON"""
    if not os.path.exists(MACHINES_FILE):
        default_data = {
            "machines": [],
            "maintenance_types": APP_CONFIG["DEFAULT_MAINTENANCE_TYPES"],
            "settings": {
                "warning_days": APP_CONFIG["WARNING_DAYS_BEFORE"],
                "critical_days": APP_CONFIG["CRITICAL_DAYS_BEFORE"]
            }
        }
        with open(MACHINES_FILE, "w", encoding="utf-8") as f:
            json.dump(default_data, f, indent=4, ensure_ascii=False)
        return default_data
    
    try:
        with open(MACHINES_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {
            "machines": [],
            "maintenance_types": APP_CONFIG["DEFAULT_MAINTENANCE_TYPES"],
            "settings": {
                "warning_days": APP_CONFIG["WARNING_DAYS_BEFORE"],
                "critical_days": APP_CONFIG["CRITICAL_DAYS_BEFORE"]
            }
        }

def save_machines_data(data):
    """حفظ بيانات الماكينات في JSON"""
    try:
        with open(MACHINES_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
        return True
    except Exception as e:
        st.error(f"❌ خطأ في حفظ بيانات الماكينات: {e}")
        return False

def initialize_excel_file():
    """تهيئة ملف Excel إذا كان فارغاً"""
    if not os.path.exists(APP_CONFIG["LOCAL_FILE"]) or os.path.getsize(APP_CONFIG["LOCAL_FILE"]) == 0:
        # إنشاء DataFrame فارغ مع الأعمدة الأساسية
        df_machines = pd.DataFrame(columns=[
            "machine_id", "name", "model", "serial_number", "location", 
            "installation_date", "total_hours", "status", "notes"
        ])
        
        df_maintenance = pd.DataFrame(columns=[
            "maintenance_id", "machine_id", "maintenance_type", "last_date", 
            "last_hours", "next_date", "next_hours", "interval", "interval_unit",
            "status", "technician", "notes"
        ])
        
        df_history = pd.DataFrame(columns=[
            "history_id", "machine_id", "maintenance_type", "date", 
            "hours", "technician", "description", "cost", "parts_used"
        ])
        
        with pd.ExcelWriter(APP_CONFIG["LOCAL_FILE"], engine='openpyxl') as writer:
            df_machines.to_excel(writer, sheet_name='Machines', index=False)
            df_maintenance.to_excel(writer, sheet_name='Maintenance_Schedule', index=False)
            df_history.to_excel(writer, sheet_name='Maintenance_History', index=False)
        
        st.info("✅ تم إنشاء ملف Excel جديد ببنية منظمة")

# ===============================
# 🔄 مزامنة مع GitHub
# ===============================
def save_local_excel_and_push(sheets_dict, commit_message="Update from Oil Maintenance System"):
    """حفظ الملف محلياً ورفعه إلى GitHub"""
    try:
        # حفظ محلياً
        with pd.ExcelWriter(APP_CONFIG["LOCAL_FILE"], engine="openpyxl") as writer:
            for name, df in sheets_dict.items():
                df.to_excel(writer, sheet_name=name, index=False)
        
        # محاولة الرفع إلى GitHub إذا كان هناك توكن
        try:
            from github import Github
            
            token = st.secrets.get("github", {}).get("token", None)
            if token:
                g = Github(token)
                repo = g.get_repo(APP_CONFIG["REPO_NAME"])
                
                with open(APP_CONFIG["LOCAL_FILE"], "rb") as f:
                    content = f.read()
                
                try:
                    contents = repo.get_contents(APP_CONFIG["FILE_PATH"], ref=APP_CONFIG["BRANCH"])
                    repo.update_file(
                        path=APP_CONFIG["FILE_PATH"],
                        message=commit_message,
                        content=content,
                        sha=contents.sha,
                        branch=APP_CONFIG["BRANCH"]
                    )
                    st.success("✅ تم المزامنة مع GitHub بنجاح")
                except:
                    repo.create_file(
                        path=APP_CONFIG["FILE_PATH"],
                        message=commit_message,
                        content=content,
                        branch=APP_CONFIG["BRANCH"]
                    )
                    st.success("✅ تم إنشاء الملف على GitHub")
        
        except ImportError:
            st.info("ℹ️ مكتبة PyGithub غير مثبتة - الحفظ محلي فقط")
        except Exception as e:
            st.warning(f"⚠️ تعذر الرفع إلى GitHub: {e}")
        
        return sheets_dict
        
    except Exception as e:
        st.error(f"❌ خطأ في الحفظ: {e}")
        return None

def fetch_from_github():
    """جلب الملف من GitHub"""
    try:
        response = requests.get(GITHUB_EXCEL_URL, stream=True, timeout=15)
        response.raise_for_status()
        
        with open(APP_CONFIG["LOCAL_FILE"], "wb") as f:
            shutil.copyfileobj(response.raw, f)
        
        st.success("✅ تم تحديث البيانات من GitHub")
        return True
    except Exception as e:
        st.error(f"⚠️ فشل التحديث من GitHub: {e}")
        return False

# ===============================
# 📊 دوال حساب المؤقتات
# ===============================
def calculate_next_date(last_date_str, interval, unit):
    """حساب التاريخ التالي للصيانة"""
    if not last_date_str or pd.isna(last_date_str):
        return None
    
    try:
        last_date = pd.to_datetime(last_date_str, dayfirst=True)
        
        if unit == "أيام":
            next_date = last_date + timedelta(days=interval)
        elif unit == "أسابيع":
            next_date = last_date + timedelta(weeks=interval)
        elif unit == "شهور":
            next_date = last_date + relativedelta(months=interval)
        elif unit == "سنوات":
            next_date = last_date + relativedelta(years=interval)
        else:
            return None
        
        return next_date.strftime("%d/%m/%Y")
    except:
        return None

def calculate_next_hours(last_hours, interval):
    """حساب عدد الساعات التالي للصيانة"""
    if pd.isna(last_hours) or last_hours == "":
        return None
    
    try:
        return float(last_hours) + float(interval)
    except:
        return None

def calculate_remaining_time(next_date_str, next_hours, current_hours=None):
    """حساب الوقت المتبقي للصيانة"""
    remaining = {
        "days": None,
        "hours": None,
        "status": "normal",
        "percentage": 100
    }
    
    # حساب الوقت المتبقي حسب التاريخ
    if next_date_str and pd.notna(next_date_str):
        try:
            next_date = pd.to_datetime(next_date_str, dayfirst=True)
            today = datetime.now()
            
            days_remaining = (next_date - today).days
            
            if days_remaining < 0:
                remaining["days"] = abs(days_remaining)
                remaining["status"] = "overdue"
                remaining["percentage"] = 0
            else:
                remaining["days"] = days_remaining
                
                # تحديد حالة المؤقت
                if days_remaining <= APP_CONFIG["CRITICAL_DAYS_BEFORE"]:
                    remaining["status"] = "critical"
                    remaining["percentage"] = max(0, 100 * days_remaining / APP_CONFIG["CRITICAL_DAYS_BEFORE"])
                elif days_remaining <= APP_CONFIG["WARNING_DAYS_BEFORE"]:
                    remaining["status"] = "warning"
                    remaining["percentage"] = max(0, 100 * days_remaining / APP_CONFIG["WARNING_DAYS_BEFORE"])
                else:
                    remaining["status"] = "normal"
                    remaining["percentage"] = max(0, 100 * (1 - (days_remaining / 365)))
        
        except:
            pass
    
    # حساب الوقت المتبقي حسب الساعات
    if next_hours and pd.notna(next_hours) and current_hours and pd.notna(current_hours):
        try:
            hours_remaining = float(next_hours) - float(current_hours)
            
            if hours_remaining < 0:
                remaining["hours"] = abs(hours_remaining)
                if remaining["status"] != "overdue":
                    remaining["status"] = "overdue"
            else:
                remaining["hours"] = hours_remaining
                
                # إذا لم يكن هناك تاريخ، نستخدم الساعات لتحديد الحالة
                if not remaining["days"]:
                    if hours_remaining <= 50:
                        remaining["status"] = "critical"
                        remaining["percentage"] = max(0, 100 * hours_remaining / 50)
                    elif hours_remaining <= 100:
                        remaining["status"] = "warning"
                        remaining["percentage"] = max(0, 100 * hours_remaining / 100)
                    else:
                        remaining["status"] = "normal"
                        remaining["percentage"] = max(0, 100 * (1 - (hours_remaining / 1000)))
        
        except:
            pass
    
    return remaining

def get_status_color(status):
    """الحصول على لون الحالة"""
    colors = APP_CONFIG["COLORS"]
    return colors.get(status, "#6c757d")

# ===============================
# 🏭 واجهات إدارة الماكينات
# ===============================
def dashboard_ui():
    """لوحة القيادة الرئيسية"""
    st.header("🏭 لوحة القيادة")
    
    # تحميل البيانات
    machines_data = load_machines_data()
    
    if not machines_data["machines"]:
        st.info("ℹ️ لا توجد ماكينات مسجلة. قم بإضافة ماكينة جديدة من تبويب 'إضافة ماكينة'")
        return
    
    # عرض الإحصائيات العامة
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        total_machines = len(machines_data["machines"])
        st.metric("🛠️ عدد الماكينات", total_machines)
    
    with col2:
        active_machines = sum(1 for m in machines_data["machines"] if m.get("status") == "active")
        st.metric("✅ ماكينات نشطة", active_machines)
    
    with col3:
        critical_count = 0
        for machine in machines_data["machines"]:
            if machine.get("next_maintenance"):
                for maint in machine["next_maintenance"]:
                    if maint.get("remaining", {}).get("status") == "critical":
                        critical_count += 1
        st.metric("🔴 صيانة حرجة", critical_count, delta=f"{critical_count} تحتاج صيانة عاجلة")
    
    with col4:
        overdue_count = 0
        for machine in machines_data["machines"]:
            if machine.get("next_maintenance"):
                for maint in machine["next_maintenance"]:
                    if maint.get("remaining", {}).get("status") == "overdue":
                        overdue_count += 1
        st.metric("⏰ متأخرة", overdue_count, delta_color="inverse")
    
    st.markdown("---")
    
    # عرض الماكينات مع مؤقتات الصيانة
    st.subheader("⏰ مؤقتات الصيانة الحالية")
    
    for machine in machines_data["machines"]:
        with st.expander(f"🛠️ {machine['name']} - {machine.get('model', 'غير محدد')}", expanded=False):
            col_info1, col_info2 = st.columns([2, 1])
            
            with col_info1:
                st.markdown(f"**المكان:** {machine.get('location', 'غير محدد')}")
                st.markdown(f"**الرقم المسلسل:** {machine.get('serial_number', 'غير محدد')}")
                st.markdown(f"**إجمالي ساعات التشغيل:** {machine.get('total_hours', 0)} ساعة")
            
            with col_info2:
                status = machine.get("status", "inactive")
                status_color = "🟢" if status == "active" else "🔴"
                st.markdown(f"**الحالة:** {status_color} {status}")
            
            if machine.get("next_maintenance"):
                st.markdown("#### 📅 جدول الصيانة")
                
                for maint in machine["next_maintenance"]:
                    remaining = maint.get("remaining", {})
                    status_color = get_status_color(remaining.get("status", "normal"))
                    
                    col_maint1, col_maint2, col_maint3 = st.columns([2, 2, 1])
                    
                    with col_maint1:
                        st.markdown(f"**{maint['type_name']}**")
                        st.markdown(f"آخر: {maint.get('last_date', 'غير محدد')}")
                    
                    with col_maint2:
                        next_date = maint.get("next_date", "غير محدد")
                        next_hours = maint.get("next_hours", "غير محدد")
                        
                        if remaining.get("days") is not None:
                            st.markdown(f"**متبقي:** {remaining['days']} يوم")
                        elif remaining.get("hours") is not None:
                            st.markdown(f"**متبقي:** {remaining['hours']:.0f} ساعة")
                        
                        st.markdown(f"**التالي:** {next_date}")
                    
                    with col_maint3:
                        # شريط التقدم
                        if remaining.get("percentage") is not None:
                            st.progress(remaining["percentage"] / 100)
                        
                        # زر تسجيل الصيانة
                        if st.button("✅ تمت", key=f"done_{machine['id']}_{maint['type_id']}"):
                            record_maintenance(machine['id'], maint['type_id'])
            
            else:
                st.info("ℹ️ لا توجد صيانة مجدولة لهذه الماكينة")

def add_machine_ui():
    """إضافة ماكينة جديدة"""
    st.header("➕ إضافة ماكينة جديدة")
    
    machines_data = load_machines_data()
    
    with st.form("add_machine_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            machine_name = st.text_input("اسم الماكينة", placeholder="مثال: مخرطة CNC 1")
            machine_model = st.text_input("الموديل", placeholder="مثال: XYZ-2000")
            serial_number = st.text_input("الرقم المسلسل")
        
        with col2:
            location = st.text_input("المكان/الموقع", placeholder="مثال: ورشة الإنتاج")
            installation_date = st.date_input("تاريخ التركيب", datetime.now())
            total_hours = st.number_input("إجمالي ساعات التشغيل الحالية", min_value=0, value=0)
        
        st.markdown("---")
        st.subheader("⚙️ إعدادات الصيانة")
        
        # اختيار أنواع الصيانة
        maintenance_types = machines_data["maintenance_types"]
        selected_types = []
        
        cols = st.columns(3)
        for idx, maint_type in enumerate(maintenance_types):
            with cols[idx % 3]:
                if st.checkbox(maint_type["name"], value=True, key=f"type_{maint_type['id']}"):
                    custom_interval = st.number_input(
                        f"الفترة بين {maint_type['name']} ({maint_type['unit']})",
                        min_value=1,
                        value=maint_type["default_interval"],
                        key=f"interval_{maint_type['id']}"
                    )
                    
                    selected_types.append({
                        "type_id": maint_type["id"],
                        "type_name": maint_type["name"],
                        "interval": custom_interval,
                        "unit": maint_type["unit"],
                        "last_date": None,
                        "last_hours": total_hours
                    })
        
        if st.form_submit_button("💾 إضافة الماكينة"):
            if not machine_name:
                st.warning("⚠️ الرجاء إدخال اسم الماكينة")
                return
            
            # إنجار معرف فريد للماكينة
            machine_id = str(uuid.uuid4())[:8]
            
            # حساب التواريخ التالية للصيانة
            next_maintenance = []
            for maint in selected_types:
                next_date = None
                next_hours = None
                
                if maint["unit"] in ["أيام", "أسابيع", "شهور", "سنوات"]:
                    next_date = calculate_next_date(
                        installation_date.strftime("%d/%m/%Y"),
                        maint["interval"],
                        maint["unit"]
                    )
                else:
                    next_hours = calculate_next_hours(total_hours, maint["interval"])
                
                remaining = calculate_remaining_time(next_date, next_hours, total_hours)
                
                next_maintenance.append({
                    **maint,
                    "next_date": next_date,
                    "next_hours": next_hours,
                    "remaining": remaining
                })
            
            # إنشاء كائن الماكينة
            new_machine = {
                "id": machine_id,
                "name": machine_name,
                "model": machine_model,
                "serial_number": serial_number,
                "location": location,
                "installation_date": installation_date.strftime("%d/%m/%Y"),
                "total_hours": total_hours,
                "status": "active",
                "notes": "",
                "next_maintenance": next_maintenance,
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat()
            }
            
            # إضافة الماكينة للبيانات
            machines_data["machines"].append(new_machine)
            
            # حفظ في JSON
            if save_machines_data(machines_data):
                # تحديث ملف Excel
                update_excel_with_machines(machines_data)
                st.success(f"✅ تم إضافة الماكينة '{machine_name}' بنجاح!")
                st.balloons()
                
                # عرض ملخص
                with st.expander("📋 ملخص الماكينة المضافة", expanded=True):
                    st.json(new_machine)
            else:
                st.error("❌ فشل في حفظ الماكينة")

def record_maintenance(machine_id, maintenance_type_id):
    """تسجيل إتمام صيانة"""
    machines_data = load_machines_data()
    
    # البحث عن الماكينة
    for machine in machines_data["machines"]:
        if machine["id"] == machine_id:
            # البحث عن نوع الصيانة
            for maint in machine.get("next_maintenance", []):
                if maint["type_id"] == maintenance_type_id:
                    # تسجيل التاريخ الحالي كآخر صيانة
                    maint["last_date"] = datetime.now().strftime("%d/%m/%Y")
                    maint["last_hours"] = machine.get("total_hours", 0)
                    
                    # حساب التاريخ التالي
                    if maint["unit"] in ["أيام", "أسابيع", "شهور", "سنوات"]:
                        maint["next_date"] = calculate_next_date(
                            maint["last_date"],
                            maint["interval"],
                            maint["unit"]
                        )
                    else:
                        maint["next_hours"] = calculate_next_hours(
                            maint["last_hours"],
                            maint["interval"]
                        )
                    
                    # تحديث وقت التعديل
                    machine["updated_at"] = datetime.now().isoformat()
                    
                    # حفظ التغييرات
                    if save_machines_data(machines_data):
                        update_excel_with_machines(machines_data)
                        st.success("✅ تم تسجيل الصيانة بنجاح!")
                        st.rerun()
                    break
            break

def update_machine_hours_ui():
    """تحديث ساعات تشغيل الماكينة"""
    st.header("🕐 تحديث ساعات التشغيل")
    
    machines_data = load_machines_data()
    
    if not machines_data["machines"]:
        st.info("ℹ️ لا توجد ماكينات مسجلة")
        return
    
    # اختيار الماكينة
    machine_options = {m["name"]: m["id"] for m in machines_data["machines"]}
    selected_machine_name = st.selectbox("اختر الماكينة", list(machine_options.keys()))
    machine_id = machine_options[selected_machine_name]
    
    # العثور على الماكينة
    machine = next((m for m in machines_data["machines"] if m["id"] == machine_id), None)
    
    if machine:
        current_hours = machine.get("total_hours", 0)
        
        col1, col2 = st.columns(2)
        with col1:
            new_hours = st.number_input(
                "الساعات الجديدة",
                min_value=float(current_hours),
                value=float(current_hours) + 8.0,
                step=1.0
            )
        
        with col2:
            operation_date = st.date_input("تاريخ التشغيل", datetime.now())
        
        if st.button("💾 تحديث الساعات", key="update_hours"):
            # تحديث ساعات الماكينة
            machine["total_hours"] = new_hours
            machine["updated_at"] = datetime.now().isoformat()
            
            # تحديث مؤقتات الصيانة بناءً على الساعات الجديدة
            for maint in machine.get("next_maintenance", []):
                if maint["unit"] == "ساعات":
                    maint["remaining"] = calculate_remaining_time(
                        maint.get("next_date"),
                        maint.get("next_hours"),
                        new_hours
                    )
            
            # حفظ التغييرات
            if save_machines_data(machines_data):
                update_excel_with_machines(machines_data)
                st.success(f"✅ تم تحديث ساعات الماكينة إلى {new_hours} ساعة")
                st.rerun()

def maintenance_management_ui():
    """إدارة جدول الصيانة"""
    st.header("📊 إدارة الصيانة")
    
    machines_data = load_machines_data()
    
    # تبويبات للإدارة
    maint_tabs = st.tabs(["📅 عرض جميع المؤقتات", "⚙️ تعديل جدول الصيانة", "➕ إضافة نوع صيانة جديد"])
    
    with maint_tabs[0]:
        st.subheader("📅 جدول الصيانة الشامل")
        
        if not machines_data["machines"]:
            st.info("ℹ️ لا توجد ماكينات مسجلة")
            return
        
        # إنشاء جدول شامل للصيانة
        all_maintenance = []
        
        for machine in machines_data["machines"]:
            for maint in machine.get("next_maintenance", []):
                remaining = maint.get("remaining", {})
                
                all_maintenance.append({
                    "الماكينة": machine["name"],
                    "نوع الصيانة": maint["type_name"],
                    "آخر تاريخ": maint.get("last_date", "غير مسجل"),
                    "التاريخ التالي": maint.get("next_date", "غير محدد"),
                    "الساعات التالية": maint.get("next_hours", "غير محدد"),
                    "المتبقي (أيام)": remaining.get("days", "-"),
                    "المتبقي (ساعات)": remaining.get("hours", "-"),
                    "الحالة": remaining.get("status", "normal"),
                    "معرف الماكينة": machine["id"],
                    "معرف الصيانة": maint["type_id"]
                })
        
        if all_maintenance:
            # تحويل إلى DataFrame
            df = pd.DataFrame(all_maintenance)
            
            # فلترة حسب الحالة
            status_filter = st.multiselect(
                "فلترة حسب الحالة",
                ["normal", "warning", "critical", "overdue"],
                default=["critical", "warning", "overdue"]
            )
            
            if status_filter:
                df = df[df["الحالة"].isin(status_filter)]
            
            # تلوين الصفوف حسب الحالة
            def color_status(val):
                color_map = {
                    "normal": "background-color: #d4edda",
                    "warning": "background-color: #fff3cd",
                    "critical": "background-color: #f8d7da",
                    "overdue": "background-color: #e2e3e5"
                }
                return color_map.get(val, "")
            
            styled_df = df.style.applymap(color_status, subset=["الحالة"])
            
            st.dataframe(styled_df, use_container_width=True, height=400)
            
            # خيارات التصدير
            if st.button("📥 تصدير إلى Excel"):
                buffer = io.BytesIO()
                with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                    df.to_excel(writer, sheet_name='جدول_الصيانة', index=False)
                
                st.download_button(
                    label="💾 تنزيل الملف",
                    data=buffer.getvalue(),
                    file_name=f"جدول_الصيانة_{datetime.now().strftime('%Y%m%d')}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
        else:
            st.info("ℹ️ لا توجد صيانة مجدولة")
    
    with maint_tabs[1]:
        st.subheader("⚙️ تعديل جدول الصيانة")
        
        if not machines_data["machines"]:
            st.info("ℹ️ لا توجد ماكينات مسجلة")
            return
        
        # اختيار الماكينة
        machine_options = {f"{m['name']} ({m['model']})": m['id'] for m in machines_data["machines"]}
        selected_machine = st.selectbox("اختر الماكينة", list(machine_options.keys()))
        machine_id = machine_options[selected_machine]
        
        # العثور على الماكينة
        machine = next((m for m in machines_data["machines"] if m["id"] == machine_id), None)
        
        if machine and machine.get("next_maintenance"):
            st.markdown(f"#### تعديل صيانة: {machine['name']}")
            
            for maint in machine["next_maintenance"]:
                with st.expander(f"{maint['type_name']}", expanded=False):
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        new_last_date = st.text_input(
                            "آخر تاريخ صيانة",
                            value=maint.get("last_date", ""),
                            key=f"last_{machine_id}_{maint['type_id']}"
                        )
                        
                        new_last_hours = st.number_input(
                            "آخر ساعات صيانة",
                            value=float(maint.get("last_hours", 0)),
                            key=f"hours_{machine_id}_{maint['type_id']}"
                        )
                    
                    with col2:
                        new_interval = st.number_input(
                            f"الفترة بين الصيانة ({maint['unit']})",
                            min_value=1,
                            value=maint["interval"],
                            key=f"interval_{machine_id}_{maint['type_id']}"
                        )
                    
                    if st.button("💾 حفظ التعديلات", key=f"save_{machine_id}_{maint['type_id']}"):
                        # تحديث البيانات
                        maint["last_date"] = new_last_date if new_last_date else None
                        maint["last_hours"] = new_last_hours
                        maint["interval"] = new_interval
                        
                        # إعادة حساب التواريخ التالية
                        if maint["unit"] in ["أيام", "أسابيع", "شهور", "سنوات"]:
                            maint["next_date"] = calculate_next_date(
                                new_last_date,
                                new_interval,
                                maint["unit"]
                            )
                        else:
                            maint["next_hours"] = calculate_next_hours(
                                new_last_hours,
                                new_interval
                            )
                        
                        # تحديث وقت التعديل
                        machine["updated_at"] = datetime.now().isoformat()
                        
                        # حفظ التغييرات
                        if save_machines_data(machines_data):
                            update_excel_with_machines(machines_data)
                            st.success(f"✅ تم تحديث {maint['type_name']}")
                            st.rerun()
    
    with maint_tabs[2]:
        st.subheader("➕ إضافة نوع صيانة جديد")
        
        with st.form("add_maintenance_type_form"):
            col1, col2 = st.columns(2)
            
            with col1:
                type_name = st.text_input("اسم نوع الصيانة", placeholder="مثال: تنظيف المرشحات")
                type_id = st.text_input("المعرف (ID)", placeholder="مثال: filter_cleaning")
            
            with col2:
                unit = st.selectbox("وحدة القياس", ["ساعات", "أيام", "أسابيع", "شهور", "سنوات"])
                default_interval = st.number_input("الفترة الافتراضية", min_value=1, value=100)
            
            if st.form_submit_button("💾 إضافة نوع الصيانة"):
                if not type_name or not type_id:
                    st.warning("⚠️ الرجاء إدخال الاسم والمعرف")
                    return
                
                # التحقق من عدم تكرار المعرف
                existing_ids = [t["id"] for t in machines_data["maintenance_types"]]
                if type_id in existing_ids:
                    st.error("❌ المعرف موجود مسبقاً")
                    return
                
                # إضافة نوع الصيانة الجديد
                new_type = {
                    "id": type_id,
                    "name": type_name,
                    "unit": unit,
                    "default_interval": default_interval
                }
                
                machines_data["maintenance_types"].append(new_type)
                
                if save_machines_data(machines_data):
                    st.success(f"✅ تم إضافة نوع الصيانة '{type_name}' بنجاح")
                    st.rerun()

def timers_dashboard_ui():
    """لوحة المؤقتات التنازلية"""
    st.header("⏰ المؤقتات التنازلية")
    
    machines_data = load_machines_data()
    
    if not machines_data["machines"]:
        st.info("ℹ️ لا توجد ماكينات مسجلة")
        return
    
    # فلترة المؤقتات
    st.subheader("🔍 فلترة المؤقتات")
    
    filter_col1, filter_col2, filter_col3 = st.columns(3)
    
    with filter_col1:
        machine_filter = st.multiselect(
            "الماكينات",
            [m["name"] for m in machines_data["machines"]],
            default=None
        )
    
    with filter_col2:
        status_filter = st.multiselect(
            "الحالة",
            ["normal", "warning", "critical", "overdue"],
            default=["critical", "warning"]
        )
    
    with filter_col3:
        type_filter = st.multiselect(
            "نوع الصيانة",
            list(set([t["name"] for t in machines_data["maintenance_types"]]))
        )
    
    st.markdown("---")
    
    # جمع جميع المؤقتات
    all_timers = []
    
    for machine in machines_data["machines"]:
        if machine_filter and machine["name"] not in machine_filter:
            continue
        
        for maint in machine.get("next_maintenance", []):
            if type_filter and maint["type_name"] not in type_filter:
                continue
            
            remaining = maint.get("remaining", {})
            
            if status_filter and remaining.get("status") not in status_filter:
                continue
            
            all_timers.append({
                "machine": machine["name"],
                "type": maint["type_name"],
                "remaining": remaining,
                "next_date": maint.get("next_date"),
                "next_hours": maint.get("next_hours"),
                "machine_id": machine["id"],
                "type_id": maint["type_id"]
            })
    
    # عرض المؤقتات
    if not all_timers:
        st.info("ℹ️ لا توجد مؤقتات مطابقة للفلتر")
        return
    
    # ترتيب المؤقتات (الأكثر حراجة أولاً)
    status_order = {"overdue": 0, "critical": 1, "warning": 2, "normal": 3}
    all_timers.sort(key=lambda x: status_order.get(x["remaining"].get("status", "normal"), 4))
    
    # عرض المؤقتات في أعمدة
    cols_per_row = 3
    for i in range(0, len(all_timers), cols_per_row):
        cols = st.columns(cols_per_row)
        
        for j in range(cols_per_row):
            idx = i + j
            if idx < len(all_timers):
                timer = all_timers[idx]
                remaining = timer["remaining"]
                status = remaining.get("status", "normal")
                color = get_status_color(status)
                
                with cols[j]:
                    # بطاقة المؤقت
                    with st.container():
                        st.markdown(f"""
                        <div style="border: 2px solid {color}; border-radius: 10px; padding: 15px; margin: 10px 0;">
                            <h4 style="color: {color}; margin: 0;">{timer['machine']}</h4>
                            <p style="margin: 5px 0;"><strong>{timer['type']}</strong></p>
                        """, unsafe_allow_html=True)
                        
                        # عرض الوقت المتبقي
                        if remaining.get("days") is not None:
                            days = remaining["days"]
                            if days < 0:
                                st.markdown(f"<p style='color: {color};'><strong>متأخر: {abs(days)} يوم</strong></p>", unsafe_allow_html=True)
                            else:
                                st.markdown(f"<p style='color: {color};'><strong>متبقي: {days} يوم</strong></p>", unsafe_allow_html=True)
                        
                        elif remaining.get("hours") is not None:
                            hours = remaining["hours"]
                            if hours < 0:
                                st.markdown(f"<p style='color: {color};'><strong>متأخر: {abs(hours):.0f} ساعة</strong></p>", unsafe_allow_html=True)
                            else:
                                st.markdown(f"<p style='color: {color};'><strong>متبقي: {hours:.0f} ساعة</strong></p>", unsafe_allow_html=True)
                        
                        # التاريخ التالي
                        if timer["next_date"]:
                            st.markdown(f"<p>التاريخ التالي: {timer['next_date']}</p>", unsafe_allow_html=True)
                        
                        # شريط التقدم
                        if remaining.get("percentage") is not None:
                            st.progress(remaining["percentage"] / 100)
                        
                        st.markdown("</div>", unsafe_allow_html=True)
                        
                        # زر تسجيل الإنجاز
                        if st.button("✅ تمت الصيانة", key=f"done_timer_{timer['machine_id']}_{timer['type_id']}"):
                            record_maintenance(timer["machine_id"], timer["type_id"])
    
    # إحصائيات المؤقتات
    st.markdown("---")
    st.subheader("📊 إحصائيات المؤقتات")
    
    status_counts = {"normal": 0, "warning": 0, "critical": 0, "overdue": 0}
    for timer in all_timers:
        status = timer["remaining"].get("status", "normal")
        status_counts[status] = status_counts.get(status, 0) + 1
    
    # مخطط دائري
    try:
        fig = go.Figure(data=[go.Pie(
            labels=list(status_counts.keys()),
            values=list(status_counts.values()),
            marker_colors=[get_status_color(s) for s in status_counts.keys()]
        )])
        
        fig.update_layout(
            title="توزيع حالات المؤقتات",
            height=400
        )
        
        st.plotly_chart(fig, use_container_width=True)
    except:
        # عرض جدول بديل
        stats_df = pd.DataFrame({
            "الحالة": list(status_counts.keys()),
            "العدد": list(status_counts.values()),
            "النسبة": [f"{(count/len(all_timers)*100):.1f}%" for count in status_counts.values()]
        })
        
        st.dataframe(stats_df, use_container_width=True)

def reports_ui():
    """التقارير والإحصائيات"""
    st.header("📈 التقارير والإحصائيات")
    
    machines_data = load_machines_data()
    
    if not machines_data["machines"]:
        st.info("ℹ️ لا توجد بيانات لتوليد التقارير")
        return
    
    # تبويبات التقارير
    report_tabs = st.tabs(["📊 إحصائيات عامة", "📅 تقرير الصيانة", "📉 تحليل الأداء", "📄 تصدير التقارير"])
    
    with report_tabs[0]:
        st.subheader("📊 إحصائيات النظام")
        
        # إحصائيات عامة
        col1, col2 = st.columns(2)
        
        with col1:
            # حساب إجمالي ساعات التشغيل
            total_hours = sum(m.get("total_hours", 0) for m in machines_data["machines"])
            st.metric("🕐 إجمالي ساعات التشغيل", f"{total_hours:,} ساعة")
            
            # متوسط ساعات التشغيل
            avg_hours = total_hours / len(machines_data["machines"]) if machines_data["machines"] else 0
            st.metric("📊 متوسط الساعات", f"{avg_hours:,.0f} ساعة")
            
            # عدد أنواع الصيانة
            maint_types_count = len(machines_data["maintenance_types"])
            st.metric("⚙️ أنواع الصيانة", maint_types_count)
        
        with col2:
            # توزيع الماكينات حسب الموقع
            locations = {}
            for machine in machines_data["machines"]:
                loc = machine.get("location", "غير محدد")
                locations[loc] = locations.get(loc, 0) + 1
            
            st.markdown("#### 🗺️ توزيع الماكينات حسب الموقع")
            for loc, count in locations.items():
                st.markdown(f"**{loc}:** {count} ماكينة")
        
        # مخطط أعمدة لتوزيع الماكينات
        try:
            machines_df = pd.DataFrame(machines_data["machines"])
            
            if not machines_df.empty and "location" in machines_df.columns:
                location_counts = machines_df["location"].value_counts()
                
                fig = px.bar(
                    x=location_counts.index,
                    y=location_counts.values,
                    title="توزيع الماكينات حسب الموقع",
                    labels={"x": "الموقع", "y": "عدد الماكينات"},
                    color=location_counts.values,
                    color_continuous_scale="Viridis"
                )
                
                st.plotly_chart(fig, use_container_width=True)
        except:
            pass
    
    with report_tabs[1]:
        st.subheader("📅 تقرير الصيانة الشهري")
        
        # فلترة حسب الشهر
        current_year = datetime.now().year
        year = st.selectbox("السنة", range(current_year-5, current_year+1), index=5)
        month = st.selectbox("الشهر", range(1, 13), index=datetime.now().month-1)
        
        # جمع بيانات الصيانة للشهر المحدد
        monthly_maintenance = []
        
        for machine in machines_data["machines"]:
            for maint in machine.get("next_maintenance", []):
                next_date = maint.get("next_date")
                if next_date:
                    try:
                        maint_date = pd.to_datetime(next_date, dayfirst=True)
                        if maint_date.year == year and maint_date.month == month:
                            monthly_maintenance.append({
                                "الماكينة": machine["name"],
                                "نوع الصيانة": maint["type_name"],
                                "التاريخ المخطط": next_date,
                                "الحالة": maint.get("remaining", {}).get("status", "normal"),
                                "المكان": machine.get("location", "غير محدد")
                            })
                    except:
                        pass
        
        if monthly_maintenance:
            monthly_df = pd.DataFrame(monthly_maintenance)
            
            # توزيع الصيانة حسب النوع
            type_counts = monthly_df["نوع الصيانة"].value_counts()
            
            col1, col2 = st.columns([2, 1])
            
            with col1:
                st.dataframe(monthly_df, use_container_width=True, height=300)
            
            with col2:
                st.markdown("#### 📊 توزيع الصيانة")
                for type_name, count in type_counts.items():
                    st.markdown(f"**{type_name}:** {count}")
            
            # مخطط دائري لتوزيع الصيانة
            try:
                fig = px.pie(
                    values=type_counts.values,
                    names=type_counts.index,
                    title=f"توزيع الصيانة لشهر {month}/{year}"
                )
                st.plotly_chart(fig, use_container_width=True)
            except:
                pass
        else:
            st.info(f"ℹ️ لا توجد صيانة مجدولة لشهر {month}/{year}")
    
    with report_tabs[2]:
        st.subheader("📉 تحليل أداء الصيانة")
        
        # حساب نسبة التزام الصيانة
        total_scheduled = 0
        total_on_time = 0
        total_delayed = 0
        
        for machine in machines_data["machines"]:
            for maint in machine.get("next_maintenance", []):
                total_scheduled += 1
                status = maint.get("remaining", {}).get("status", "normal")
                
                if status == "overdue":
                    total_delayed += 1
                else:
                    total_on_time += 1
        
        if total_scheduled > 0:
            on_time_percentage = (total_on_time / total_scheduled) * 100
            delayed_percentage = (total_delayed / total_scheduled) * 100
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric("📅 مجدول", total_scheduled)
            
            with col2:
                st.metric("✅ في الوقت", f"{on_time_percentage:.1f}%")
            
            with col3:
                st.metric("⏰ متأخر", f"{delayed_percentage:.1f}%")
            
            # مخطط شريطي
            performance_data = {
                "الفئة": ["في الوقت", "متأخر"],
                "النسبة": [on_time_percentage, delayed_percentage]
            }
            
            try:
                fig = px.bar(
                    performance_data,
                    x="الفئة",
                    y="النسبة",
                    title="نسبة التزام الصيانة",
                    color="الفئة",
                    color_discrete_map={"في الوقت": "#28a745", "متأخر": "#dc3545"}
                )
                st.plotly_chart(fig, use_container_width=True)
            except:
                pass
    
    with report_tabs[3]:
        st.subheader("📄 تصدير التقارير")
        
        col1, col2 = st.columns(2)
        
        with col1:
            report_type = st.selectbox(
                "نوع التقرير",
                ["تقرير الماكينات", "جدول الصيانة", "تقرير المؤقتات", "التقرير الشامل"]
            )
        
        with col2:
            format_type = st.radio("التنسيق", ["Excel", "PDF", "CSV"])
        
        if st.button("🚀 إنشاء وتصدير التقرير", type="primary"):
            with st.spinner("جاري إنشاء التقرير..."):
                # إنشاء DataFrame بناءً على نوع التقرير
                if report_type == "تقرير الماكينات":
                    data = []
                    for machine in machines_data["machines"]:
                        data.append({
                            "اسم الماكينة": machine["name"],
                            "الموديل": machine.get("model", ""),
                            "الرقم المسلسل": machine.get("serial_number", ""),
                            "المكان": machine.get("location", ""),
                            "تاريخ التركيب": machine.get("installation_date", ""),
                            "ساعات التشغيل": machine.get("total_hours", 0),
                            "الحالة": machine.get("status", ""),
                            "عدد أنواع الصيانة": len(machine.get("next_maintenance", []))
                        })
                    
                    df = pd.DataFrame(data)
                
                elif report_type == "جدول الصيانة":
                    data = []
                    for machine in machines_data["machines"]:
                        for maint in machine.get("next_maintenance", []):
                            remaining = maint.get("remaining", {})
                            data.append({
                                "الماكينة": machine["name"],
                                "نوع الصيانة": maint["type_name"],
                                "آخر تاريخ": maint.get("last_date", ""),
                                "التاريخ التالي": maint.get("next_date", ""),
                                "الساعات التالية": maint.get("next_hours", ""),
                                "المتبقي (أيام)": remaining.get("days", ""),
                                "المتبقي (ساعات)": remaining.get("hours", ""),
                                "الحالة": remaining.get("status", ""),
                                "الفترة": f"{maint['interval']} {maint['unit']}"
                            })
                    
                    df = pd.DataFrame(data)
                
                elif report_type == "تقرير المؤقتات":
                    data = []
                    for machine in machines_data["machines"]:
                        for maint in machine.get("next_maintenance", []):
                            remaining = maint.get("remaining", {})
                            data.append({
                                "الماكينة": machine["name"],
                                "نوع الصيانة": maint["type_name"],
                                "حالة المؤقت": remaining.get("status", ""),
                                "نسبة الإنجاز": f"{remaining.get('percentage', 0):.1f}%",
                                "ملاحظات": "🔴 تحتاج صيانة عاجلة" if remaining.get("status") == "critical" else
                                          "🟡 تحتاج صيانة قريباً" if remaining.get("status") == "warning" else
                                          "🟢 تحت السيطرة" if remaining.get("status") == "normal" else
                                          "⚫ متأخرة"
                            })
                    
                    df = pd.DataFrame(data)
                
                else:  # التقرير الشامل
                    # سيتضمن جميع البيانات
                    df_machines = pd.DataFrame(machines_data["machines"])
                    
                    # إنشاء ملف Excel متعدد الأوراق
                    buffer = io.BytesIO()
                    with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                        # ورقة الماكينات
                        machines_df = pd.DataFrame([{
                            "اسم الماكينة": m["name"],
                            "الموديل": m.get("model", ""),
                            "الرقم المسلسل": m.get("serial_number", ""),
                            "المكان": m.get("location", ""),
                            "ساعات التشغيل": m.get("total_hours", 0)
                        } for m in machines_data["machines"]])
                        machines_df.to_excel(writer, sheet_name='الماكينات', index=False)
                        
                        # ورقة الصيانة
                        maint_data = []
                        for machine in machines_data["machines"]:
                            for maint in machine.get("next_maintenance", []):
                                maint_data.append({
                                    "الماكينة": machine["name"],
                                    "نوع الصيانة": maint["type_name"],
                                    "التاريخ التالي": maint.get("next_date", ""),
                                    "الحالة": maint.get("remaining", {}).get("status", "")
                                })
                        
                        maint_df = pd.DataFrame(maint_data)
                        maint_df.to_excel(writer, sheet_name='الصيانة', index=False)
                        
                        # ورقة الإحصائيات
                        stats_data = {
                            "المعيار": ["عدد الماكينات", "إجمالي ساعات التشغيل", "عدد أنواع الصيانة", "تاريخ التقرير"],
                            "القيمة": [
                                len(machines_data["machines"]),
                                sum(m.get("total_hours", 0) for m in machines_data["machines"]),
                                len(machines_data["maintenance_types"]),
                                datetime.now().strftime("%d/%m/%Y %H:%M")
                            ]
                        }
                        
                        stats_df = pd.DataFrame(stats_data)
                        stats_df.to_excel(writer, sheet_name='الإحصائيات', index=False)
                    
                    file_data = buffer.getvalue()
                    file_name = f"التقرير_الشامل_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx"
                    mime_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                
                if report_type != "التقرير الشامل":
                    if format_type == "Excel":
                        buffer = io.BytesIO()
                        with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                            df.to_excel(writer, index=False, sheet_name='تقرير')
                        file_data = buffer.getvalue()
                        file_name = f"{report_type}_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx"
                        mime_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    
                    elif format_type == "CSV":
                        file_data = df.to_csv(index=False, encoding='utf-8-sig')
                        file_name = f"{report_type}_{datetime.now().strftime('%Y%m%d_%H%M')}.csv"
                        mime_type = "text/csv"
                    
                    else:  # PDF
                        # يمكن إضافة مكتبة لإنشاء PDF هنا
                        st.info("⏳ تصدير PDF قيد التطوير")
                        return
                
                # زر التحميل
                st.download_button(
                    label="📥 تنزيل التقرير",
                    data=file_data,
                    file_name=file_name,
                    mime=mime_type
                )
                
                st.success("✅ تم إنشاء التقرير بنجاح!")

def update_excel_with_machines(machines_data):
    """تحديث ملف Excel ببيانات الماكينات"""
    try:
        # إنشاء DataFrames
        machines_list = []
        maintenance_list = []
        
        for machine in machines_data["machines"]:
            # بيانات الماكينة الأساسية
            machines_list.append({
                "machine_id": machine["id"],
                "name": machine["name"],
                "model": machine.get("model", ""),
                "serial_number": machine.get("serial_number", ""),
                "location": machine.get("location", ""),
                "installation_date": machine.get("installation_date", ""),
                "total_hours": machine.get("total_hours", 0),
                "status": machine.get("status", "active"),
                "notes": machine.get("notes", ""),
                "created_at": machine.get("created_at", ""),
                "updated_at": machine.get("updated_at", "")
            })
            
            # بيانات الصيانة
            for maint in machine.get("next_maintenance", []):
                maintenance_list.append({
                    "maintenance_id": f"{machine['id']}_{maint['type_id']}",
                    "machine_id": machine["id"],
                    "machine_name": machine["name"],
                    "maintenance_type": maint["type_name"],
                    "maintenance_type_id": maint["type_id"],
                    "last_date": maint.get("last_date", ""),
                    "last_hours": maint.get("last_hours", 0),
                    "next_date": maint.get("next_date", ""),
                    "next_hours": maint.get("next_hours", 0),
                    "interval": maint["interval"],
                    "interval_unit": maint["unit"],
                    "status": maint.get("remaining", {}).get("status", "normal"),
                    "remaining_days": maint.get("remaining", {}).get("days", 0),
                    "remaining_hours": maint.get("remaining", {}).get("hours", 0),
                    "updated_at": machine.get("updated_at", "")
                })
        
        # إنشاء DataFrames
        df_machines = pd.DataFrame(machines_list)
        df_maintenance = pd.DataFrame(maintenance_list)
        
        # أنواع الصيانة
        df_types = pd.DataFrame(machines_data["maintenance_types"])
        
        # حفظ في ملف Excel
        sheets_dict = {
            "Machines": df_machines,
            "Maintenance_Schedule": df_maintenance,
            "Maintenance_Types": df_types
        }
        
        # استخدام دالة الحفظ المشتركة
        save_local_excel_and_push(
            sheets_dict,
            f"تحديث بيانات الصيانة - {datetime.now().strftime('%d/%m/%Y %H:%M')}"
        )
        
        return True
    
    except Exception as e:
        st.error(f"❌ خطأ في تحديث ملف Excel: {e}")
        return False

def settings_ui():
    """إعدادات النظام"""
    st.header("⚙️ إعدادات النظام")
    
    machines_data = load_machines_data()
    settings = machines_data.get("settings", {})
    
    with st.form("system_settings_form"):
        st.subheader("⚙️ إعدادات المؤقتات")
        
        col1, col2 = st.columns(2)
        
        with col1:
            warning_days = st.number_input(
                "الأيام للإشعار التحذيري",
                min_value=1,
                value=settings.get("warning_days", APP_CONFIG["WARNING_DAYS_BEFORE"]),
                help="عدد الأيام قبل موعد الصيانة لتغيير الحالة إلى تحذير"
            )
        
        with col2:
            critical_days = st.number_input(
                "الأيام للإشعار الحرج",
                min_value=1,
                value=settings.get("critical_days", APP_CONFIG["CRITICAL_DAYS_BEFORE"]),
                help="عدد الأيام قبل موعد الصيانة لتغيير الحالة إلى حرج"
            )
        
        st.subheader("🔄 إدارة البيانات")
        
        data_col1, data_col2 = st.columns(2)
        
        with data_col1:
            if st.form_submit_button("💾 حفظ الإعدادات", type="primary"):
                machines_data["settings"] = {
                    "warning_days": warning_days,
                    "critical_days": critical_days
                }
                
                if save_machines_data(machines_data):
                    st.success("✅ تم حفظ الإعدادات بنجاح!")
                    st.rerun()
        
        with data_col2:
            if st.button("🔄 تحديث جميع المؤقتات", key="refresh_all_timers"):
                # إعادة حساب جميع المؤقتات
                for machine in machines_data["machines"]:
                    for maint in machine.get("next_maintenance", []):
                        maint["remaining"] = calculate_remaining_time(
                            maint.get("next_date"),
                            maint.get("next_hours"),
                            machine.get("total_hours", 0)
                        )
                
                if save_machines_data(machines_data):
                    update_excel_with_machines(machines_data)
                    st.success("✅ تم تحديث جميع المؤقتات!")
                    st.rerun()
    
    st.markdown("---")
    
    # إدارة النسخ الاحتياطي
    st.subheader("💾 النسخ الاحتياطي")
    
    col_backup1, col_backup2 = st.columns(2)
    
    with col_backup1:
        if st.button("📥 تنزيل نسخة احتياطية", key="backup_download"):
            # تنزيل ملف JSON
            backup_data = json.dumps(machines_data, indent=4, ensure_ascii=False)
            
            st.download_button(
                label="💾 تحميل ملف النسخ الاحتياطي",
                data=backup_data,
                file_name=f"maintenance_backup_{datetime.now().strftime('%Y%m%d_%H%M')}.json",
                mime="application/json"
            )
    
    with col_backup2:
        uploaded_file = st.file_uploader("استعادة من نسخة احتياطية", type=["json"])
        
        if uploaded_file is not None:
            if st.button("🔄 استعادة البيانات", key="restore_backup"):
                try:
                    restored_data = json.load(uploaded_file)
                    
                    if "machines" in restored_data and "maintenance_types" in restored_data:
                        if save_machines_data(restored_data):
                            update_excel_with_machines(restored_data)
                            st.success("✅ تم استعادة البيانات بنجاح!")
                            st.rerun()
                    else:
                        st.error("❌ ملف النسخ الاحتياطي غير صالح")
                except Exception as e:
                    st.error(f"❌ خطأ في استعادة البيانات: {e}")

# ===============================
# 🔐 تسجيل الدخول
# ===============================
def login_ui():
    """واجهة تسجيل الدخول"""
    st.title(f"{APP_CONFIG['APP_ICON']} تسجيل الدخول - {APP_CONFIG['APP_TITLE']}")
    
    users = load_users()
    state = load_state()
    
    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False
    
    if not st.session_state.logged_in:
        col1, col2 = st.columns([1, 2])
        
        with col1:
            st.image("https://cdn-icons-png.flaticon.com/512/3067/3067256.png", width=100)
        
        with col2:
            username = st.text_input("👤 اسم المستخدم")
            password = st.text_input("🔑 كلمة المرور", type="password")
            
            if st.button("🚀 تسجيل الدخول", type="primary", use_container_width=True):
                if username in users and users[username]["password"] == password:
                    # تحديث حالة الجلسة
                    state[username] = {
                        "active": True,
                        "login_time": datetime.now().isoformat()
                    }
                    save_state(state)
                    
                    st.session_state.logged_in = True
                    st.session_state.username = username
                    st.session_state.user_role = users[username].get("role", "user")
                    
                    st.success(f"✅ مرحباً {username}!")
                    st.rerun()
                else:
                    st.error("❌ اسم المستخدم أو كلمة المرور غير صحيحة")
    
    else:
        # شريط معلومات الجلسة
        st.success(f"✅ مسجل الدخول كـ: {st.session_state.username}")
        
        if st.button("🚪 تسجيل الخروج", key="logout_main"):
            state[st.session_state.username]["active"] = False
            save_state(state)
            
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            
            st.rerun()
        
        return True
    
    return False

# ===============================
# 🖥 الواجهة الرئيسية
# ===============================
def main():
    """الواجهة الرئيسية للتطبيق"""
    
    # إعداد الصفحة
    st.set_page_config(
        page_title=APP_CONFIG["APP_TITLE"],
        page_icon="⚙️",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    # تهيئة ملف Excel إذا لم يكن موجوداً
    initialize_excel_file()
    
    # التحقق من تسجيل الدخول
    if not st.session_state.get("logged_in"):
        if login_ui():
            st.rerun()
        else:
            st.stop()
    
    # الشريط الجانبي
    with st.sidebar:
        st.header(f"{APP_CONFIG['APP_ICON']} {APP_CONFIG['APP_TITLE']}")
        
        # معلومات المستخدم
        st.markdown(f"""
        **👤 المستخدم:** {st.session_state.username}
        **🎭 الدور:** {st.session_state.user_role}
        """)
        
        st.markdown("---")
        
        # أدوات سريعة
        st.subheader("🛠️ أدوات سريعة")
        
        if st.button("🔄 تحديث البيانات من GitHub", key="refresh_github_sidebar"):
            if fetch_from_github():
                st.rerun()
        
        if st.button("🗑️ مسح الكاش", key="clear_cache_sidebar"):
            try:
                if 'cache_data' in dir(st):
                    st.cache_data.clear()
                st.success("✅ تم مسح الكاش")
                st.rerun()
            except:
                st.error("❌ تعذر مسح الكاش")
        
        # زر تحديث ساعات التشغيل
        if st.button("🕐 تحديث ساعات التشغيل", key="update_hours_sidebar"):
            st.session_state["show_update_hours"] = True
        
        st.markdown("---")
        
        # إحصائيات سريعة
        machines_data = load_machines_data()
        
        total_machines = len(machines_data["machines"])
        critical_count = 0
        
        for machine in machines_data["machines"]:
            for maint in machine.get("next_maintenance", []):
                if maint.get("remaining", {}).get("status") == "critical":
                    critical_count += 1
        
        st.markdown(f"""
        **📊 إحصائيات سريعة:**
        
        🛠️ **الماكينات:** {total_machines}
        🔴 **حرجة:** {critical_count}
        """)
        
        st.markdown("---")
        
        # زر تسجيل الخروج
        if st.button("🚪 تسجيل الخروج", key="logout_sidebar", use_container_width=True):
            state = load_state()
            state[st.session_state.username]["active"] = False
            save_state(state)
            
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            
            st.rerun()
    
    # العنوان الرئيسي
    st.title(f"{APP_CONFIG['APP_ICON']} {APP_CONFIG['APP_TITLE']}")
    
    # عرض تحديث الساعات إذا طلب
    if st.session_state.get("show_update_hours", False):
        update_machine_hours_ui()
        return
    
    # التبويبات الرئيسية
    tabs = st.tabs(APP_CONFIG["CUSTOM_TABS"])
    
    with tabs[0]:
        dashboard_ui()
    
    with tabs[1]:
        add_machine_ui()
    
    with tabs[2]:
        maintenance_management_ui()
    
    with tabs[3]:
        timers_dashboard_ui()
    
    with tabs[4]:
        reports_ui()
    
    with tabs[5]:
        settings_ui()

# تشغيل التطبيق
if __name__ == "__main__":
    main()
