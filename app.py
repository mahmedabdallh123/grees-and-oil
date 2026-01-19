import streamlit as st
import pandas as pd
from datetime import datetime
from io import BytesIO
import os
import traceback

# إعداد الصفحة
st.set_page_config(
    page_title="نظام تتبع صيانة الماكينات",
    page_icon="⚙️",
    layout="wide"
)

# العنوان الرئيسي
st.title("⚙️ نظام تتبع صيانة الماكينات")
st.markdown("---")

# تهيئة حالة الجلسة
if 'machines_df' not in st.session_state:
    st.session_state.machines_df = pd.DataFrame()
if 'changes_made' not in st.session_state:
    st.session_state.changes_made = False
if 'data_loaded' not in st.session_state:
    st.session_state.data_loaded = False
if 'debug_mode' not in st.session_state:
    st.session_state.debug_mode = False

# دالة للتصحيح
def debug_log(message):
    if st.session_state.debug_mode:
        st.sidebar.write(f"🔍 DEBUG: {message}")

# دالة لإنشاء ملف Excel جديد إذا لم يكن موجوداً
def initialize_excel_file():
    """إنشاء ملف Excel جديد بالأعمدة المطلوبة إذا لم يكن موجوداً"""
    try:
        if not os.path.exists('machines_data.xlsx'):
            columns = [
                'machine_id', 'machine_name', 'machine_type', 
                'installation_date', 'total_hours', 'last_maintenance_date',
                'last_maintenance_hours', 'oil_change_interval',
                'greasing_interval', 'other_maintenance_interval',
                'next_oil_change_hours', 'next_greasing_hours',
                'next_other_maintenance_hours', 'status'
            ]
            
            df = pd.DataFrame(columns=columns)
            df.to_excel('machines_data.xlsx', index=False, engine='openpyxl')
            debug_log("تم إنشاء ملف Excel جديد")
            return True
        return False
    except Exception as e:
        st.error(f"خطأ في إنشاء ملف Excel: {str(e)}")
        return False

# دالة لتحميل البيانات من Excel
def load_data():
    try:
        debug_log("بدء تحميل البيانات من Excel")
        
        # أولاً: تأكد من وجود الملف
        file_created = initialize_excel_file()
        
        if file_created:
            debug_log("تم إنشاء ملف جديد، إرجاع DataFrame فارغ")
            return pd.DataFrame(columns=[
                'machine_id', 'machine_name', 'machine_type', 
                'installation_date', 'total_hours', 'last_maintenance_date',
                'last_maintenance_hours', 'oil_change_interval',
                'greasing_interval', 'other_maintenance_interval',
                'next_oil_change_hours', 'next_greasing_hours',
                'next_other_maintenance_hours', 'status'
            ])
        
        # تحميل البيانات من الملف
        debug_log("محاولة قراءة ملف Excel")
        df = pd.read_excel('machines_data.xlsx', engine='openpyxl')
        debug_log(f"تم تحميل {len(df)} سجل من Excel")
        
        # تحويل التواريخ من نص إلى تاريخ
        date_columns = ['last_maintenance_date', 'installation_date']
        for col in date_columns:
            if col in df.columns:
                df[col] = pd.to_datetime(df[col], errors='coerce')
        
        return df
    except Exception as e:
        st.error(f"خطأ في تحميل البيانات: {str(e)}")
        debug_log(f"خطأ في التحميل: {str(e)}")
        # إنشاء DataFrame جديد في حالة الخطأ
        return pd.DataFrame(columns=[
            'machine_id', 'machine_name', 'machine_type', 
            'installation_date', 'total_hours', 'last_maintenance_date',
            'last_maintenance_hours', 'oil_change_interval',
            'greasing_interval', 'other_maintenance_interval',
            'next_oil_change_hours', 'next_greasing_hours',
            'next_other_maintenance_hours', 'status'
        ])

