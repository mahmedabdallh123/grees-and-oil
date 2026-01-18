import streamlit as st
import pandas as pd
from datetime import datetime
from io import BytesIO
import os

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

# دالة لتحميل البيانات من Excel
def load_data():
    try:
        df = pd.read_excel('machines_data.xlsx', engine='openpyxl')
        # تحويل التواريخ من نص إلى تاريخ
        date_columns = ['last_maintenance_date', 'installation_date']
        for col in date_columns:
            if col in df.columns:
                df[col] = pd.to_datetime(df[col], errors='coerce')
        return df
    except FileNotFoundError:
        # إنشاء DataFrame جديد إذا لم يوجد الملف
        return pd.DataFrame(columns=[
            'machine_id', 'machine_name', 'machine_type', 
            'installation_date', 'total_hours', 'last_maintenance_date',
            'last_maintenance_hours', 'oil_change_interval',
            'greasing_interval', 'other_maintenance_interval',
            'next_oil_change_hours', 'next_greasing_hours',
            'next_other_maintenance_hours', 'status'
        ])

# دالة لحفظ البيانات إلى Excel
def save_data(df):
    df.to_excel('machines_data.xlsx', index=False, engine='openpyxl')
    return True

# دالة لحساب العدادات التنازلية
def calculate_countdowns(df):
    if df.empty:
        return df
    
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
    
    return df

# تحميل البيانات
machines_df = load_data()
if not machines_df.empty:
    machines_df = calculate_countdowns(machines_df)

# الشريط الجانبي
with st.sidebar:
    st.header("🛠️ التحكم في النظام")
    
    # قسم إضافة ماكينة جديدة
    st.subheader("إضافة ماكينة جديدة")
    
    with st.form("add_machine_form"):
        machine_name = st.text_input("اسم الماكينة", key="machine_name")
        machine_type = st.selectbox("نوع الماكينة", ["معدات ثقيلة", "معدات خفيفة", "مولدات", "أخرى"], key="machine_type")
        
        col1, col2 = st.columns(2)
        with col1:
            installation_date = st.date_input("تاريخ التركيب", datetime.now(), key="installation_date")
            total_hours = st.number_input("إجمالي ساعات التشغيل", min_value=0.0, value=0.0, step=10.0, key="total_hours")
        
        with col2:
            last_maintenance_date = st.date_input("تاريخ آخر صيانة", datetime.now(), key="last_maintenance_date")
            last_maintenance_hours = st.number_input("ساعات التشغيل عند آخر صيانة", 
                                                    min_value=0.0, value=0.0, step=10.0, key="last_maintenance_hours")
        
        st.subheader("فترات الصيانة (بالساعات)")
        oil_interval = st.number_input("فترة تغيير الزيت", min_value=1, value=1000, step=50, key="oil_interval")
        greasing_interval = st.number_input("فترة التشحيم", min_value=1, value=500, step=50, key="greasing_interval")
        other_interval = st.number_input("فترة الصيانة الأخرى", min_value=1, value=2000, step=100, key="other_interval")
        
        submit_machine = st.form_submit_button("إضافة الماكينة")
        
        if submit_machine and machine_name:
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
            
            machines_df = pd.concat([machines_df, pd.DataFrame([new_machine])], ignore_index=True)
            save_data(machines_df)
            st.session_state.changes_made = True
            st.session_state.machines_df = machines_df
            st.success(f"✅ تمت إضافة الماكينة '{machine_name}' بنجاح!")
            st.rerun()
    
    st.markdown("---")
    
    # قسم التحميل اليدوي لملف Excel
    st.subheader("تحميل ملف Excel")
    
    uploaded_file = st.file_uploader("اختر ملف Excel", type=['xlsx', 'xls'], key="excel_uploader")
    
    if uploaded_file is not None:
        try:
            new_df = pd.read_excel(uploaded_file, engine='openpyxl')
            if not new_df.empty:
                save_data(new_df)
                st.session_state.machines_df = new_df
                st.success("✅ تم تحميل الملف بنجاح!")
                st.rerun()
        except Exception as e:
            st.error(f"❌ خطأ في تحميل الملف: {str(e)}")
    
    st.markdown("---")
    
    # خيارات إضافية
    if st.button("🔄 تحديث البيانات"):
        machines_df = load_data()
        if not machines_df.empty:
            machines_df = calculate_countdowns(machines_df)
        st.session_state.machines_df = machines_df
        st.success("✅ تم تحديث البيانات!")
        st.rerun()
    
    if st.button("🗑️ مسح جميع البيانات"):
        if st.checkbox("تأكيد حذف جميع البيانات"):
            empty_df = pd.DataFrame(columns=machines_df.columns)
            save_data(empty_df)
            st.session_state.machines_df = empty_df
            st.warning("✅ تم مسح جميع البيانات!")
            st.rerun()

