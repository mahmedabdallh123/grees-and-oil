import streamlit as st
import pandas as pd
import json
import os
import uuid
from datetime import datetime, timedelta
import plotly.express as px
import plotly.graph_objects as go
from io import BytesIO

# ===============================
# ⚙ إعدادات التطبيق
# ===============================
APP_CONFIG = {
    "APP_TITLE": "نظام إدارة صيانة الماكينات - CMMS",
    "APP_ICON": "🏭",
    "DATA_FILE": "machines_data.json",
    "BACKUP_FOLDER": "backups",
    "MAINTENANCE_TYPES": [
        "تغيير زيت",
        "تغيير شحم",
        "تنظيف فلاتر",
        "فحص كهرباء",
        "صيانة ميكانيكية",
        "معايرة",
        "فحص أمان",
        "صيانة وقائية",
        "إصلاح عطل",
        "تغيير قطع غيار"
    ],
    "MACHINE_TYPES": [
        "ماكينة إنتاج",
        "ماكينة تغليف",
        "ماكينة قص",
        "ماكينة لحام",
        "ماكينة تشكيل",
        "مكبس هيدروليك",
        "مولد",
        "كمبروسر",
        "معدات مساعدة",
        "أخرى"
    ]
}

# ===============================
# 🗂 وظائف إدارة الملفات
# ===============================
def load_data():
    """تحميل بيانات النظام من ملف JSON"""
    if not os.path.exists(APP_CONFIG["DATA_FILE"]):
        # إنشاء بيانات افتراضية
        default_data = {
            "machines": {},
            "maintenance_tasks": {},
            "maintenance_history": {},
            "settings": {
                "default_maintenance_hours": {
                    "تغيير زيت": 500,
                    "تغيير شحم": 250,
                    "تنظيف فلاتر": 200,
                    "فحص كهرباء": 1000,
                    "صيانة ميكانيكية": 1500
                },
                "auto_backup": True,
                "notify_before_hours": 24
            }
        }
        save_data(default_data)
        return default_data
    
    try:
        with open(APP_CONFIG["DATA_FILE"], "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {"machines": {}, "maintenance_tasks": {}, "maintenance_history": {}, "settings": {}}

def save_data(data):
    """حفظ بيانات النظام في ملف JSON"""
    # إنشاء نسخة احتياطية إذا كان الإعداد مفعل
    if data.get("settings", {}).get("auto_backup", True):
        create_backup()
    
    with open(APP_CONFIG["DATA_FILE"], "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)
    return True

def create_backup():
    """إنشاء نسخة احتياطية"""
    if not os.path.exists(APP_CONFIG["BACKUP_FOLDER"]):
        os.makedirs(APP_CONFIG["BACKUP_FOLDER"])
    
    if os.path.exists(APP_CONFIG["DATA_FILE"]):
        backup_name = f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        backup_path = os.path.join(APP_CONFIG["BACKUP_FOLDER"], backup_name)
        
        try:
            with open(APP_CONFIG["DATA_FILE"], "r", encoding="utf-8") as src:
                data = src.read()
            with open(backup_path, "w", encoding="utf-8") as dst:
                dst.write(data)
        except:
            pass

# ===============================
# 🏭 وظائف إدارة الماكينات
# ===============================
def add_new_machine(data, machine_data):
    """إضافة ماكينة جديدة"""
    machine_id = str(uuid.uuid4())[:8]
    
    machine_info = {
        "id": machine_id,
        "name": machine_data.get("name", ""),
        "type": machine_data.get("type", "أخرى"),
        "model": machine_data.get("model", ""),
        "serial_number": machine_data.get("serial_number", ""),
        "location": machine_data.get("location", ""),
        "department": machine_data.get("department", ""),
        "installation_date": machine_data.get("installation_date", datetime.now().strftime("%Y-%m-%d")),
        "status": "نشطة",
        "total_operating_hours": 0,
        "last_maintenance_date": None,
        "next_maintenance_date": None,
        "remaining_hours": 0,
        "notes": machine_data.get("notes", ""),
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat()
    }
    
    data["machines"][machine_id] = machine_info
    return machine_id

def update_machine_operating_hours(data, machine_id, hours_to_add):
    """تحديد ساعات التشغيل للماكينة"""
    if machine_id in data["machines"]:
        machine = data["machines"][machine_id]
        machine["total_operating_hours"] = machine.get("total_operating_hours", 0) + hours_to_add
        machine["remaining_hours"] = max(0, machine.get("remaining_hours", 0) - hours_to_add)
        machine["updated_at"] = datetime.now().isoformat()
        
        # تحديث المهام المرتبطة
        update_maintenance_tasks_due(data, machine_id)
        
        return True
    return False

def calculate_next_maintenance(machine, maintenance_type):
    """حساب تاريخ الصيانة القادمة"""
    settings = st.session_state.system_data.get("settings", {})
    default_hours = settings.get("default_maintenance_hours", {})
    
    hours_needed = default_hours.get(maintenance_type, 500)
    current_hours = machine.get("total_operating_hours", 0)
    
    return current_hours + hours_needed

# ===============================
# 🔧 وظائف إدارة مهام الصيانة
# ===============================
def add_maintenance_task(data, task_data):
    """إضافة مهمة صيانة جديدة"""
    task_id = str(uuid.uuid4())[:8]
    
    machine_id = task_data.get("machine_id")
    if machine_id not in data["machines"]:
        return None
    
    machine = data["machines"][machine_id]
    
    task_info = {
        "id": task_id,
        "machine_id": machine_id,
        "machine_name": machine.get("name", ""),
        "maintenance_type": task_data.get("maintenance_type", "تغيير زيت"),
        "description": task_data.get("description", ""),
        "scheduled_hours": task_data.get("scheduled_hours", 500),
        "current_hours": machine.get("total_operating_hours", 0),
        "remaining_hours": task_data.get("scheduled_hours", 500),
        "priority": task_data.get("priority", "متوسط"),
        "status": "مجدولة",
        "assigned_to": task_data.get("assigned_to", ""),
        "notes": task_data.get("notes", ""),
        "created_at": datetime.now().isoformat(),
        "created_by": st.session_state.get("username", "system"),
        "last_updated": datetime.now().isoformat(),
        "completed_at": None,
        "completed_by": None
    }
    
    data["maintenance_tasks"][task_id] = task_info
    
    # تحديث الماكينة
    machine["remaining_hours"] = task_info["remaining_hours"]
    machine["next_maintenance_date"] = task_info.get("scheduled_hours", 500)
    
    return task_id

def complete_maintenance_task(data, task_id, completion_data):
    """إكمال مهمة صيانة"""
    if task_id not in data["maintenance_tasks"]:
        return False
    
    task = data["maintenance_tasks"][task_id]
    machine_id = task["machine_id"]
    
    # تحديث حالة المهمة
    task["status"] = "مكتملة"
    task["completed_at"] = datetime.now().isoformat()
    task["completed_by"] = completion_data.get("technician", "غير معروف")
    task["actual_hours"] = completion_data.get("actual_hours", task["current_hours"])
    task["notes"] = completion_data.get("notes", task["notes"])
    task["last_updated"] = datetime.now().isoformat()
    
    # إضافة إلى سجل الصيانة
    history_id = str(uuid.uuid4())[:8]
    history_entry = {
        "id": history_id,
        "task_id": task_id,
        "machine_id": machine_id,
        "machine_name": task["machine_name"],
        "maintenance_type": task["maintenance_type"],
        "description": task["description"],
        "scheduled_hours": task["scheduled_hours"],
        "actual_hours": task["actual_hours"],
        "completed_by": task["completed_by"],
        "notes": task["notes"],
        "completion_date": task["completed_at"]
    }
    
    if "maintenance_history" not in data:
        data["maintenance_history"] = {}
    data["maintenance_history"][history_id] = history_entry
    
    # تحديث الماكينة
    if machine_id in data["machines"]:
        machine = data["machines"][machine_id]
        machine["last_maintenance_date"] = task["completed_at"]
        machine["updated_at"] = datetime.now().isoformat()
    
    return True

def update_maintenance_tasks_due(data, machine_id):
    """تحديث المهام المستحقة بناءً على ساعات التشغيل"""
    machine = data["machines"].get(machine_id)
    if not machine:
        return
    
    current_hours = machine.get("total_operating_hours", 0)
    
    for task_id, task in data["maintenance_tasks"].items():
        if task["machine_id"] == machine_id and task["status"] == "مجدولة":
            task["current_hours"] = current_hours
            task["remaining_hours"] = max(0, task["scheduled_hours"] - current_hours)
            task["last_updated"] = datetime.now().isoformat()
            
            # تحديث حالة المهمة إذا انتهى وقتها
            if task["remaining_hours"] <= 0:
                task["status"] = "متأخرة"

# ===============================
# 📊 وظائف التقارير والإحصائيات
# ===============================
def generate_machines_report(data):
    """إنشاء تقرير عن حالة الماكينات"""
    machines = data.get("machines", {})
    
    report_data = []
    for machine_id, machine in machines.items():
        report_data.append({
            "رقم الماكينة": machine_id,
            "اسم الماكينة": machine.get("name", ""),
            "النوع": machine.get("type", ""),
            "الموقع": machine.get("location", ""),
            "ساعات التشغيل": machine.get("total_operating_hours", 0),
            "آخر صيانة": machine.get("last_maintenance_date", "لم تتم"),
            "الساعات المتبقية": machine.get("remaining_hours", 0),
            "الحالة": machine.get("status", "نشطة"),
            "عدد المهام النشطة": count_active_tasks(data, machine_id)
        })
    
    return pd.DataFrame(report_data)

def generate_maintenance_report(data):
    """إنشاء تقرير عن مهام الصيانة"""
    tasks = data.get("maintenance_tasks", {})
    
    report_data = []
    for task_id, task in tasks.items():
        report_data.append({
            "رقم المهمة": task_id,
            "الماكينة": task.get("machine_name", ""),
            "نوع الصيانة": task.get("maintenance_type", ""),
            "الحالة": task.get("status", ""),
            "الأولوية": task.get("priority", ""),
            "الساعات المجدولة": task.get("scheduled_hours", 0),
            "الساعات المتبقية": task.get("remaining_hours", 0),
            "المسند إلى": task.get("assigned_to", ""),
            "تاريخ الإنشاء": format_date(task.get("created_at")),
            "آخر تحديث": format_date(task.get("last_updated"))
        })
    
    return pd.DataFrame(report_data)

def generate_history_report(data):
    """إنشاء تقرير عن سجل الصيانة"""
    history = data.get("maintenance_history", {})
    
    report_data = []
    for history_id, entry in history.items():
        report_data.append({
            "رقم العملية": history_id,
            "الماكينة": entry.get("machine_name", ""),
            "نوع الصيانة": entry.get("maintenance_type", ""),
            "الساعات المجدولة": entry.get("scheduled_hours", 0),
            "الساعات الفعلية": entry.get("actual_hours", 0),
            "الفني": entry.get("completed_by", ""),
            "تاريخ الإكمال": format_date(entry.get("completion_date")),
            "ملاحظات": entry.get("notes", "")
        })
    
    return pd.DataFrame(report_data)

def count_active_tasks(data, machine_id):
    """عد المهام النشطة لماكينة معينة"""
    tasks = data.get("maintenance_tasks", {})
    count = 0
    for task in tasks.values():
        if task.get("machine_id") == machine_id and task.get("status") in ["مجدولة", "متأخرة"]:
            count += 1
    return count

def format_date(date_str):
    """تنسيق التاريخ للعرض"""
    if not date_str:
        return ""
    try:
        date_obj = datetime.fromisoformat(date_str)
        return date_obj.strftime("%Y-%m-%d %H:%M")
    except:
        return date_str

# ===============================
# 📈 وظائف الرسوم البيانية
# ===============================
def create_machines_status_chart(data):
    """إنشاء مخطط حالة الماكينات"""
    machines = data.get("machines", {})
    
    status_count = {"نشطة": 0, "متوقفة": 0, "تحت الصيانة": 0, "محذوفة": 0}
    
    for machine in machines.values():
        status = machine.get("status", "نشطة")
        status_count[status] = status_count.get(status, 0) + 1
    
    fig = px.pie(
        names=list(status_count.keys()),
        values=list(status_count.values()),
        title="توزيع حالة الماكينات",
        color_discrete_sequence=px.colors.qualitative.Set3
    )
    fig.update_traces(textposition='inside', textinfo='percent+label')
    return fig

def create_maintenance_status_chart(data):
    """إنشاء مخطط حالة مهام الصيانة"""
    tasks = data.get("maintenance_tasks", {})
    
    status_count = {"مجدولة": 0, "قيد التنفيذ": 0, "مكتملة": 0, "متأخرة": 0, "ملغاة": 0}
    
    for task in tasks.values():
        status = task.get("status", "مجدولة")
        status_count[status] = status_count.get(status, 0) + 1
    
    fig = px.bar(
        x=list(status_count.keys()),
        y=list(status_count.values()),
        title="توزيع حالة مهام الصيانة",
        labels={"x": "الحالة", "y": "العدد"},
        color=list(status_count.values()),
        color_continuous_scale="Viridis"
    )
    return fig

def create_hours_remaining_chart(data):
    """إنشاء مخطط الساعات المتبقية للصيانة"""
    machines = data.get("machines", {})
    
    chart_data = []
    for machine_id, machine in machines.items():
        if machine.get("status") == "نشطة":
            chart_data.append({
                "الماكينة": machine.get("name", machine_id),
                "الساعات المتبقية": machine.get("remaining_hours", 0)
            })
    
    if not chart_data:
        return None
    
    df = pd.DataFrame(chart_data)
    fig = px.bar(
        df,
        x="الماكينة",
        y="الساعات المتبقية",
        title="الساعات المتبقية للصيانة",
        color="الساعات المتبقية",
        color_continuous_scale="RdYlGn_r"
    )
    fig.update_layout(xaxis_tickangle=-45)
    return fig

# ===============================
# 🔔 وظائف التنبيهات
# ===============================
def check_upcoming_maintenance(data):
    """التحقق من المهام القريبة"""
    settings = data.get("settings", {})
    notify_hours = settings.get("notify_before_hours", 24)
    
    upcoming_tasks = []
    
    for task_id, task in data.get("maintenance_tasks", {}).items():
        if task.get("status") in ["مجدولة", "متأخرة"]:
            remaining_hours = task.get("remaining_hours", 0)
            if remaining_hours <= notify_hours:
                upcoming_tasks.append(task)
    
    return upcoming_tasks

# ===============================
# 🖥 واجهة إضافة ماكينة جديدة
# ===============================
def show_add_machine_ui():
    """عرض واجهة إضافة ماكينة جديدة"""
    st.markdown("### 🏭 إضافة ماكينة جديدة")
    
    with st.form("add_machine_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            machine_name = st.text_input("اسم الماكينة *", max_chars=100)
            machine_type = st.selectbox("نوع الماكينة *", APP_CONFIG["MACHINE_TYPES"])
            model = st.text_input("الموديل", max_chars=50)
            serial_number = st.text_input("الرقم التسلسلي", max_chars=50)
        
        with col2:
            location = st.text_input("الموقع *", max_chars=100)
            department = st.text_input("القسم/الإدارة", max_chars=50)
            installation_date = st.date_input("تاريخ التركيب", value=datetime.now())
            initial_hours = st.number_input("ساعات التشغيل الابتدائية", min_value=0, value=0)
        
        notes = st.text_area("ملاحظات إضافية")
        
        col_btn1, col_btn2 = st.columns(2)
        with col_btn1:
            submitted = st.form_submit_button("💾 حفظ الماكينة", type="primary")
        with col_btn2:
            st.form_submit_button("🗑 مسح الحقول")
        
        if submitted:
            if not machine_name or not location:
                st.error("⚠ الرجاء ملء الحقول الإلزامية (*)")
                return
            
            machine_data = {
                "name": machine_name,
                "type": machine_type,
                "model": model,
                "serial_number": serial_number,
                "location": location,
                "department": department,
                "installation_date": installation_date.strftime("%Y-%m-%d"),
                "notes": notes
            }
            
            machine_id = add_new_machine(st.session_state.system_data, machine_data)
            
            if initial_hours > 0:
                update_machine_operating_hours(st.session_state.system_data, machine_id, initial_hours)
            
            save_data(st.session_state.system_data)
            st.success(f"✅ تم إضافة الماكينة '{machine_name}' بنجاح! الرقم: {machine_id}")
            st.rerun()

# ===============================
# 🔧 واجهة إضافة مهمة صيانة
# ===============================
def show_add_maintenance_task_ui():
    """عرض واجهة إضافة مهمة صيانة"""
    st.markdown("### 🔧 إضافة مهمة صيانة جديدة")
    
    machines = st.session_state.system_data.get("machines", {})
    if not machines:
        st.warning("⚠ لا توجد ماكينات مسجلة. الرجاء إضافة ماكينة أولاً.")
        return
    
    machine_options = {mid: f"{m.get('name', 'غير معروف')} ({mid})" 
                      for mid, m in machines.items() 
                      if m.get("status") == "نشطة"}
    
    if not machine_options:
        st.warning("⚠ لا توجد ماكينات نشطة لإضافة مهام صيانة.")
        return
    
    with st.form("add_maintenance_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            selected_machine = st.selectbox(
                "اختر الماكينة *",
                options=list(machine_options.keys()),
                format_func=lambda x: machine_options[x]
            )
            
            maintenance_type = st.selectbox("نوع الصيانة *", APP_CONFIG["MAINTENANCE_TYPES"])
            
            # الحصول على الساعات الافتراضية
            settings = st.session_state.system_data.get("settings", {})
            default_hours = settings.get("default_maintenance_hours", {})
            default_hours_value = default_hours.get(maintenance_type, 500)
            
            scheduled_hours = st.number_input(
                "الساعات المجدولة للصيانة *",
                min_value=1,
                value=default_hours_value,
                help="بعد كم ساعة تشغيل يجب إجراء هذه الصيانة"
            )
        
        with col2:
            priority = st.selectbox("الأولوية", ["منخفضة", "متوسطة", "عالية", "حرجة"])
            assigned_to = st.text_input("المسند إلى", placeholder="اسم الفني المسؤول")
            
            # عرض معلومات الماكينة المختارة
            if selected_machine in machines:
                machine = machines[selected_machine]
                current_hours = machine.get("total_operating_hours", 0)
                st.info(f"**ساعات التشغيل الحالية:** {current_hours}")
                st.info(f"**ساعات التشغيل للصيانة:** {current_hours + scheduled_hours}")
        
        description = st.text_area("وصف المهمة *", placeholder="وصف تفصيلي للصيانة المطلوبة")
        notes = st.text_area("ملاحظات إضافية")
        
        col_btn1, col_btn2 = st.columns(2)
        with col_btn1:
            submitted = st.form_submit_button("💾 حفظ المهمة", type="primary")
        with col_btn2:
            st.form_submit_button("🗑 مسح الحقول")
        
        if submitted:
            if not description:
                st.error("⚠ الرجاء إدخال وصف للمهمة")
                return
            
            task_data = {
                "machine_id": selected_machine,
                "maintenance_type": maintenance_type,
                "description": description,
                "scheduled_hours": scheduled_hours,
                "priority": priority,
                "assigned_to": assigned_to,
                "notes": notes
            }
            
            task_id = add_maintenance_task(st.session_state.system_data, task_data)
            
            if task_id:
                save_data(st.session_state.system_data)
                st.success(f"✅ تم إضافة مهمة الصيانة بنجاح! الرقم: {task_id}")
                st.rerun()
            else:
                st.error("❌ فشل إضافة المهمة. الرجاء التحقق من البيانات.")

# ===============================
# ⏱ واجهة تحديث ساعات التشغيل
# ===============================
def show_update_hours_ui():
    """عرض واجهة تحديث ساعات التشغيل"""
    st.markdown("### ⏱ تحديث ساعات التشغيل")
    
    machines = st.session_state.system_data.get("machines", {})
    if not machines:
        st.warning("⚠ لا توجد ماكينات مسجلة.")
        return
    
    active_machines = {mid: m for mid, m in machines.items() if m.get("status") == "نشطة"}
    
    if not active_machines:
        st.warning("⚠ لا توجد ماكينات نشطة.")
        return
    
    machine_options = {mid: f"{m.get('name', 'غير معروف')} ({mid}) - {m.get('total_operating_hours', 0)} ساعة" 
                      for mid, m in active_machines.items()}
    
    with st.form("update_hours_form"):
        selected_machine = st.selectbox(
            "اختر الماكينة",
            options=list(machine_options.keys()),
            format_func=lambda x: machine_options[x]
        )
        
        hours_to_add = st.number_input(
            "الساعات المضافة",
            min_value=0,
            max_value=1000,
            value=8,
            help="عدد ساعات التشغيل المضافة"
        )
        
        operation_date = st.date_input("تاريخ التشغيل", value=datetime.now())
        notes = st.text_area("ملاحظات", placeholder="ملاحظات عن التشغيل")
        
        col_btn1, col_btn2 = st.columns(2)
        with col_btn1:
            submitted = st.form_submit_button("💾 تحديث الساعات", type="primary")
        with col_btn2:
            st.form_submit_button("🗑 مسح الحقول")
        
        if submitted:
            if selected_machine and hours_to_add > 0:
                if update_machine_operating_hours(st.session_state.system_data, selected_machine, hours_to_add):
                    save_data(st.session_state.system_data)
                    machine_name = active_machines[selected_machine].get("name", "غير معروف")
                    st.success(f"✅ تم تحديث ساعات التشغيل للماكينة '{machine_name}' بإضافة {hours_to_add} ساعة")
                    
                    # عرض المهام المستحقة
                    tasks = st.session_state.system_data.get("maintenance_tasks", {})
                    due_tasks = []
                    for task in tasks.values():
                        if task.get("machine_id") == selected_machine and task.get("remaining_hours") <= 0:
                            due_tasks.append(task)
                    
                    if due_tasks:
                        st.warning(f"⚠ هناك {len(due_tasks)} مهمة صيانة مستحقة لهذه الماكينة!")
                    
                    st.rerun()
                else:
                    st.error("❌ فشل تحديث الساعات")
            else:
                st.error("⚠ الرجاء إدخال قيمة صحيحة للساعات")

# ===============================
# ✅ واجهة إكمال مهمة صيانة
# ===============================
def show_complete_task_ui():
    """عرض واجهة إكمال مهمة صيانة"""
    st.markdown("### ✅ إكمال مهمة صيانة")
    
    tasks = st.session_state.system_data.get("maintenance_tasks", {})
    pending_tasks = {tid: t for tid, t in tasks.items() 
                    if t.get("status") in ["مجدولة", "متأخرة", "قيد التنفيذ"]}
    
    if not pending_tasks:
        st.info("🎉 لا توجد مهام صيانة معلقة حالياً!")
        return
    
    task_options = {tid: f"{t.get('machine_name', 'غير معروف')} - {t.get('maintenance_type', 'صيانة')} ({tid})" 
                   for tid, t in pending_tasks.items()}
    
    with st.form("complete_task_form"):
        selected_task = st.selectbox(
            "اختر المهمة للإكمال",
            options=list(task_options.keys()),
            format_func=lambda x: task_options[x]
        )
        
        if selected_task:
            task_info = pending_tasks[selected_task]
            
            col1, col2 = st.columns(2)
            with col1:
                st.info(f"**الماكينة:** {task_info.get('machine_name')}")
                st.info(f"**نوع الصيانة:** {task_info.get('maintenance_type')}")
                st.info(f"**الساعات المجدولة:** {task_info.get('scheduled_hours')}")
            
            with col2:
                st.info(f"**الساعات الحالية:** {task_info.get('current_hours')}")
                st.info(f"**الساعات المتبقية:** {task_info.get('remaining_hours')}")
                st.info(f"**الأولوية:** {task_info.get('priority')}")
        
        technician = st.text_input("اسم الفني المنفذ *", placeholder="اسم الفني الذي أجرى الصيانة")
        actual_hours = st.number_input(
            "ساعات التشغيل الفعلية *",
            min_value=0,
            value=task_info.get("current_hours", 0) if selected_task else 0
        )
        
        completion_notes = st.text_area("ملاحظات الإكمال *", 
                                       placeholder="تفاصيل العمل المنجز، القطع المستبدلة، إلخ.")
        
        col_btn1, col_btn2 = st.columns(2)
        with col_btn1:
            submitted = st.form_submit_button("✅ إكمال المهمة", type="primary")
        with col_btn2:
            st.form_submit_button("🗑 إلغاء")
        
        if submitted:
            if not technician or not completion_notes:
                st.error("⚠ الرجاء ملء جميع الحقول الإلزامية (*)")
                return
            
            completion_data = {
                "technician": technician,
                "actual_hours": actual_hours,
                "notes": completion_notes
            }
            
            if complete_maintenance_task(st.session_state.system_data, selected_task, completion_data):
                save_data(st.session_state.system_data)
                st.success(f"✅ تم إكمال مهمة الصيانة بنجاح!")
                
                # عرض ملخص
                with st.expander("📋 ملخص العملية", expanded=True):
                    st.markdown(f"**رقم المهمة:** {selected_task}")
                    st.markdown(f"**الماكينة:** {task_info.get('machine_name')}")
                    st.markdown(f"**نوع الصيانة:** {task_info.get('maintenance_type')}")
                    st.markdown(f"**الفني:** {technician}")
                    st.markdown(f"**تاريخ الإكمال:** {datetime.now().strftime('%Y-%m-%d %H:%M')}")
                
                st.rerun()
            else:
                st.error("❌ فشل إكمال المهمة")

# ===============================
# 📋 واجهة عرض الماكينات
# ===============================
def show_machines_list():
    """عرض قائمة الماكينات"""
    st.markdown("### 📋 قائمة الماكينات")
    
    machines = st.session_state.system_data.get("machines", {})
    if not machines:
        st.info("ℹ️ لا توجد ماكينات مسجلة بعد.")
        return
    
    # فلترة البحث
    search_term = st.text_input("🔍 بحث في الماكينات:", placeholder="ابحث بالاسم، النوع، الموقع...")
    
    filtered_machines = {}
    for mid, machine in machines.items():
        if not search_term:
            filtered_machines[mid] = machine
        else:
            search_text = f"{machine.get('name', '')} {machine.get('type', '')} {machine.get('location', '')} {machine.get('model', '')}".lower()
            if search_term.lower() in search_text:
                filtered_machines[mid] = machine
    
    if not filtered_machines:
        st.warning("⚠ لم يتم العثور على ماكينات تطابق البحث.")
        return
    
    # عرض الماكينات
    for machine_id, machine in filtered_machines.items():
        with st.expander(f"🏭 {machine.get('name', 'غير معروف')} ({machine_id})", expanded=False):
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown(f"**النوع:** {machine.get('type', 'غير محدد')}")
                st.markdown(f"**الموديل:** {machine.get('model', 'غير محدد')}")
                st.markdown(f"**الموقع:** {machine.get('location', 'غير محدد')}")
                st.markdown(f"**القسم:** {machine.get('department', 'غير محدد')}")
            
            with col2:
                status = machine.get("status", "نشطة")
                status_color = "🟢" if status == "نشطة" else "🟡" if status == "تحت الصيانة" else "🔴"
                st.markdown(f"**الحالة:** {status_color} {status}")
                st.markdown(f"**ساعات التشغيل:** {machine.get('total_operating_hours', 0)}")
                
                remaining_hours = machine.get("remaining_hours", 0)
                hours_color = "🟢" if remaining_hours > 100 else "🟡" if remaining_hours > 24 else "🔴"
                st.markdown(f"**الساعات المتبقية:** {hours_color} {remaining_hours}")
                
                last_maintenance = machine.get("last_maintenance_date", "لم تتم")
                if last_maintenance != "لم تتم":
                    try:
                        last_date = datetime.fromisoformat(last_maintenance).strftime("%Y-%m-%d")
                        st.markdown(f"**آخر صيانة:** {last_date}")
                    except:
                        st.markdown(f"**آخر صيانة:** {last_maintenance}")
                else:
                    st.markdown(f"**آخر صيانة:** {last_maintenance}")
            
            # أزرار الإدارة
            col_btn1, col_btn2, col_btn3 = st.columns(3)
            with col_btn1:
                if st.button(f"📊 المهام", key=f"tasks_{machine_id}"):
                    st.session_state["selected_machine"] = machine_id
                    st.session_state["show_machine_tasks"] = True
                    st.rerun()
            with col_btn2:
                if st.button(f"⏱ تحديث ساعات", key=f"update_{machine_id}"):
                    st.session_state["selected_machine"] = machine_id
                    st.session_state["show_update_hours"] = True
                    st.rerun()
            with col_btn3:
                if st.button(f"✏ تعديل", key=f"edit_{machine_id}"):
                    st.session_state["edit_machine_id"] = machine_id
                    st.rerun()

# ===============================
# 📊 واجهة عرض مهام الصيانة
# ===============================
def show_maintenance_tasks():
    """عرض مهام الصيانة"""
    st.markdown("### 📊 مهام الصيانة")
    
    tasks = st.session_state.system_data.get("maintenance_tasks", {})
    if not tasks:
        st.info("ℹ️ لا توجد مهام صيانة مسجلة بعد.")
        return
    
    # فلترة المهام
    filter_col1, filter_col2, filter_col3 = st.columns(3)
    with filter_col1:
        status_filter = st.selectbox("فلترة بالحالة", ["الكل", "مجدولة", "قيد التنفيذ", "مكتملة", "متأخرة", "ملغاة"])
    with filter_col2:
        priority_filter = st.selectbox("فلترة بالأولوية", ["الكل", "منخفضة", "متوسطة", "عالية", "حرجة"])
    with filter_col3:
        machine_filter = st.selectbox("فلترة بالماكينة", ["الكل"] + list(st.session_state.system_data.get("machines", {}).keys()))
    
    # تطبيق الفلاتر
    filtered_tasks = {}
    for task_id, task in tasks.items():
        status_match = (status_filter == "الكل") or (task.get("status") == status_filter)
        priority_match = (priority_filter == "الكل") or (task.get("priority") == priority_filter)
        machine_match = (machine_filter == "الكل") or (task.get("machine_id") == machine_filter)
        
        if status_match and priority_match and machine_match:
            filtered_tasks[task_id] = task
    
    if not filtered_tasks:
        st.warning("⚠ لم يتم العثور على مهام تطابق الفلتر.")
        return
    
    # عرض المهام
    for task_id, task in filtered_tasks.items():
        # تحديد لون البطاقة حسب الحالة
        status_colors = {
            "مجدولة": "#e3f2fd",
            "قيد التنفيذ": "#fff3e0",
            "مكتملة": "#e8f5e9",
            "متأخرة": "#ffebee",
            "ملغاة": "#f5f5f5"
        }
        
        card_color = status_colors.get(task.get("status", "مجدولة"), "#ffffff")
        
        with st.container():
            st.markdown(f"""
            <div style="background-color:{card_color}; padding:15px; border-radius:10px; margin-bottom:10px; border-left:5px solid {'#4caf50' if task.get('status') == 'مكتملة' else '#ff9800' if task.get('status') == 'متأخرة' else '#2196f3'};">
                <div style="display:flex; justify-content:space-between; align-items:center;">
                    <div>
                        <h4 style="margin:0;">{task.get('maintenance_type', 'صيانة')} - {task.get('machine_name', 'غير معروف')}</h4>
                        <p style="margin:5px 0; color:#666;">{task.get('description', '')}</p>
                    </div>
                    <div style="text-align:right;">
                        <span style="background:{'#ff9800' if task.get('priority') == 'عالية' else '#4caf50' if task.get('priority') == 'منخفضة' else '#2196f3'}; 
                                    color:white; padding:2px 8px; border-radius:12px; font-size:12px;">
                            {task.get('priority', 'متوسطة')}
                        </span>
                    </div>
                </div>
                <div style="display:flex; justify-content:space-between; margin-top:10px; font-size:14px;">
                    <div>
                        <span>🕐 {task.get('remaining_hours', 0)} ساعة متبقية</span> |
                        <span>👷 {task.get('assigned_to', 'غير مسند')}</span>
                    </div>
                    <div>
                        <span>{task.get('status', 'مجدولة')}</span>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            # أزرار الإجراءات
            col_act1, col_act2, col_act3 = st.columns([1, 1, 2])
            with col_act1:
                if task.get("status") in ["مجدولة", "متأخرة"]:
                    if st.button("▶️ بدء التنفيذ", key=f"start_{task_id}"):
                        st.session_state.system_data["maintenance_tasks"][task_id]["status"] = "قيد التنفيذ"
                        save_data(st.session_state.system_data)
                        st.rerun()
            with col_act2:
                if task.get("status") in ["قيد التنفيذ", "متأخرة"]:
                    if st.button("✅ إكمال", key=f"complete_{task_id}"):
                        st.session_state["complete_task_id"] = task_id
                        st.rerun()
            with col_act3:
                if st.button("📋 التفاصيل", key=f"details_{task_id}"):
                    with st.expander("تفاصيل المهمة", expanded=True):
                        show_task_details(task_id)

# ===============================
# 📜 واجهة سجل الصيانة
# ===============================
def show_maintenance_history():
    """عرض سجل الصيانة"""
    st.markdown("### 📜 سجل الصيانة")
    
    history = st.session_state.system_data.get("maintenance_history", {})
    if not history:
        st.info("ℹ️ لا توجد سجلات صيانة بعد.")
        return
    
    # تحويل السجل إلى DataFrame للعرض
    history_list = []
    for history_id, entry in history.items():
        history_list.append({
            "رقم العملية": history_id,
            "الماكينة": entry.get("machine_name", ""),
            "نوع الصيانة": entry.get("maintenance_type", ""),
            "الفني": entry.get("completed_by", ""),
            "الساعات المجدولة": entry.get("scheduled_hours", 0),
            "الساعات الفعلية": entry.get("actual_hours", 0),
            "تاريخ الإكمال": format_date(entry.get("completion_date")),
            "ملاحظات": entry.get("notes", "")
        })
    
    if history_list:
        history_df = pd.DataFrame(history_list)
        
        # فلترة البحث
        search_history = st.text_input("🔍 بحث في السجل:", placeholder="ابحث بالماكينة، النوع، الفني...")
        
        if search_history:
            mask = history_df.apply(lambda row: row.astype(str).str.contains(search_history, case=False).any(), axis=1)
            filtered_df = history_df[mask]
        else:
            filtered_df = history_df
        
        if not filtered_df.empty:
            st.dataframe(filtered_df, use_container_width=True, height=400)
            
            # خيارات التصدير
            col_exp1, col_exp2 = st.columns(2)
            with col_exp1:
                if st.button("📊 تصدير إلى Excel", key="export_history_excel"):
                    buffer = BytesIO()
                    with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                        filtered_df.to_excel(writer, sheet_name='سجل_الصيانة', index=False)
                    
                    st.download_button(
                        label="⬇️ تحميل ملف Excel",
                        data=buffer.getvalue(),
                        file_name=f"سجل_الصيانة_{datetime.now().strftime('%Y%m%d')}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )
            
            with col_exp2:
                if st.button("📄 تصدير إلى CSV", key="export_history_csv"):
                    csv = filtered_df.to_csv(index=False, encoding='utf-8-sig')
                    st.download_button(
                        label="⬇️ تحميل ملف CSV",
                        data=csv,
                        file_name=f"سجل_الصيانة_{datetime.now().strftime('%Y%m%d')}.csv",
                        mime="text/csv"
                    )
        else:
            st.warning("⚠ لم يتم العثور على سجلات تطابق البحث.")
    else:
        st.info("ℹ️ لا توجد سجلات صيانة لعرضها.")

# ===============================
# ⚙ واجهة الإعدادات
# ===============================
def show_settings_ui():
    """عرض واجهة الإعدادات"""
    st.markdown("### ⚙ إعدادات النظام")
    
    settings = st.session_state.system_data.get("settings", {})
    
    with st.form("settings_form"):
        st.markdown("#### ⏱ إعدادات ساعات الصيانة الافتراضية")
        
        default_hours = settings.get("default_maintenance_hours", {})
        
        cols = st.columns(3)
        maintenance_types = APP_CONFIG["MAINTENANCE_TYPES"]
        
        for i, maint_type in enumerate(maintenance_types):
            with cols[i % 3]:
                hours_value = st.number_input(
                    f"{maint_type} (ساعة)",
                    min_value=1,
                    value=default_hours.get(maint_type, 500),
                    key=f"hours_{maint_type}"
                )
                default_hours[maint_type] = hours_value
        
        st.markdown("---")
        st.markdown("#### 🔔 إعدادات التنبيهات")
        
        col_set1, col_set2 = st.columns(2)
        with col_set1:
            notify_hours = st.number_input(
                "التنبيه قبل (ساعة)",
                min_value=1,
                value=settings.get("notify_before_hours", 24),
                help="عدد الساعات قبل موعد الصيانة لإرسال التنبيه"
            )
        with col_set2:
            auto_backup = st.checkbox(
                "النسخ الاحتياطي التلقائي",
                value=settings.get("auto_backup", True)
            )
        
        st.markdown("---")
        col_btn1, col_btn2 = st.columns(2)
        with col_btn1:
            submitted = st.form_submit_button("💾 حفظ الإعدادات", type="primary")
        with col_btn2:
            st.form_submit_button("🗑 إلغاء")
        
        if submitted:
            st.session_state.system_data["settings"] = {
                "default_maintenance_hours": default_hours,
                "notify_before_hours": notify_hours,
                "auto_backup": auto_backup
            }
            
            save_data(st.session_state.system_data)
            st.success("✅ تم حفظ الإعدادات بنجاح!")
            st.rerun()
    
    st.markdown("---")
    st.markdown("#### 🗂 إدارة النسخ الاحتياطية")
    
    if os.path.exists(APP_CONFIG["BACKUP_FOLDER"]):
        backup_files = os.listdir(APP_CONFIG["BACKUP_FOLDER"])
        backup_files = [f for f in backup_files if f.endswith('.json')]
        
        if backup_files:
            st.info(f"عدد النسخ الاحتياطية: {len(backup_files)}")
            
            latest_backups = sorted(backup_files, reverse=True)[:5]
            for backup in latest_backups:
                backup_path = os.path.join(APP_CONFIG["BACKUP_FOLDER"], backup)
                backup_time = os.path.getmtime(backup_path)
                backup_date = datetime.fromtimestamp(backup_time).strftime("%Y-%m-%d %H:%M")
                
                col_bak1, col_bak2 = st.columns([3, 1])
                with col_bak1:
                    st.text(f"📁 {backup} - {backup_date}")
                with col_bak2:
                    if st.button("🔄 استعادة", key=f"restore_{backup}"):
                        try:
                            with open(backup_path, "r", encoding="utf-8") as f:
                                backup_data = json.load(f)
                            
                            st.session_state.system_data = backup_data
                            save_data(backup_data)
                            st.success(f"✅ تم استعادة النسخة الاحتياطية: {backup}")
                            st.rerun()
                        except:
                            st.error(f"❌ فشل استعادة النسخة الاحتياطية: {backup}")
        else:
            st.info("ℹ️ لا توجد نسخ احتياطية")
    else:
        st.info("ℹ️ مجلد النسخ الاحتياطية غير موجود")
    
    # زر إنشاء نسخة احتياطية يدوية
    if st.button("💾 إنشاء نسخة احتياطية الآن", key="manual_backup"):
        create_backup()
        st.success("✅ تم إنشاء نسخة احتياطية بنجاح!")
        st.rerun()

# ===============================
# 📱 الواجهة الرئيسية
# ===============================
def main():
    """الواجهة الرئيسية للتطبيق"""
    
    # إعداد صفحة Streamlit
    st.set_page_config(
        page_title=APP_CONFIG["APP_TITLE"],
        page_icon="🏭",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    # تهيئة بيانات الجلسة
    if "system_data" not in st.session_state:
        st.session_state.system_data = load_data()
    
    if "selected_machine" not in st.session_state:
        st.session_state.selected_machine = None
    
    if "show_machine_tasks" not in st.session_state:
        st.session_state.show_machine_tasks = False
    
    if "show_update_hours" not in st.session_state:
        st.session_state.show_update_hours = False
    
    if "complete_task_id" not in st.session_state:
        st.session_state.complete_task_id = None
    
    if "edit_machine_id" not in st.session_state:
        st.session_state.edit_machine_id = None
    
    # الشريط الجانبي
    with st.sidebar:
        st.title(f"{APP_CONFIG['APP_ICON']} {APP_CONFIG['APP_TITLE']}")
        
        st.markdown("---")
        
        # الإحصائيات السريعة
        machines_count = len(st.session_state.system_data.get("machines", {}))
        active_tasks = len([t for t in st.session_state.system_data.get("maintenance_tasks", {}).values() 
                           if t.get("status") in ["مجدولة", "متأخرة", "قيد التنفيذ"]])
        
        st.metric("🏭 عدد الماكينات", machines_count)
        st.metric("🔧 المهام النشطة", active_tasks)
        
        # التحقق من المهام القريبة
        upcoming = check_upcoming_maintenance(st.session_state.system_data)
        if upcoming:
            st.warning(f"⚠ {len(upcoming)} مهمة صيانة قريبة!")
        
        st.markdown("---")
        
        # قائمة التنقل
        nav_options = {
            "🏠 لوحة التحكم": "dashboard",
            "🏭 إدارة الماكينات": "machines",
            "🔧 مهام الصيانة": "maintenance",
            "📜 سجل الصيانة": "history",
            "📊 التقارير": "reports",
            "⚙ الإعدادات": "settings"
        }
        
        selected_nav = st.radio(
            "القائمة الرئيسية",
            options=list(nav_options.keys()),
            label_visibility="collapsed"
        )
        
        st.markdown("---")
        
        # أزرار الإجراءات السريعة
        st.markdown("### 🚀 إجراءات سريعة")
        
        col_q1, col_q2 = st.columns(2)
        with col_q1:
            if st.button("➕ ماكينة جديدة", use_container_width=True):
                st.session_state["show_add_machine"] = True
                st.rerun()
        with col_q2:
            if st.button("🔧 مهمة جديدة", use_container_width=True):
                st.session_state["show_add_task"] = True
                st.rerun()
        
        if st.button("🔄 تحديث البيانات", use_container_width=True):
            st.session_state.system_data = load_data()
            st.rerun()
        
        st.markdown("---")
        st.caption(f"الإصدار 1.0 | آخر تحديث: {datetime.now().strftime('%Y-%m-%d')}")

    # المحتوى الرئيسي
    if selected_nav == "🏠 لوحة التحكم":
        show_dashboard()
    elif selected_nav == "🏭 إدارة الماكينات":
        show_machines_management()
    elif selected_nav == "🔧 مهام الصيانة":
        show_maintenance_management()
    elif selected_nav == "📜 سجل الصيانة":
        show_maintenance_history()
    elif selected_nav == "📊 التقارير":
        show_reports()
    elif selected_nav == "⚙ الإعدادات":
        show_settings_ui()

# ===============================
# 🏠 لوحة التحكم
# ===============================
def show_dashboard():
    """عرض لوحة التحكم الرئيسية"""
    st.title("🏠 لوحة التحكم")
    
    # الإحصائيات الرئيسية
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        machines_count = len(st.session_state.system_data.get("machines", {}))
        st.metric("🏭 الماكينات", machines_count)
    
    with col2:
        tasks_count = len(st.session_state.system_data.get("maintenance_tasks", {}))
        st.metric("🔧 مهام الصيانة", tasks_count)
    
    with col3:
        active_tasks = len([t for t in st.session_state.system_data.get("maintenance_tasks", {}).values() 
                           if t.get("status") in ["مجدولة", "متأخرة"]])
        st.metric("📋 المهام النشطة", active_tasks)
    
    with col4:
        history_count = len(st.session_state.system_data.get("maintenance_history", {}))
        st.metric("📜 سجلات الصيانة", history_count)
    
    st.markdown("---")
    
    # الرسوم البيانية
    col_chart1, col_chart2 = st.columns(2)
    
    with col_chart1:
        st.markdown("### 📊 حالة الماكينات")
        fig1 = create_machines_status_chart(st.session_state.system_data)
        if fig1:
            st.plotly_chart(fig1, use_container_width=True)
        else:
            st.info("ℹ️ لا توجد بيانات لعرض المخطط")
    
    with col_chart2:
        st.markdown("### 📈 حالة مهام الصيانة")
        fig2 = create_maintenance_status_chart(st.session_state.system_data)
        if fig2:
            st.plotly_chart(fig2, use_container_width=True)
        else:
            st.info("ℹ️ لا توجد بيانات لعرض المخطط")
    
    st.markdown("---")
    
    # المهام القريبة
    st.markdown("### 🔔 المهام القريبة")
    upcoming = check_upcoming_maintenance(st.session_state.system_data)
    
    if upcoming:
        for task in upcoming[:5]:  # عرض أول 5 مهام فقط
            remaining_hours = task.get("remaining_hours", 0)
            
            if remaining_hours <= 0:
                status_text = "⏰ **متأخرة**"
                color = "#ff4444"
            elif remaining_hours <= 24:
                status_text = "⚠ **قريبة**"
                color = "#ff9900"
            else:
                status_text = "🕐 **قادمة**"
                color = "#33b5e5"
            
            st.markdown(f"""
            <div style="background-color:{color}10; padding:10px; border-radius:5px; margin-bottom:5px; border-left:4px solid {color};">
                <div style="display:flex; justify-content:space-between;">
                    <div>
                        <strong>{task.get('machine_name', 'غير معروف')}</strong><br>
                        <small>{task.get('maintenance_type', 'صيانة')}</small>
                    </div>
                    <div style="text-align:right;">
                        {status_text}<br>
                        <small>{remaining_hours} ساعة متبقية</small>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)
        
        if len(upcoming) > 5:
            st.info(f"و {len(upcoming) - 5} مهمة أخرى...")
    else:
        st.success("🎉 لا توجد مهام صيانة قريبة حالياً!")
    
    st.markdown("---")
    
    # أحدث عمليات الصيانة
    st.markdown("### 📝 أحدث عمليات الصيانة")
    history = st.session_state.system_data.get("maintenance_history", {})
    
    if history:
        # تحويل السجل إلى قائمة وترتيبها حسب التاريخ
        history_list = []
        for history_id, entry in history.items():
            try:
                date_obj = datetime.fromisoformat(entry.get("completion_date", ""))
                history_list.append((date_obj, entry))
            except:
                pass
        
        # ترتيب تنازلي حسب التاريخ
        history_list.sort(reverse=True)
        
        # عرض آخر 5 عمليات
        for date_obj, entry in history_list[:5]:
            st.markdown(f"""
            <div style="background-color:#f5f5f5; padding:10px; border-radius:5px; margin-bottom:5px;">
                <div style="display:flex; justify-content:space-between;">
                    <div>
                        <strong>{entry.get('machine_name', 'غير معروف')}</strong><br>
                        <small>{entry.get('maintenance_type', 'صيانة')}</small>
                    </div>
                    <div style="text-align:right;">
                        <small>{date_obj.strftime('%Y-%m-%d')}</small><br>
                        <small>بواسطة: {entry.get('completed_by', 'غير معروف')}</small>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.info("ℹ️ لا توجد سجلات صيانة حديثة")

# ===============================
# 🏭 إدارة الماكينات
# ===============================
def show_machines_management():
    """عرض واجهة إدارة الماكينات"""
    st.title("🏭 إدارة الماكينات")
    
    # التحقق من الإجراءات المطلوبة
    if st.session_state.get("show_add_machine", False):
        show_add_machine_ui()
        if st.button("← العودة للقائمة"):
            st.session_state.show_add_machine = False
            st.rerun()
        return
    
    if st.session_state.get("show_update_hours", False) and st.session_state.selected_machine:
        show_update_hours_for_machine(st.session_state.selected_machine)
        return
    
    if st.session_state.get("show_machine_tasks", False) and st.session_state.selected_machine:
        show_machine_tasks(st.session_state.selected_machine)
        return
    
    if st.session_state.get("edit_machine_id"):
        show_edit_machine_ui(st.session_state.edit_machine_id)
        return
    
    # تبويبات إدارة الماكينات
    tab1, tab2, tab3 = st.tabs(["📋 عرض الماكينات", "➕ إضافة ماكينة", "⏱ تحديث الساعات"])
    
    with tab1:
        show_machines_list()
    
    with tab2:
        show_add_machine_ui()
    
    with tab3:
        show_update_hours_ui()

def show_machine_tasks(machine_id):
    """عرض مهام ماكينة معينة"""
    machine = st.session_state.system_data["machines"].get(machine_id, {})
    machine_name = machine.get("name", machine_id)
    
    st.markdown(f"### 🔧 مهام صيانة: {machine_name}")
    
    if st.button("← العودة للقائمة"):
        st.session_state.show_machine_tasks = False
        st.rerun()
    
    # الحصول على مهام الماكينة
    tasks = st.session_state.system_data.get("maintenance_tasks", {})
    machine_tasks = [t for t in tasks.values() if t.get("machine_id") == machine_id]
    
    if not machine_tasks:
        st.info(f"ℹ️ لا توجد مهام صيانة للماكينة '{machine_name}'")
        return
    
    # عرض المهام
    for task in machine_tasks:
        status_color = {
            "مجدولة": "blue",
            "قيد التنفيذ": "orange",
            "مكتملة": "green",
            "متأخرة": "red",
            "ملغاة": "gray"
        }.get(task.get("status", "مجدولة"), "blue")
        
        st.markdown(f"""
        <div style="border:1px solid {status_color}; border-radius:5px; padding:10px; margin-bottom:10px;">
            <div style="display:flex; justify-content:space-between;">
                <div>
                    <strong>{task.get('maintenance_type', 'صيانة')}</strong><br>
                    <small>{task.get('description', '')}</small>
                </div>
                <div style="text-align:right;">
                    <span style="color:{status_color}; font-weight:bold;">{task.get('status')}</span><br>
                    <small>{task.get('remaining_hours', 0)} ساعة متبقية</small>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

def show_update_hours_for_machine(machine_id):
    """عرض واجهة تحديث ساعات لماكينة محددة"""
    machine = st.session_state.system_data["machines"].get(machine_id, {})
    machine_name = machine.get("name", machine_id)
    
    st.markdown(f"### ⏱ تحديث ساعات التشغيل: {machine_name}")
    
    if st.button("← العودة"):
        st.session_state.show_update_hours = False
        st.rerun()
    
    st.info(f"الساعات الحالية: {machine.get('total_operating_hours', 0)}")
    
    hours_to_add = st.number_input("الساعات المضافة", min_value=0, max_value=1000, value=8)
    
    if st.button("💾 تحديث الساعات", type="primary"):
        if hours_to_add > 0:
            if update_machine_operating_hours(st.session_state.system_data, machine_id, hours_to_add):
                save_data(st.session_state.system_data)
                st.success(f"✅ تم تحديث الساعات بنجاح! (+{hours_to_add} ساعة)")
                st.rerun()
            else:
                st.error("❌ فشل تحديث الساعات")

def show_edit_machine_ui(machine_id):
    """عرض واجهة تعديل الماكينة"""
    machine = st.session_state.system_data["machines"].get(machine_id, {})
    
    if not machine:
        st.error("❌ الماكينة غير موجودة")
        st.session_state.edit_machine_id = None
        st.rerun()
        return
    
    st.markdown(f"### ✏ تعديل الماكينة: {machine.get('name', machine_id)}")
    
    if st.button("← العودة للقائمة"):
        st.session_state.edit_machine_id = None
        st.rerun()
    
    with st.form("edit_machine_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            machine_name = st.text_input("اسم الماكينة", value=machine.get("name", ""))
            machine_type = st.selectbox("نوع الماكينة", APP_CONFIG["MACHINE_TYPES"], 
                                      index=APP_CONFIG["MACHINE_TYPES"].index(machine.get("type", "أخرى")) 
                                      if machine.get("type") in APP_CONFIG["MACHINE_TYPES"] else 0)
            model = st.text_input("الموديل", value=machine.get("model", ""))
            serial_number = st.text_input("الرقم التسلسلي", value=machine.get("serial_number", ""))
        
        with col2:
            location = st.text_input("الموقع", value=machine.get("location", ""))
            department = st.text_input("القسم/الإدارة", value=machine.get("department", ""))
            status = st.selectbox("الحالة", ["نشطة", "متوقفة", "تحت الصيانة", "محذوفة"], 
                                index=["نشطة", "متوقفة", "تحت الصيانة", "محذوفة"].index(machine.get("status", "نشطة")))
        
        notes = st.text_area("ملاحظات", value=machine.get("notes", ""))
        
        col_btn1, col_btn2 = st.columns(2)
        with col_btn1:
            submitted = st.form_submit_button("💾 حفظ التعديلات", type="primary")
        with col_btn2:
            delete_machine = st.form_submit_button("🗑 حذف الماكينة", type="secondary")
        
        if submitted:
            # تحديث بيانات الماكينة
            st.session_state.system_data["machines"][machine_id].update({
                "name": machine_name,
                "type": machine_type,
                "model": model,
                "serial_number": serial_number,
                "location": location,
                "department": department,
                "status": status,
                "notes": notes,
                "updated_at": datetime.now().isoformat()
            })
            
            save_data(st.session_state.system_data)
            st.success("✅ تم تحديث بيانات الماكينة بنجاح!")
            st.session_state.edit_machine_id = None
            st.rerun()
        
        if delete_machine:
            # تأكيد الحذف
            confirm = st.checkbox("أؤكد حذف هذه الماكينة")
            if confirm:
                # حذف الماكينة والمهام المرتبطة
                del st.session_state.system_data["machines"][machine_id]
                
                # حذف المهام المرتبطة
                tasks = st.session_state.system_data.get("maintenance_tasks", {})
                tasks_to_delete = [tid for tid, t in tasks.items() if t.get("machine_id") == machine_id]
                for tid in tasks_to_delete:
                    del st.session_state.system_data["maintenance_tasks"][tid]
                
                save_data(st.session_state.system_data)
                st.success("✅ تم حذف الماكينة والمهام المرتبطة بها بنجاح!")
                st.session_state.edit_machine_id = None
                st.rerun()

# ===============================
# 🔧 إدارة مهام الصيانة
# ===============================
def show_maintenance_management():
    """عرض واجهة إدارة مهام الصيانة"""
    st.title("🔧 إدارة مهام الصيانة")
    
    # التحقق من الإجراءات المطلوبة
    if st.session_state.get("show_add_task", False):
        show_add_maintenance_task_ui()
        if st.button("← العودة للقائمة"):
            st.session_state.show_add_task = False
            st.rerun()
        return
    
    if st.session_state.get("complete_task_id"):
        show_complete_specific_task(st.session_state.complete_task_id)
        return
    
    # تبويبات إدارة المهام
    tab1, tab2, tab3 = st.tabs(["📋 عرض المهام", "➕ إضافة مهمة", "✅ إكمال مهمة"])
    
    with tab1:
        show_maintenance_tasks()
    
    with tab2:
        show_add_maintenance_task_ui()
    
    with tab3:
        show_complete_task_ui()

def show_complete_specific_task(task_id):
    """عرض واجهة إكمال مهمة محددة"""
    task = st.session_state.system_data["maintenance_tasks"].get(task_id, {})
    
    if not task:
        st.error("❌ المهمة غير موجودة")
        st.session_state.complete_task_id = None
        st.rerun()
        return
    
    st.markdown(f"### ✅ إكمال مهمة الصيانة")
    st.info(f"الماكينة: {task.get('machine_name', 'غير معروف')}")
    st.info(f"نوع الصيانة: {task.get('maintenance_type', 'صيانة')}")
    
    if st.button("← العودة"):
        st.session_state.complete_task_id = None
        st.rerun()
    
    with st.form("complete_specific_task_form"):
        technician = st.text_input("اسم الفني المنفذ *", placeholder="اسم الفني الذي أجرى الصيانة")
        actual_hours = st.number_input(
            "ساعات التشغيل الفعلية *",
            min_value=0,
            value=task.get("current_hours", 0)
        )
        completion_notes = st.text_area("ملاحظات الإكمال *", placeholder="تفاصيل العمل المنجز")
        
        col_btn1, col_btn2 = st.columns(2)
        with col_btn1:
            submitted = st.form_submit_button("✅ تأكيد الإكمال", type="primary")
        with col_btn2:
            st.form_submit_button("🗑 إلغاء")
        
        if submitted:
            if not technician or not completion_notes:
                st.error("⚠ الرجاء ملء جميع الحقول الإلزامية (*)")
                return
            
            completion_data = {
                "technician": technician,
                "actual_hours": actual_hours,
                "notes": completion_notes
            }
            
            if complete_maintenance_task(st.session_state.system_data, task_id, completion_data):
                save_data(st.session_state.system_data)
                st.success("✅ تم إكمال المهمة بنجاح!")
                st.session_state.complete_task_id = None
                st.rerun()
            else:
                st.error("❌ فشل إكمال المهمة")

def show_task_details(task_id):
    """عرض تفاصيل مهمة محددة"""
    task = st.session_state.system_data["maintenance_tasks"].get(task_id, {})
    
    if not task:
        st.error("❌ المهمة غير موجودة")
        return
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown(f"**رقم المهمة:** {task_id}")
        st.markdown(f"**الماكينة:** {task.get('machine_name', 'غير معروف')}")
        st.markdown(f"**نوع الصيانة:** {task.get('maintenance_type', 'صيانة')}")
        st.markdown(f"**الأولوية:** {task.get('priority', 'متوسطة')}")
        st.markdown(f"**الحالة:** {task.get('status', 'مجدولة')}")
    
    with col2:
        st.markdown(f"**الساعات المجدولة:** {task.get('scheduled_hours', 0)}")
        st.markdown(f"**الساعات الحالية:** {task.get('current_hours', 0)}")
        st.markdown(f"**الساعات المتبقية:** {task.get('remaining_hours', 0)}")
        st.markdown(f"**المسند إلى:** {task.get('assigned_to', 'غير مسند')}")
        st.markdown(f"**تاريخ الإنشاء:** {format_date(task.get('created_at'))}")
    
    st.markdown("**الوصف:**")
    st.write(task.get('description', 'لا يوجد وصف'))
    
    if task.get('notes'):
        st.markdown("**ملاحظات:**")
        st.write(task.get('notes'))

# ===============================
# 📊 التقارير
# ===============================
def show_reports():
    """عرض واجهة التقارير"""
    st.title("📊 التقارير والإحصائيات")
    
    # إحصائيات سريعة
    col1, col2, col3 = st.columns(3)
    
    with col1:
        total_hours = sum(m.get("total_operating_hours", 0) 
                         for m in st.session_state.system_data.get("machines", {}).values())
        st.metric("⏱ إجمالي ساعات التشغيل", f"{total_hours:,}")
    
    with col2:
        avg_hours = total_hours / max(len(st.session_state.system_data.get("machines", {})), 1)
        st.metric("📈 متوسط الساعات للماكينة", f"{avg_hours:.0f}")
    
    with col3:
        completed_tasks = len([t for t in st.session_state.system_data.get("maintenance_history", {}).values()])
        st.metric("✅ المهام المكتملة", completed_tasks)
    
    st.markdown("---")
    
    # تبويبات التقارير
    tab1, tab2, tab3, tab4 = st.tabs(["📈 الرسوم البيانية", "📋 تقرير الماكينات", "🔧 تقرير المهام", "📜 تقرير السجل"])
    
    with tab1:
        show_charts_tab()
    
    with tab2:
        show_machines_report_tab()
    
    with tab3:
        show_tasks_report_tab()
    
    with tab4:
        show_history_report_tab()

def show_charts_tab():
    """عرض تبويب الرسوم البيانية"""
    st.markdown("### 📈 الرسوم البيانية التفاعلية")
    
    # مخطط الساعات المتبقية
    fig1 = create_hours_remaining_chart(st.session_state.system_data)
    if fig1:
        st.plotly_chart(fig1, use_container_width=True)
    else:
        st.info("ℹ️ لا توجد بيانات لعرض المخطط")
    
    # مخطط توزيع أنواع الصيانة
    tasks = st.session_state.system_data.get("maintenance_tasks", {})
    if tasks:
        maintenance_types = {}
        for task in tasks.values():
            maint_type = task.get("maintenance_type", "أخرى")
            maintenance_types[maint_type] = maintenance_types.get(maint_type, 0) + 1
        
        fig2 = px.pie(
            names=list(maintenance_types.keys()),
            values=list(maintenance_types.values()),
            title="توزيع أنواع الصيانة",
            color_discrete_sequence=px.colors.qualitative.Pastel
        )
        fig2.update_traces(textposition='inside', textinfo='percent+label')
        st.plotly_chart(fig2, use_container_width=True)
    
    # مخطط توزيع الأولويات
    if tasks:
        priorities = {}
        for task in tasks.values():
            priority = task.get("priority", "متوسطة")
            priorities[priority] = priorities.get(priority, 0) + 1
        
        fig3 = px.bar(
            x=list(priorities.keys()),
            y=list(priorities.values()),
            title="توزيع مهام الصيانة حسب الأولوية",
            labels={"x": "الأولوية", "y": "العدد"},
            color=list(priorities.values()),
            color_continuous_scale="Reds"
        )
        st.plotly_chart(fig3, use_container_width=True)

def show_machines_report_tab():
    """عرض تبويب تقرير الماكينات"""
    st.markdown("### 📋 تقرير حالة الماكينات")
    
    report_df = generate_machines_report(st.session_state.system_data)
    
    if not report_df.empty:
        # فلترة البحث
        search_machines = st.text_input("🔍 بحث في التقرير:", key="search_machines_report")
        
        if search_machines:
            mask = report_df.apply(lambda row: row.astype(str).str.contains(search_machines, case=False).any(), axis=1)
            filtered_df = report_df[mask]
        else:
            filtered_df = report_df
        
        if not filtered_df.empty:
            st.dataframe(filtered_df, use_container_width=True, height=400)
            
            # خيارات التصدير
            col_exp1, col_exp2 = st.columns(2)
            with col_exp1:
                if st.button("📊 تصدير إلى Excel", key="export_machines_excel"):
                    buffer = BytesIO()
                    with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                        filtered_df.to_excel(writer, sheet_name='تقرير_الماكينات', index=False)
                    
                    st.download_button(
                        label="⬇️ تحميل ملف Excel",
                        data=buffer.getvalue(),
                        file_name=f"تقرير_الماكينات_{datetime.now().strftime('%Y%m%d')}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )
            
            with col_exp2:
                if st.button("📄 تصدير إلى CSV", key="export_machines_csv"):
                    csv = filtered_df.to_csv(index=False, encoding='utf-8-sig')
                    st.download_button(
                        label="⬇️ تحميل ملف CSV",
                        data=csv,
                        file_name=f"تقرير_الماكينات_{datetime.now().strftime('%Y%m%d')}.csv",
                        mime="text/csv"
                    )
        else:
            st.warning("⚠ لم يتم العثور على بيانات تطابق البحث")
    else:
        st.info("ℹ️ لا توجد بيانات لتقرير الماكينات")

def show_tasks_report_tab():
    """عرض تبويب تقرير المهام"""
    st.markdown("### 🔧 تقرير مهام الصيانة")
    
    report_df = generate_maintenance_report(st.session_state.system_data)
    
    if not report_df.empty:
        # فلترة البحث
        search_tasks = st.text_input("🔍 بحث في التقرير:", key="search_tasks_report")
        
        if search_tasks:
            mask = report_df.apply(lambda row: row.astype(str).str.contains(search_tasks, case=False).any(), axis=1)
            filtered_df = report_df[mask]
        else:
            filtered_df = report_df
        
        if not filtered_df.empty:
            st.dataframe(filtered_df, use_container_width=True, height=400)
            
            # خيارات التصدير
            col_exp1, col_exp2 = st.columns(2)
            with col_exp1:
                if st.button("📊 تصدير إلى Excel", key="export_tasks_excel"):
                    buffer = BytesIO()
                    with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                        filtered_df.to_excel(writer, sheet_name='تقرير_المهام', index=False)
                    
                    st.download_button(
                        label="⬇️ تحميل ملف Excel",
                        data=buffer.getvalue(),
                        file_name=f"تقرير_المهام_{datetime.now().strftime('%Y%m%d')}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )
            
            with col_exp2:
                if st.button("📄 تصدير إلى CSV", key="export_tasks_csv"):
                    csv = filtered_df.to_csv(index=False, encoding='utf-8-sig')
                    st.download_button(
                        label="⬇️ تحميل ملف CSV",
                        data=csv,
                        file_name=f"تقرير_المهام_{datetime.now().strftime('%Y%m%d')}.csv",
                        mime="text/csv"
                    )
        else:
            st.warning("⚠ لم يتم العثور على بيانات تطابق البحث")
    else:
        st.info("ℹ️ لا توجد بيانات لتقرير المهام")

def show_history_report_tab():
    """عرض تبويب تقرير السجل"""
    st.markdown("### 📜 تقرير سجل الصيانة")
    
    report_df = generate_history_report(st.session_state.system_data)
    
    if not report_df.empty:
        # فلترة حسب التاريخ
        col_date1, col_date2 = st.columns(2)
        with col_date1:
            start_date = st.date_input("من تاريخ", value=datetime.now() - timedelta(days=30))
        with col_date2:
            end_date = st.date_input("إلى تاريخ", value=datetime.now())
        
        # فلترة البحث
        search_history = st.text_input("🔍 بحث في التقرير:", key="search_history_report")
        
        # تطبيق الفلاتر
        filtered_df = report_df.copy()
        
        # فلترة التاريخ
        if start_date and end_date:
            try:
                filtered_df["تاريخ الإكمال"] = pd.to_datetime(filtered_df["تاريخ الإكمال"], errors='coerce')
                mask = (filtered_df["تاريخ الإكمال"].dt.date >= start_date) & (filtered_df["تاريخ الإكمال"].dt.date <= end_date)
                filtered_df = filtered_df[mask]
            except:
                pass
        
        # فلترة البحث النصي
        if search_history:
            mask = filtered_df.apply(lambda row: row.astype(str).str.contains(search_history, case=False).any(), axis=1)
            filtered_df = filtered_df[mask]
        
        if not filtered_df.empty:
            st.dataframe(filtered_df, use_container_width=True, height=400)
            
            # خيارات التصدير
            col_exp1, col_exp2 = st.columns(2)
            with col_exp1:
                if st.button("📊 تصدير إلى Excel", key="export_history_excel2"):
                    buffer = BytesIO()
                    with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                        filtered_df.to_excel(writer, sheet_name='سجل_الصيانة', index=False)
                    
                    st.download_button(
                        label="⬇️ تحميل ملف Excel",
                        data=buffer.getvalue(),
                        file_name=f"سجل_الصيانة_{datetime.now().strftime('%Y%m%d')}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )
            
            with col_exp2:
                if st.button("📄 تصدير إلى CSV", key="export_history_csv2"):
                    csv = filtered_df.to_csv(index=False, encoding='utf-8-sig')
                    st.download_button(
                        label="⬇️ تحميل ملف CSV",
                        data=csv,
                        file_name=f"سجل_الصيانة_{datetime.now().strftime('%Y%m%d')}.csv",
                        mime="text/csv"
                    )
            
            # إحصائيات السجل
            st.markdown("---")
            st.markdown("#### 📊 إحصائيات السجل")
            
            col_stat1, col_stat2, col_stat3 = st.columns(3)
            with col_stat1:
                total_operations = len(filtered_df)
                st.metric("إجمالي العمليات", total_operations)
            
            with col_stat2:
                if not filtered_df.empty:
                    avg_hours_diff = (filtered_df["الساعات الفعلية"] - filtered_df["الساعات المجدولة"]).mean()
                    st.metric("متوسط فرق الساعات", f"{avg_hours_diff:.1f}")
            
            with col_stat3:
                if not filtered_df.empty:
                    unique_techs = filtered_df["الفني"].nunique()
                    st.metric("عدد الفنيين المختلفين", unique_techs)
        else:
            st.warning("⚠ لم يتم العثور على سجلات تطابق البحث")
    else:
        st.info("ℹ️ لا توجد بيانات لتقرير السجل")

# ===============================
# 🚀 تشغيل التطبيق
# ===============================
if __name__ == "__main__":
    # إضافة تخصيصات CSS
    st.markdown("""
    <style>
    .stButton > button {
        width: 100%;
    }
    .stProgress > div > div > div > div {
        background-color: #4CAF50;
    }
    .css-1d391kg {
        padding-top: 1rem;
    }
    </style>
    """, unsafe_allow_html=True)
    
    main()