# دالة لحفظ البيانات إلى Excel - محسنة
def save_data(df):
    try:
        debug_log(f"بدء حفظ {len(df)} سجل إلى Excel")
        
        if df.empty:
            debug_log("DataFrame فارغ، إنشاء DataFrame جديد بالأعمدة")
            # إنشاء DataFrame جديد بالأعمدة المطلوبة
            columns = [
                'machine_id', 'machine_name', 'machine_type', 
                'installation_date', 'total_hours', 'last_maintenance_date',
                'last_maintenance_hours', 'oil_change_interval',
                'greasing_interval', 'other_maintenance_interval',
                'next_oil_change_hours', 'next_greasing_hours',
                'next_other_maintenance_hours', 'status'
            ]
            df = pd.DataFrame(columns=columns)
        
        # حفظ البيانات
        debug_log("جاري كتابة البيانات إلى الملف...")
        df.to_excel('machines_data.xlsx', index=False, engine='openpyxl')
        
        # التحقق من أن الملف تم حفظه
        if os.path.exists('machines_data.xlsx'):
            file_size = os.path.getsize('machines_data.xlsx')
            debug_log(f"تم حفظ الملف بنجاح! الحجم: {file_size} بايت")
            return True
        else:
            debug_log("❌ فشل في حفظ الملف - الملف غير موجود بعد الحفظ")
            return False
            
    except Exception as e:
        error_msg = f"خطأ في حفظ البيانات: {str(e)}"
        st.error(error_msg)
        debug_log(error_msg)
        debug_log(traceback.format_exc())
        return False

# دالة لحساب العدادات التنازلية
def calculate_countdowns(df):
    if df.empty:
        debug_log("DataFrame فارغ، لا يمكن حساب العدادات")
        return df
    
    debug_log("بدء حساب العدادات التنازلية")
    df = df.copy()
    
    # حساب الساعات المتبقية للتشحيم
    if 'next_greasing_hours' in df.columns and 'total_hours' in df.columns:
        df['greasing_countdown'] = df['next_greasing_hours'] - df['total_hours']
        df['greasing_status'] = df['greasing_countdown'].apply(
            lambda x: '⚠️ يحتاج تشحيم' if x <= 50 else ('🟡 قريب' if x <= 100 else '🟢 جيد')
        )
    
    # حساب الساعات المتبقية لتغيير الزيت
    if 'next_oil_change_hours' in df.columns and 'total_hours' in df.columns:
        df['oil_change_countdown'] = df['next_oil_change_hours'] - df['total_hours']
        df['oil_change_status'] = df['oil_change_countdown'].apply(
            lambda x: '⚠️ يحتاج تغيير زيت' if x <= 50 else ('🟡 قريب' if x <= 100 else '🟢 جيد')
        )
    
    # حساب الساعات المتبقية للصيانة الأخرى
    if 'next_other_maintenance_hours' in df.columns and 'total_hours' in df.columns:
        df['other_maintenance_countdown'] = df['next_other_maintenance_hours'] - df['total_hours']
        df['other_maintenance_status'] = df['other_maintenance_countdown'].apply(
            lambda x: '⚠️ يحتاج صيانة' if x <= 50 else ('🟡 قريب' if x <= 100 else '🟢 جيد')
        )
    
    # تحديد الحالة العامة للماكينة
    df['overall_status'] = '🟢 جيد'
    if 'greasing_status' in df.columns:
        df.loc[df['greasing_status'].str.contains('⚠️'), 'overall_status'] = '⚠️ يحتاج صيانة'
    if 'oil_change_status' in df.columns:
        df.loc[df['oil_change_status'].str.contains('⚠️'), 'overall_status'] = '⚠️ يحتاج صيانة'
    if 'other_maintenance_status' in df.columns:
        df.loc[df['other_maintenance_status'].str.contains('⚠️'), 'overall_status'] = '⚠️ يحتاج صيانة'
    
    debug_log("تم حساب العدادات بنجاح")
    return df