# علامات التبويب الرئيسية
tab1, tab2, tab3 = st.tabs(["📊 لوحة التحكم", "📋 قائمة الماكينات", "🔄 تسجيل صيانة"])

with tab1:
    st.header("لوحة التحكم الرئيسية")
    
    if machines_df.empty:
        st.info("📝 لا توجد ماكينات مضافة حتى الآن. استخدم الشريط الجانبي لإضافة ماكينة جديدة.")
    else:
        # إحصائيات سريعة
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("إجمالي الماكينات", len(machines_df))
        
        with col2:
            need_maintenance = len(machines_df[machines_df['overall_status'].str.contains('⚠️')]) if 'overall_status' in machines_df.columns else 0
            st.metric("تحتاج صيانة", need_maintenance)
        
        with col3:
            total_hours = machines_df['total_hours'].sum() if 'total_hours' in machines_df.columns else 0
            st.metric("إجمالي الساعات", f"{total_hours:,.0f}")
        
        with col4:
            avg_hours = machines_df['total_hours'].mean() if 'total_hours' in machines_df.columns else 0
            st.metric("متوسط الساعات", f"{avg_hours:,.0f}")
        
        st.markdown("---")
        
        # الماكينات التي تحتاج صيانة عاجلة
        st.subheader("🚨 الماكينات التي تحتاج صيانة عاجلة")
        
        if 'overall_status' in machines_df.columns:
            urgent_machines = machines_df[machines_df['overall_status'].str.contains('⚠️')]
            
            if not urgent_machines.empty:
                urgent_cols = ['machine_name', 'machine_type', 'total_hours', 
                              'greasing_countdown', 'oil_change_countdown', 
                              'other_maintenance_countdown', 'overall_status']
                
                display_cols = [col for col in urgent_cols if col in urgent_machines.columns]
                
                st.dataframe(
                    urgent_machines[display_cols].rename(columns={
                        'machine_name': 'اسم الماكينة',
                        'machine_type': 'النوع',
                        'total_hours': 'ساعات التشغيل',
                        'greasing_countdown': 'متبقي للتشحيم',
                        'oil_change_countdown': 'متبقي لتغيير الزيت',
                        'other_maintenance_countdown': 'متبقي للصيانة الأخرى',
                        'overall_status': 'الحالة'
                    }),
                    use_container_width=True
                )
            else:
                st.success("🎉 لا توجد ماكينات تحتاج صيانة عاجلة حالياً.")
        
        st.markdown("---")
        
        # نظرة عامة على جميع الماكينات
        st.subheader("📋 نظرة عامة على الماكينات")
        
        if 'overall_status' in machines_df.columns:
            status_counts = machines_df['overall_status'].value_counts()
            
            # عرض الإحصائيات في أعمدة
            cols = st.columns(len(status_counts))
            for idx, (status, count) in enumerate(status_counts.items()):
                with cols[idx]:
                    st.metric(status, count)
            
            # عرض تفاصيل الحالة
            for status in ['⚠️ يحتاج صيانة', '🟡 قريب', '🟢 جيد']:
                if status in status_counts:
                    with st.expander(f"{status} ({status_counts[status]})"):
                        status_machines = machines_df[machines_df['overall_status'] == status]
                        if not status_machines.empty:
                            st.dataframe(
                                status_machines[['machine_name', 'machine_type', 'total_hours']].rename(columns={
                                    'machine_name': 'اسم الماكينة',
                                    'machine_type': 'النوع',
                                    'total_hours': 'ساعات التشغيل'
                                }),
                                use_container_width=True
                            )

