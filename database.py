import pandas as pd
import os
from datetime import datetime
import json
import shutil

class ExcelDatabase:
    def __init__(self, file_path="machines.xlsx"):
        self.file_path = file_path
        self.backup_dir = "backups"
        
        # إنشاء مجلد النسخ الاحتياطي
        os.makedirs(self.backup_dir, exist_ok=True)
        
        # إنشاء ملف Excel جديد إذا لم يكن موجوداً
        if not os.path.exists(self.file_path):
            self.create_new_excel()
    
    def create_new_excel(self):
        """إنشاء ملف Excel جديد"""
        with pd.ExcelWriter(self.file_path, engine='openpyxl') as writer:
            # إنشاء ورقة الماكينات
            machines_df = pd.DataFrame(columns=[
                'id', 'اسم الماكينة', 'الموديل', 'الرقم التسلسلي',
                'تاريخ التركيب', 'إجمالي ساعات التشغيل',
                'آخر تحديث للساعات', 'القسم', 'ملاحظات',
                'نشطة', 'تاريخ الإضافة'
            ])
            machines_df.to_excel(writer, sheet_name='Machines', index=False)
            
            # إنشاء ورقة المهام
            tasks_df = pd.DataFrame(columns=[
                'id', 'معرف الماكينة', 'نوع الصيانة', 'الفترة بين الصيانة (ساعات)',
                'تاريخ آخر صيانة', 'عدد ساعات التشغيل عند آخر صيانة',
                'عدد الساعات المتبقية', 'تاريخ الصيانة القادم',
                'وصف المهمة', 'نشطة', 'تاريخ الإضافة'
            ])
            tasks_df.to_excel(writer, sheet_name='Tasks', index=False)
            
            # إنشاء ورقة السجل
            logs_df = pd.DataFrame(columns=[
                'id', 'معرف الماكينة', 'معرف المهمة', 'تاريخ الصيانة',
                'عدد ساعات التشغيل', 'تمت بواسطة', 'الأجزاء المستبدلة',
                'ملاحظات', 'تاريخ التسجيل'
            ])
            logs_df.to_excel(writer, sheet_name='Logs', index=False)
            
            # إنشاء ورقة الإعدادات
            settings_df = pd.DataFrame({
                'الإعداد': ['إشعار مسبق (أيام)', 'تفعيل النسخ الاحتياطي', 'آخر نسخة احتياطية'],
                'القيمة': ['7', 'نعم', datetime.now().strftime('%Y-%m-%d %H:%M')],
                'الوصف': ['عدد الأيام للإشعار المسبق', 'تفعيل النسخ الاحتياطي التلقائي', 'تاريخ آخر نسخة احتياطية']
            })
            settings_df.to_excel(writer, sheet_name='Settings', index=False)
    
    def load_sheet(self, sheet_name):
        """تحميل ورقة معينة من ملف Excel"""
        try:
            df = pd.read_excel(self.file_path, sheet_name=sheet_name, dtype=str)
            # تحويل الأعمدة الرقمية
            numeric_columns = ['id', 'معرف الماكينة', 'معرف المهمة', 'إجمالي ساعات التشغيل',
                             'الفترة بين الصيانة (ساعات)', 'عدد ساعات التشغيل عند آخر صيانة',
                             'عدد الساعات المتبقية', 'عدد ساعات التشغيل']
            
            for col in numeric_columns:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce')
            
            return df
        except Exception as e:
            print(f"خطأ في تحميل {sheet_name}: {str(e)}")
            return pd.DataFrame()
    
    def save_sheet(self, sheet_name, df):
        """حفظ ورقة معينة في ملف Excel"""
        try:
            # تحميل جميع الأوراق
            with pd.ExcelFile(self.file_path, engine='openpyxl') as xls:
                sheet_names = xls.sheet_names
            
            # حفظ جميع الأوراق
            with pd.ExcelWriter(self.file_path, engine='openpyxl') as writer:
                for sheet in sheet_names:
                    if sheet == sheet_name:
                        df.to_excel(writer, sheet_name=sheet_name, index=False)
                    else:
                        # تحميل الورقة القديمة
                        old_df = pd.read_excel(self.file_path, sheet_name=sheet)
                        old_df.to_excel(writer, sheet_name=sheet, index=False)
            
            return True
        except Exception as e:
            print(f"خطأ في حفظ {sheet_name}: {str(e)}")
            return False
    
    def create_backup(self):
        """إنشاء نسخة احتياطية"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = os.path.join(self.backup_dir, f"backup_{timestamp}.xlsx")
            shutil.copy2(self.file_path, backup_path)
            
            # حذف النسخ القديمة (أكثر من 30 يوم)
            self.clean_old_backups()
            
            return True
        except Exception as e:
            print(f"خطأ في إنشاء النسخة الاحتياطية: {str(e)}")
            return False
    
    def clean_old_backups(self, days=30):
        """حذف النسخ الاحتياطية القديمة"""
        try:
            cutoff_time = datetime.now().timestamp() - (days * 24 * 60 * 60)
            
            for filename in os.listdir(self.backup_dir):
                if filename.endswith('.xlsx'):
                    filepath = os.path.join(self.backup_dir, filename)
                    if os.path.getmtime(filepath) < cutoff_time:
                        os.remove(filepath)
        except Exception as e:
            print(f"خطأ في تنظيف النسخ القديمة: {str(e)}")
    
    # ===============================
    # 🔧 دوال للماكينات
    # ===============================
    def get_machines(self):
        return self.load_sheet('Machines')
    
    def add_machine(self, machine_data):
        machines = self.get_machines()
        
        # إضافة الصف الجديد
        new_df = pd.DataFrame([machine_data])
        machines = pd.concat([machines, new_df], ignore_index=True)
        
        # حفظ وإنشاء نسخة احتياطية
        if self.save_sheet('Machines', machines):
            self.create_backup()
            return True
        return False
    
    def update_machine(self, machine_data):
        machines = self.get_machines()
        
        if machines.empty:
            return False
        
        # البحث عن الصف الموجود
        mask = machines['id'] == machine_data['id']
        if mask.any():
            # تحديث الصف الموجود
            for key, value in machine_data.items():
                machines.loc[mask, key] = value
            
            # حفظ وإنشاء نسخة احتياطية
            if self.save_sheet('Machines', machines):
                self.create_backup()
                return True
        
        return False
    
    def delete_machine(self, machine_id):
        machines = self.get_machines()
        
        if machines.empty:
            return False
        
        # حذف الصف
        machines = machines[machines['id'] != machine_id]
        
        # حفظ وإنشاء نسخة احتياطية
        if self.save_sheet('Machines', machines):
            self.create_backup()
            return True
        return False
    
    # ===============================
    # 🔧 دوال للمهام
    # ===============================
    def get_tasks(self):
        return self.load_sheet('Tasks')
    
    def add_task(self, task_data):
        tasks = self.get_tasks()
        
        # إضافة الصف الجديد
        new_df = pd.DataFrame([task_data])
        tasks = pd.concat([tasks, new_df], ignore_index=True)
        
        # حفظ وإنشاء نسخة احتياطية
        if self.save_sheet('Tasks', tasks):
            self.create_backup()
            return True
        return False
    
    def update_task(self, task_data):
        tasks = self.get_tasks()
        
        if tasks.empty:
            return False
        
        # البحث عن الصف الموجود
        mask = tasks['id'] == task_data['id']
        if mask.any():
            # تحديث الصف الموجود
            for key, value in task_data.items():
                tasks.loc[mask, key] = value
            
            # حفظ وإنشاء نسخة احتياطية
            if self.save_sheet('Tasks', tasks):
                self.create_backup()
                return True
        
        return False
    
    # ===============================
    # 📝 دوال للسجل
    # ===============================
    def get_logs(self):
        return self.load_sheet('Logs')
    
    def add_log(self, log_data):
        logs = self.get_logs()
        
        # إضافة الصف الجديد
        new_df = pd.DataFrame([log_data])
        logs = pd.concat([logs, new_df], ignore_index=True)
        
        # حفظ وإنشاء نسخة احتياطية
        if self.save_sheet('Logs', logs):
            self.create_backup()
            return True
        return False
    
    # ===============================
    # ⚙️ دوال للإعدادات
    # ===============================
    def get_settings(self):
        return self.load_sheet('Settings')
    
    # ===============================
    # 🔧 دوال عامة
    # ===============================
    def force_save(self):
        """إجبار الحفظ"""
        return self.create_backup()
    
    def get_file_info(self):
        """الحصول على معلومات الملف"""
        if os.path.exists(self.file_path):
            stats = os.stat(self.file_path)
            return {
                "size_kb": stats.st_size / 1024,
                "last_modified": datetime.fromtimestamp(stats.st_mtime).strftime("%Y-%m-%d %H:%M"),
                "created": datetime.fromtimestamp(stats.st_ctime).strftime("%Y-%m-%d %H:%M")
            }
        return {}