# دالة لإضافة ماكينة جديدة - محسنة
def add_machine(machine_data):
    try:
        debug_log(f"بدء إضافة ماكينة: {machine_data['machine_name']}")
        
        # الحصول على البيانات الحالية
        current_df = st.session_state.machines_df.copy()
        
        # إن DataFrame جديد للماكينة
        new_machine_df = pd.DataFrame([machine_data])
        
        # دمج البيانات القديمة مع الجديدة
        if current_df.empty:
            updated_df = new_machine_df
        else:
            updated_df = pd.concat([current_df, new_machine_df], ignore_index=True)
        
        # حساب العدادات
        updated_df = calculate_countdowns(updated_df)
        
        # حفظ في session state
        st.session_state.machines_df = updated_df
        
        # حفظ في ملف Excel
        if save_data(updated_df):
            debug_log(f"تم حفظ الماكينة {machine_data['machine_name']} بنجاح")
            return True
        else:
            debug_log(f"فشل في حفظ الماكينة {machine_data['machine_name']}")
            return False
            
    except Exception as e:
        error_msg = f"خطأ في إضافة الماكينة: {str(e)}"
        st.error(error_msg)
        debug_log(error_msg)
        return False

# تحميل البيانات عند بدء التشغيل
if not st.session_state.data_loaded:
    debug_log("جاري تحميل البيانات للمرة الأولى")
    machines_df = load_data()
    if not machines_df.empty:
        machines_df = calculate_countdowns(machines_df)
    st.session_state.machines_df = machines_df
    st.session_state.data_loaded = True
    debug_log(f"تم تحميل {len(machines_df)} ماكينة")
else:
    machines_df = st.session_state.machines_df
    debug_log(f"استخدام البيانات من session state: {len(machines_df)} ماكينة")