with tab2:
    st.header("قائمة جميع الماكينات")
    
    if machines_df.empty:
        st.info("📝 لا توجد ماكينات مضافة حتى الآن.")
    else:
        # خيارات البحث والتصفية
        col1, col2 = st.columns(2)
        
        with col1:
            search_term = st.text_input("🔍 بحث عن ماكينة", "", key="search_tab2")
        
        with col2:
            filter_type = st.selectbox("تصفية حسب النوع", ["الكل"] + list(machines_df['machine_type'].unique()), key="filter_type")
        
        # تصفية البيانات
        display_df = machines_df.copy()
        
        if search_term:
            mask = display_df.apply(lambda row: row.astype(str).str.contains(search_term, case=False).any(), axis=1)
            display_df = display_df[mask]
        
        if filter_type != "الكل":
            display_df = display_df[display_df['machine_type'] == filter_type]
        
        # خيارات العرض
        show_details = st.checkbox("عرض التفاصيل الكاملة", value=False)
        
        if show_details:
            display_columns = [
                'machine_id', 'machine_name', 'machine_type', 'installation_date',
                'total_hours', 'last_maintenance_date', 'last_maintenance_hours',
                'oil_change_interval', 'greasing_interval', 'other_maintenance_interval',
                'next_oil_change_hours', 'next_greasing_hours', 'next_other_maintenance_hours',
                'greasing_countdown', 'oil_change_countdown', 'other_maintenance_countdown',
                'greasing_status', 'oil_change_status', 'other_maintenance_status', 'overall_status'
            ]
            
            column_names = {
                'machine_id': 'رقم الماكينة',
                'machine_name': 'اسم الماكينة',
                'machine_type': 'النوع',
                'installation_date': 'تاريخ التركيب',
                'total_hours': 'ساعات التشغيل',
                'last_maintenance_date': 'تاريخ آخر صيانة',
                'last_maintenance_hours': 'ساعات آخر صيانة',
                'oil_change_interval': 'فترة تغيير الزيت',
                'greasing_interval': 'فترة التشحيم',
                'other_maintenance_interval': 'فترة الصيانة الأخرى',
                'next_oil_change_hours': 'الهدف تغيير الزيت',
                'next_greasing_hours': 'الهدف التشحيم',
                'next_other_maintenance_hours': 'الهدف صيانة أخرى',
                'greasing_countdown': 'متبقي للتشحيم',
                'oil_change_countdown': 'متبقي لتغيير الزيت',
                'other_maintenance_countdown': 'متبقي للصيانة الأخرى',
                'greasing_status': 'حالة التشحيم',
                'oil_change_status': 'حالة تغيير الزيت',
                'other_maintenance_status': 'حالة الصيانة الأخرى',
                'overall_status': 'الحالة العامة'
            }
        else:
            display_columns = [
                'machine_id', 'machine_name', 'machine_type', 'total_hours',
                'last_maintenance_date', 'greasing_status',
                'oil_change_status', 'other_maintenance_status', 'overall_status'
            ]
            
            column_names = {
                'machine_id': 'رقم الماكينة',
                'machine_name': 'اسم الماكينة',
                'machine_type': 'النوع',
                'total_hours': 'ساعات التشغيل',
                'last_maintenance_date': 'تاريخ آخر صيانة',
                'greasing_status': 'حالة التشحيم',
                'oil_change_status': 'حالة تغيير الزيت',
                'other_maintenance_status': 'حالة الصيانة الأخرى',
                'overall_status': 'الحالة العامة'
            }
        
        # عرض البيانات
        st.dataframe(
            display_df[[col for col in display_columns if col in display_df.columns]].rename(columns=column_names),
            use_container_width=True,
            height=400
        )
        
        # إحصائيات سريعة
        st.markdown("---")
        st.subheader("📊 إحصائيات سريعة")
        
        if not display_df.empty:
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric("عدد الماكينات المعروضة", len(display_df))
            
            with col2:
                avg_hours = display_df['total_hours'].mean()
                st.metric("متوسط ساعات التشغيل", f"{avg_hours:,.0f}")
            
            with col3:
                total_hours = display_df['total_hours'].sum()
                st.metric("إجمالي ساعات التشغيل", f"{total_hours:,.0f}")
        
        # خيارات التصدير
        st.markdown("---")
        st.subheader("📤 خيارات التصدير")
        
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("💾 حفظ التعديلات"):
                save_data(machines_df)
                st.success("✅ تم حفظ التعديلات بنجاح!")
        
        with col2:
            # تصدير إلى Excel
            buffer = BytesIO()
            with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                machines_df.to_excel(writer, index=False, sheet_name='Machines')
            
            st.download_button(
                label="📥 تحميل ملف Excel",
                data=buffer.getvalue(),
                file_name=f"machines_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

with tab3:
    st.header("تسجيل عملية صيانة جديدة")
    
    if machines_df.empty:
        st.info("📝 لا توجد ماكينات مضافة حتى الآن.")
    else:
        with st.form("maintenance_form"):
            # اختيار الماكينة
            machine_options = machines_df['machine_name'].tolist()
            selected_machine = st.selectbox("اختر الماكينة", machine_options, key="selected_machine")
            
            if selected_machine:
                # عرض معلومات الماكينة المختارة
                machine_info = machines_df[machines_df['machine_name'] == selected_machine].iloc[0]
                
                col1, col2 = st.columns(2)
                with col1:
                    st.info(f"**اسم الماكينة:** {machine_info['machine_name']}")
                    st.info(f"**النوع:** {machine_info['machine_type']}")
                    st.info(f"**ساعات التشغيل الحالية:** {machine_info['total_hours']:,.0f}")
                
                with col2:
                    if 'greasing_countdown' in machine_info:
                        st.info(f"**متبقي للتشحيم:** {machine_info['greasing_countdown']:,.0f} ساعة")
                    if 'oil_change_countdown' in machine_info:
                        st.info(f"**متبقي لتغيير الزيت:** {machine_info['oil_change_countdown']:,.0f} ساعة")
            
            # نوع الصيانة
            maintenance_type = st.selectbox(
                "نوع الصيانة",
                ["تغيير زيت", "تشحيم", "صيانة دورية", "إصلاح عطل", "فحص روتيني", "أخرى"],
                key="maintenance_type"
            )
            
            col1, col2 = st.columns(2)
            with col1:
                maintenance_date = st.date_input("تاريخ الصيانة", datetime.now(), key="maintenance_date")
                current_hours = st.number_input(
                    "ساعات التشغيل الحالية",
                    min_value=0.0,
                    value=float(machine_info['total_hours']) if not machines_df.empty else 0.0,
                    step=10.0,
                    key="current_hours"
                )
            
            with col2:
                technician = st.text_input("اسم الفني", key="technician")
                cost = st.number_input("تكلفة الصيانة (ريال)", min_value=0.0, value=0.0, step=100.0, key="cost")
            
            description = st.text_area("وصف الصيانة/الملاحظات", key="description", height=100)
            
            col1, col2 = st.columns(2)
            with col1:
                submit_maintenance = st.form_submit_button("✅ تسجيل الصيانة")
            
            with col2:
                cancel_maintenance = st.form_submit_button("❌ إلغاء")
            
            if submit_maintenance and selected_machine:
                # تحديث بيانات الماكينة
                machine_idx = machines_df[machines_df['machine_name'] == selected_machine].index[0]
                
                # تحديث ساعات التشغيل
                machines_df.at[machine_idx, 'total_hours'] = current_hours
                
                # تحديث تاريخ آخر صيانة
                machines_df.at[machine_idx, 'last_maintenance_date'] = maintenance_date
                machines_df.at[machine_idx, 'last_maintenance_hours'] = current_hours
                
                # إعادة حساب مواعيد الصيانة القادمة بناءً على نوع الصيانة
                if maintenance_type == "تغيير زيت":
                    next_oil_hours = current_hours + machines_df.at[machine_idx, 'oil_change_interval']
                    machines_df.at[machine_idx, 'next_oil_change_hours'] = next_oil_hours
                    st.success(f"✅ تم تحديث موعد تغيير الزيت القادم إلى {next_oil_hours:,.0f} ساعة")
                
                elif maintenance_type == "تشحيم":
                    next_greasing_hours = current_hours + machines_df.at[machine_idx, 'greasing_interval']
                    machines_df.at[machine_idx, 'next_greasing_hours'] = next_greasing_hours
                    st.success(f"✅ تم تحديث موعد التشحيم القادم إلى {next_greasing_hours:,.0f} ساعة")
                
                elif maintenance_type == "صيانة دورية":
                    next_other_hours = current_hours + machines_df.at[machine_idx, 'other_maintenance_interval']
                    machines_df.at[machine_idx, 'next_other_maintenance_hours'] = next_other_hours
                    st.success(f"✅ تم تحديث موعد الصيانة الدورية القادم إلى {next_other_hours:,.0f} ساعة")
                
                # إعادة حساب العدادات
                machines_df = calculate_countdowns(machines_df)
                
                # حفظ التغييرات
                save_data(machines_df)
                st.session_state.changes_made = True
                st.session_state.machines_df = machines_df
                
                # عرض ملخص الصيانة
                st.markdown("---")
                st.subheader("📋 ملخص الصيانة المسجلة")
                
                summary_cols = st.columns(2)
                with summary_cols[0]:
                    st.info(f"**الماكينة:** {selected_machine}")
                    st.info(f"**نوع الصيانة:** {maintenance_type}")
                    st.info(f"**التاريخ:** {maintenance_date}")
                    st.info(f"**الفني:** {technician if technician else 'غير محدد'}")
                
                with summary_cols[1]:
                    st.info(f"**ساعات التشغيل:** {current_hours:,.0f}")
                    st.info(f"**التكلفة:** {cost:,.0f} ريال")
                    if description:
                        st.info(f"**الملاحظات:** {description}")
                
                st.success(f"✅ تم تسجيل صيانة '{maintenance_type}' للماكينة '{selected_machine}' بنجاح!")
                st.rerun()

# تذييل الصفحة
st.markdown("---")
st.markdown("""
<div style="text-align: center; color: gray;">
    <p>نظام تتبع صيانة الماكينات | إصدار مبسط</p>
    <p>لتشغيل النظام: <code>streamlit run app.py</code></p>
    <p>المتطلبات الأساسية: streamlit, pandas, openpyxl</p>
</div>
""", unsafe_allow_html=True)