# الشريط الجانبي
with st.sidebar:
    st.header("🛠️ التحكم في النظام")
    
    # وضع التصحيح
    st.session_state.debug_mode = st.checkbox("وضع التصحيح", value=False)
    
    # قسم إضافة ماكينة جديدة
    st.subheader("➕ إضافة ماكينة جديدة")
    
    with st.form("add_machine_form", clear_on_submit=True):
        machine_name = st.text_input("اسم الماكينة *", placeholder="مثل: ماكينة الخياطة ١", key="machine_name_input")
        
        col1, col2 = st.columns(2)
        with col1:
            machine_type = st.selectbox("نوع الماكينة *", 
                                       ["معدات ثقيلة", "معدات خفيفة", "مولدات", 
                                        "آلات تصنيع", "مركبات", "أخرى"],
                                       key="machine_type_select")
            installation_date = st.date_input("تاريخ التركيب *", datetime.now(), key="install_date")
        
        with col2:
            total_hours = st.number_input("إجمالي ساعات التشغيل *", 
                                         min_value=0.0, value=0.0, step=10.0,
                                         key="total_hours_input")
            last_maintenance_date = st.date_input("تاريخ آخر صيانة *", datetime.now(), key="last_maint_date")
        
        last_maintenance_hours = st.number_input(
            "ساعات التشغيل عند آخر صيانة *", 
            min_value=0.0, value=0.0, step=10.0,
            key="last_maint_hours"
        )
        
        st.subheader("⏰ فترات الصيانة (بالساعات)")
        
        col1, col2, col3 = st.columns(3)
        with col1:
            oil_interval = st.number_input("تغيير الزيت *", 
                                          min_value=1, value=1000, step=50,
                                          key="oil_interval_input")
        
        with col2:
            greasing_interval = st.number_input("التشحيم *", 
                                               min_value=1, value=500, step=50,
                                               key="greasing_interval_input")
        
        with col3:
            other_interval = st.number_input("صيانة أخرى", 
                                            min_value=1, value=2000, step=100,
                                            key="other_interval_input")
        
        submit_machine = st.form_submit_button("✅ إضافة الماكينة")
        
        if submit_machine:
            if not machine_name:
                st.error("❌ يرجى إدخال اسم الماكينة")
            else:
                # حساب القيم التالية للصيانة
                next_oil_hours = last_maintenance_hours + oil_interval
                next_greasing_hours = last_maintenance_hours + greasing_interval
                next_other_hours = last_maintenance_hours + other_interval
                
                # إنشاء سجل جديد
                new_machine = {
                    'machine_id': f"MCH-{len(machines_df) + 1:04d}",
                    'machine_name': machine_name,
                    'machine_type': machine_type,
                    'installation_date': installation_date,
                    'total_hours': total_hours,
                    'last_maintenance_date': last_maintenance_date,
                    'last_maintenance_hours': last_maintenance_hours,
                    'oil_change_interval': oil_interval,
                    'greasing_interval': greasing_interval,
                    'other_maintenance_interval': other_interval,
                    'next_oil_change_hours': next_oil_hours,
                    'next_greasing_hours': next_greasing_hours,
                    'next_other_maintenance_hours': next_other_hours,
                    'status': 'نشطة'
                }
                
                # إضافة الماكينة باستخدام الدالة الجديدة
                if add_machine(new_machine):
                    st.success(f"✅ تمت إضافة الماكينة '{machine_name}' بنجاح!")
                    
                    # عرض تفاصيل الحفظ
                    if os.path.exists('machines_data.xlsx'):
                        file_info = os.stat('machines_data.xlsx')
                        st.sidebar.info(f"تم الحفظ في: machines_data.xlsx ({file_info.st_size} بايت)")
                    
                    # تحديث البيانات المعروضة
                    machines_df = st.session_state.machines_df
                    st.rerun()
                else:
                    st.error("❌ فشل في حفظ الماكينة. حاول مرة أخرى.")
    
    st.markdown("---")
    
    # قسم إدارة الملفات
    st.subheader("📁 إدارة قاعدة البيانات")
    
    # عرض حالة الملف
    if os.path.exists('machines_data.xlsx'):
        file_info = os.stat('machines_data.xlsx')
        modified_time = datetime.fromtimestamp(file_info.st_mtime)
        
        with st.expander("🔍 حالة قاعدة البيانات", expanded=False):
            st.write(f"**الاسم:** machines_data.xlsx")
            st.write(f"**الحجم:** {file_info.st_size:,} بايت")
            st.write(f"**آخر تعديل:** {modified_time.strftime('%Y-%m-%d %H:%M:%S')}")
            st.write(f"**عدد الماكينات:** {len(machines_df)}")
            
            if not machines_df.empty:
                st.write("**عينة من البيانات:**")
                st.dataframe(machines_df[['machine_id', 'machine_name', 'machine_type']].head(3))
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("🔄 تحديث البيانات", use_container_width=True, key="refresh_data"):
            with st.spinner("جاري تحديث البيانات..."):
                machines_df = load_data()
                if not machines_df.empty:
                    machines_df = calculate_countdowns(machines_df)
                st.session_state.machines_df = machines_df
                st.session_state.data_loaded = True
                st.success("✅ تم تحديث البيانات!")
                st.rerun()
    
    with col2:
        if not machines_df.empty:
            buffer = BytesIO()
            with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                machines_df.to_excel(writer, index=False, sheet_name='Machines')
            
            st.download_button(
                label="📥 تصدير Excel",
                data=buffer.getvalue(),
                file_name=f"machines_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True,
                key="export_excel"
            )
    
    st.markdown("---")
    
    # قسم الاختبار والحفظ
    st.subheader("🧪 اختبار الحفظ")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("💾 اختبار الحفظ", use_container_width=True, key="test_save"):
            if not machines_df.empty:
                if save_data(machines_df):
                    st.success("✅ تم اختبار الحفظ بنجاح!")
                else:
                    st.error("❌ فشل في اختبار الحفظ")
            else:
                st.warning("⚠️ لا توجد بيانات لحفظها")
    
    with col2:
        if st.button("📋 عرض البيانات", use_container_width=True, key="show_data"):
            if not machines_df.empty:
                with st.expander("عرض البيانات المخزنة", expanded=True):
                    st.write(f"عدد السجلات: {len(machines_df)}")
                    st.dataframe(machines_df)
            else:
                st.info("لا توجد بيانات مخزنة")
    
    # إنشاء بيانات تجريبية
    st.markdown("---")
    if st.button("🎯 إنشاء بيانات تجريبية", use_container_width=True, key="create_sample"):
        if machines_df.empty:
            with st.spinner("جاري إنشاء البيانات التجريبية..."):
                sample_data = [
                    {
                        'machine_id': 'MCH-0001',
                        'machine_name': 'مولد كهرباء ١',
                        'machine_type': 'مولدات',
                        'installation_date': datetime(2023, 1, 15),
                        'total_hours': 2450,
                        'last_maintenance_date': datetime(2024, 1, 10),
                        'last_maintenance_hours': 2400,
                        'oil_change_interval': 1000,
                        'greasing_interval': 500,
                        'other_maintenance_interval': 2000,
                        'next_oil_change_hours': 3400,
                        'next_greasing_hours': 2900,
                        'next_other_maintenance_hours': 4400,
                        'status': 'نشطة'
                    },
                    {
                        'machine_id': 'MCH-0002',
                        'machine_name': 'ماكينة الخياطة الكبيرة',
                        'machine_type': 'آلات تصنيع',
                        'installation_date': datetime(2023, 3, 20),
                        'total_hours': 1850,
                        'last_maintenance_date': datetime(2024, 2, 5),
                        'last_maintenance_hours': 1800,
                        'oil_change_interval': 800,
                        'greasing_interval': 400,
                        'other_maintenance_interval': 1500,
                        'next_oil_change_hours': 2600,
                        'next_greasing_hours': 2200,
                        'next_other_maintenance_hours': 3300,
                        'status': 'نشطة'
                    }
                ]
                
                for machine in sample_data:
                    add_machine(machine)
                
                st.success("✅ تم إنشاء البيانات التجريبية بنجاح!")
                st.rerun()
        else:
            st.warning("⚠️ قاعدة البيانات تحتوي بالفعل على بيانات")

# علامات التبويب الرئيسية
tab1, tab2, tab3, tab4 = st.tabs(["🏠 الرئيسية", "📋 جميع الماكينات", "🔧 تسجيل صيانة", "⚙️ الإعدادات"])

with tab1:
    st.header("🏠 الصفحة الرئيسية")
    
    if machines_df.empty:
        st.info("""
        ## 🎯 مرحباً بك في نظام تتبع صيانة الماكينات
        
        ### لبدء الاستخدام:
        1. **أضف أول ماكينة** من الشريط الجانبي ← "➕ إضافة ماكينة جديدة"
        2. **أو أنشئ بيانات تجريبية** باستخدام زر "🎯 إنشاء بيانات تجريبية"
        
        ### حالة النظام:
        - 📁 قاعدة البيانات: {} 
        - 📊 عدد الماكينات: 0
        """.format("✅ جاهزة" if os.path.exists('machines_data.xlsx') else "❌ غير موجودة"))
    else:
        # إحصائيات سريعة
        st.subheader("📊 إحصائيات سريعة")
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            total_machines = len(machines_df)
            st.metric("إجمالي الماكينات", total_machines)
        
        with col2:
            if 'status' in machines_df.columns:
                active_machines = len(machines_df[machines_df['status'] == 'نشطة'])
                st.metric("الماكينات النشطة", active_machines)
            else:
                st.metric("الماكينات النشطة", len(machines_df))
        
        with col3:
            if 'overall_status' in machines_df.columns:
                need_maintenance = len(machines_df[machines_df['overall_status'].str.contains('⚠️')])
                st.metric("تحتاج صيانة", need_maintenance, delta_color="inverse")
            else:
                st.metric("تحتاج صيانة", 0)
        
        with col4:
            if 'total_hours' in machines_df.columns:
                total_hours = machines_df['total_hours'].sum()
                st.metric("إجمالي الساعات", f"{total_hours:,.0f}")
            else:
                st.metric("إجمالي الساعات", 0)
        
        st.markdown("---")
        
        # الماكينات التي تحتاج صيانة عاجلة
        if 'overall_status' in machines_df.columns:
            urgent_machines = machines_df[machines_df['overall_status'].str.contains('⚠️')]
            
            if not urgent_machines.empty:
                st.subheader("🚨 الماكينات التي تحتاج صيانة عاجلة")
                
                for _, machine in urgent_machines.iterrows():
                    with st.container():
                        col1, col2, col3 = st.columns([2, 2, 1])
                        
                        with col1:
                            st.write(f"**{machine['machine_name']}**")
                            st.write(f"نوع: {machine.get('machine_type', 'غير محدد')}")
                        
                        with col2:
                            st.write(f"ساعات التشغيل: {machine.get('total_hours', 0):,.0f}")
                            if 'greasing_countdown' in machine and machine['greasing_countdown'] < 0:
                                st.write(f"**تأخر التشحيم:** {abs(machine['greasing_countdown']):,.0f} ساعة")
                        
                        with col3:
                            st.error("يحتاج صيانة عاجلة!")
                        
                        st.markdown("---")

with tab2:
    st.header("📋 جميع الماكينات")
    
    if machines_df.empty:
        st.info("لا توجد ماكينات لعرضها. أضف ماكينة جديدة من الشريط الجانبي.")
    else:
        # خيارات البحث والتصفية
        col1, col2 = st.columns(2)
        
        with col1:
            search_term = st.text_input("🔍 بحث بالاسم", "", key="search_name_tab2")
        
        with col2:
            # التحقق من وجود العمود machine_type
            if 'machine_type' in machines_df.columns and not machines_df.empty:
                machine_types = ["الكل"] + list(machines_df['machine_type'].dropna().unique())
                filter_type = st.selectbox("تصفية بالنوع", machine_types, key="filter_type_tab2")
            else:
                filter_type = "الكل"
                st.selectbox("تصفية بالنوع", ["الكل"], disabled=True, key="filter_type_disabled")
        
        # تطبيق الفلاتر
        filtered_df = machines_df.copy()
        
        if search_term:
            filtered_df = filtered_df[filtered_df['machine_name'].astype(str).str.contains(search_term, case=False, na=False)]
        
        if filter_type != "الكل" and 'machine_type' in filtered_df.columns:
            filtered_df = filtered_df[filtered_df['machine_type'] == filter_type]
        
        # عرض عدد النتائج
        st.write(f"**عدد النتائج:** {len(filtered_df)} ماكينة")
        
        # عرض البيانات
        if not filtered_df.empty:
            # تحديد الأعمدة المتاحة للعرض
            available_columns = []
            possible_columns = [
                'machine_id', 'machine_name', 'machine_type', 
                'total_hours', 'last_maintenance_date', 'overall_status',
                'greasing_countdown', 'oil_change_countdown'
            ]
            
            for col in possible_columns:
                if col in filtered_df.columns:
                    available_columns.append(col)
            
            if available_columns:
                column_names = {
                    'machine_id': 'رقم الماكينة',
                    'machine_name': 'اسم الماكينة',
                    'machine_type': 'النوع',
                    'total_hours': 'ساعات التشغيل',
                    'last_maintenance_date': 'تاريخ آخر صيانة',
                    'overall_status': 'الحالة',
                    'greasing_countdown': 'متبقي للتشحيم',
                    'oil_change_countdown': 'متبقي لتغيير الزيت'
                }
                
                # إنشاء نسخة من البيانات للعرض
                display_df = filtered_df[available_columns].copy()
                
                # تنسيق التواريخ
                if 'last_maintenance_date' in display_df.columns:
                    display_df['last_maintenance_date'] = display_df['last_maintenance_date'].dt.strftime('%Y-%m-%d')
                
                st.dataframe(
                    display_df.rename(columns=column_names),
                    use_container_width=True,
                    height=400
                )
            else:
                st.warning("لا توجد أعمدة بيانات متاحة للعرض")
        else:
            st.warning("⚠️ لا توجد نتائج تطابق معايير البحث")

with tab3:
    st.header("🔧 تسجيل عملية صيانة")
    
    if machines_df.empty:
        st.info("لا توجد ماكينات لتسجيل صيانة. أضف ماكينة أولاً.")
    else:
        col1, col2 = st.columns(2)
        
        with col1:
            if 'machine_name' in machines_df.columns and not machines_df.empty:
                selected_machine = st.selectbox(
                    "اختر الماكينة",
                    machines_df['machine_name'].tolist(),
                    key="select_machine_tab3"
                )
            else:
                selected_machine = None
                st.selectbox("اختر الماكينة", ["لا توجد ماكينات"], disabled=True, key="select_machine_disabled")
        
        with col2:
            maintenance_type = st.selectbox(
                "نوع الصيانة",
                ["تغيير زيت", "تشحيم", "صيانة دورية", "إصلاح", "فحص", "تنظيف", "أخرى"],
                key="maintenance_type_tab3"
            )
        
        if selected_machine and not machines_df.empty:
            # الحصول على بيانات الماكينة المختارة
            machine_match = machines_df[machines_df['machine_name'] == selected_machine]
            
            if not machine_match.empty:
                machine_data = machine_match.iloc[0]
                
                st.subheader("معلومات الماكينة المختارة")
                
                info_col1, info_col2 = st.columns(2)
                
                with info_col1:
                    st.info(f"**الرقم:** {machine_data.get('machine_id', 'غير معروف')}")
                    st.info(f"**النوع:** {machine_data.get('machine_type', 'غير معروف')}")
                    st.info(f"**فترة التشحيم:** كل {machine_data.get('greasing_interval', 0):,.0f} ساعة")
                
                with info_col2:
                    st.info(f"**ساعات التشغيل:** {machine_data.get('total_hours', 0):,.0f}")
                    if 'last_maintenance_date' in machine_data:
                        last_date = machine_data['last_maintenance_date']
                        if pd.notna(last_date):
                            st.info(f"**آخر صيانة:** {last_date.strftime('%Y-%m-%d')}")
                        else:
                            st.info(f"**آخر صيانة:** غير معروف")
                    else:
                        st.info(f"**آخر صيانة:** غير معروف")
                    
                    if 'greasing_countdown' in machine_data:
                        countdown = machine_data['greasing_countdown']
                        if countdown <= 0:
                            st.error(f"**تأخر التشحيم:** {abs(countdown):,.0f} ساعة")
                        else:
                            st.info(f"**متبقي للتشحيم:** {countdown:,.0f} ساعة")
        
        st.subheader("تفاصيل الصيانة")
        
        with st.form("record_maintenance_form", clear_on_submit=True):
            col1, col2 = st.columns(2)
            
            with col1:
                maintenance_date = st.date_input("تاريخ الصيانة", datetime.now(), key="maint_date_input")
                
                if selected_machine and not machines_df.empty:
                    current_hours = st.number_input(
                        "ساعات التشغيل الحالية",
                        min_value=0.0,
                        value=float(machine_data.get('total_hours', 0)),
                        step=10.0,
                        key="current_hours_input"
                    )
                else:
                    current_hours = st.number_input("ساعات التشغيل الحالية", min_value=0.0, value=0.0, step=10.0, key="current_hours_default")
            
            with col2:
                technician = st.text_input("اسم الفني (اختياري)", key="technician_input")
                cost = st.number_input("التكلفة (ريال)", min_value=0.0, value=0.0, step=50.0, key="cost_input")
            
            notes = st.text_area("ملاحظات إضافية", height=100, key="notes_input", placeholder="أدخل أي ملاحظات إضافية عن الصيانة...")
            
            submit_btn = st.form_submit_button("✅ تسجيل الصيانة", use_container_width=True, key="submit_maintenance")
            
            if submit_btn and selected_machine:
                # تحديث بيانات الماكينة
                idx = machines_df[machines_df['machine_name'] == selected_machine].index[0]
                
                machines_df.at[idx, 'total_hours'] = current_hours
                machines_df.at[idx, 'last_maintenance_date'] = maintenance_date
                machines_df.at[idx, 'last_maintenance_hours'] = current_hours
                
                # تحديث مواعيد الصيانة القادمة
                if maintenance_type == "تغيير زيت" and 'oil_change_interval' in machines_df.columns:
                    next_oil = current_hours + machines_df.at[idx, 'oil_change_interval']
                    machines_df.at[idx, 'next_oil_change_hours'] = next_oil
                
                elif maintenance_type == "تشحيم" and 'greasing_interval' in machines_df.columns:
                    next_grease = current_hours + machines_df.at[idx, 'greasing_interval']
                    machines_df.at[idx, 'next_greasing_hours'] = next_grease
                
                elif maintenance_type == "صيانة دورية" and 'other_maintenance_interval' in machines_df.columns:
                    next_other = current_hours + machines_df.at[idx, 'other_maintenance_interval']
                    machines_df.at[idx, 'next_other_maintenance_hours'] = next_other
                
                # إعادة حساب العدادات
                machines_df = calculate_countdowns(machines_df)
                
                # حفظ التغييرات
                if save_data(machines_df):
                    st.success(f"✅ تم تسجيل صيانة '{maintenance_type}' للماكينة '{selected_machine}' بنجاح!")
                    st.session_state.machines_df = machines_df
                    
                    # عرض ملخص
                    with st.expander("📋 عرض ملخص الصيانة", expanded=True):
                        col1, col2 = st.columns(2)
                        with col1:
                            st.write(f"**الماكينة:** {selected_machine}")
                            st.write(f"**نوع الصيانة:** {maintenance_type}")
                            st.write(f"**التاريخ:** {maintenance_date}")
                            st.write(f"**الساعات:** {current_hours:,.0f}")
                        
                        with col2:
                            if technician:
                                st.write(f"**الفني:** {technician}")
                            if cost > 0:
                                st.write(f"**التكلفة:** {cost:,.0f} ريال")
                            if notes:
                                st.write(f"**الملاحظات:** {notes}")
                    
                    st.rerun()
                else:
                    st.error("❌ فشل في حفظ بيانات الصيانة. حاول مرة أخرى.")

with tab4:
    st.header("⚙️ إعدادات النظام")
    
    st.subheader("🧹 صيانة النظام")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("🔄 إعادة تحميل البيانات", use_container_width=True, key="reload_data"):
            with st.spinner("جاري إعادة تحميل البيانات..."):
                machines_df = load_data()
                if not machines_df.empty:
                    machines_df = calculate_countdowns(machines_df)
                st.session_state.machines_df = machines_df
                st.success("✅ تم إعادة تحميل البيانات!")
                st.rerun()
    
    with col2:
        if st.button("🔍 فحص قاعدة البيانات", use_container_width=True, key="check_database"):
            if os.path.exists('machines_data.xlsx'):
                file_info = os.stat('machines_data.xlsx')
                st.success(f"✅ قاعدة البيانات موجودة ({file_info.st_size:,} بايت)")
            else:
                st.error("❌ قاعدة البيانات غير موجودة")
    
    with col3:
        if st.button("🗑️ مسح ذاكرة التخزين", use_container_width=True, key="clear_cache"):
            st.session_state.data_loaded = False
            st.success("✅ تم مسح ذاكرة التخزين المؤقت")
    
    st.markdown("---")
    
    st.subheader("📊 معلومات النظام")
    
    info_col1, info_col2 = st.columns(2)
    
    with info_col1:
        st.write("**معلومات الملف:**")
        if os.path.exists('machines_data.xlsx'):
            file_info = os.stat('machines_data.xlsx')
            st.write(f"- الحجم: {file_info.st_size:,} بايت")
            st.write(f"- آخر تعديل: {datetime.fromtimestamp(file_info.st_mtime).strftime('%Y-%m-%d %H:%M:%S')}")
        else:
            st.write("- الملف غير موجود")
        
        st.write("**معلومات البيانات:**")
        st.write(f"- عدد الماكينات: {len(machines_df)}")
        st.write(f"- عدد الأعمدة: {len(machines_df.columns) if not machines_df.empty else 0}")
    
    with info_col2:
        st.write("**حالة النظام:**")
        st.write(f"- تم تحميل البيانات: {'✅' if st.session_state.data_loaded else '❌'}")
        st.write(f"- وضع التصحيح: {'✅ تشغيل' if st.session_state.debug_mode else '❌ إيقاف'}")
        st.write("- الإصدار: 2.0 (معدل)")

# تذييل الصفحة
st.markdown("---")
st.markdown("""
<div style="text-align: center; color: gray;">
    <p>نظام تتبع صيانة الماكينات | الإصدار 2.0 (معدل)</p>
    <p>✅ قاعدة البيانات: machines_data.xlsx</p>
    <p>📁 المسار: {}</p>
    <p>لتشغيل النظام: <code>streamlit run app.py</code></p>
</div>
""".format(os.path.abspath('machines_data.xlsx') if os.path.exists('machines_data.xlsx') else "غير محدد"), unsafe_allow_html=True)

# تشغيل دالة التهيئة عند بدء التشغيل
initialize_excel_file()
