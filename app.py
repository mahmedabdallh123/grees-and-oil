import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import os
from io import BytesIO
import matplotlib.pyplot as plt

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

# دالة للتحميل من GitHub
def load_from_github():
    try:
        github_token = st.secrets.get("GITHUB_TOKEN", "")
        
        if not github_token:
            st.warning("لم يتم تكوين GitHub Token. يرجى إضافته في إعدادات Streamlit Secrets.")
            return None
        
        from github import Github, Auth
        
        auth = Auth.Token(github_token)
        g = Github(auth=auth)
        
        repo_name = st.secrets.get("GITHUB_REPO", "your-username/your-repo-name")
        repo = g.get_repo(repo_name)
        
        file_content = repo.get_contents("machines_data.xlsx")
        
        with open('machines_data.xlsx', 'wb') as f:
            f.write(file_content.decoded_content)
        
        st.success("✅ تم تحميل البيانات من GitHub بنجاح!")
        return load_data()
    except ImportError:
        st.error("مكتبة PyGithub غير مثبتة. يرجى تثبيتها باستخدام: pip install pygithub")
        return None
    except Exception as e:
        st.error(f"خطأ في تحميل البيانات من GitHub: {str(e)}")
        return None

# دالة للرفع إلى GitHub
def push_to_github():
    try:
        github_token = st.secrets.get("GITHUB_TOKEN", "")
        
        if not github_token:
            st.warning("لم يتم تكوين GitHub Token. يرجى إضافته في إعدادات Streamlit Secrets.")
            return False
        
        from github import Github, Auth
        
        auth = Auth.Token(github_token)
        g = Github(auth=auth)
        
        repo_name = st.secrets.get("GITHUB_REPO", "your-username/your-repo-name")
        repo = g.get_repo(repo_name)
        
        with open('machines_data.xlsx', 'rb') as f:
            content = f.read()
        
        try:
            file = repo.get_contents("machines_data.xlsx")
            repo.update_file(
                path="machines_data.xlsx",
                message="تحديث بيانات الماكينات - " + datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                content=content,
                sha=file.sha
            )
        except:
            repo.create_file(
                path="machines_data.xlsx",
                message="إنشاء ملف بيانات الماكينات - " + datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                content=content
            )
        
        st.success("✅ تم رفع البيانات إلى GitHub بنجاح!")
        return True
    except ImportError:
        st.error("مكتبة PyGithub غير مثبتة. يرجى تثبيتها باستخدام: pip install pygithub")
        return False
    except Exception as e:
        st.error(f"خطأ في رفع البيانات إلى GitHub: {str(e)}")
        return False

# تحميل البيانات
machines_df = load_data()
if not machines_df.empty:
    machines_df = calculate_countdowns(machines_df)

# الشريط الجانبي
with st.sidebar:
    st.header("🛠️ التحكم في النظام")
    
    # قسم التحميل والرفع
    st.subheader("التكامل مع GitHub")
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("📥 تحميل من GitHub"):
            with st.spinner("جاري تحميل البيانات..."):
                new_df = load_from_github()
                if new_df is not None:
                    machines_df = new_df
                    st.session_state.machines_df = machines_df
                    st.rerun()
    
    with col2:
        if st.button("📤 رفع إلى GitHub"):
            with st.spinner("جاري رفع البيانات..."):
                if save_data(machines_df):
                    push_to_github()
    
    st.markdown("---")
    
    # قسم إضافة ماكينة جديدة
    st.subheader("إضافة ماكينة جديدة")
    
    with st.form("add_machine_form"):
        machine_name = st.text_input("اسم الماكينة")
        machine_type = st.selectbox("نوع الماكينة", ["معدات ثقيلة", "معدات خفيفة", "مولدات", "أخرى"])
        
        col1, col2 = st.columns(2)
        with col1:
            installation_date = st.date_input("تاريخ التركيب", datetime.now())
            total_hours = st.number_input("إجمالي ساعات التشغيل", min_value=0.0, value=0.0, step=10.0)
        
        with col2:
            last_maintenance_date = st.date_input("تاريخ آخر صيانة", datetime.now())
            last_maintenance_hours = st.number_input("ساعات التشغيل عند آخر صيانة", 
                                                    min_value=0.0, value=0.0, step=10.0)
        
        st.subheader("فترات الصيانة (بالساعات)")
        oil_interval = st.number_input("فترة تغيير الزيت", min_value=1, value=1000, step=50)
        greasing_interval = st.number_input("فترة التشحيم", min_value=1, value=500, step=50)
        other_interval = st.number_input("فترة الصيانة الأخرى", min_value=1, value=2000, step=100)
        
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
            st.success(f"تمت إضافة الماكينة '{machine_name}' بنجاح!")
            st.rerun()

# علامات التبويب الرئيسية
tab1, tab2, tab3, tab4 = st.tabs(["📊 لوحة التحكم", "📋 قائمة الماكينات", "🔄 تسجيل صيانة", "📈 التقارير"])

with tab1:
    st.header("لوحة التحكم الرئيسية")
    
    if machines_df.empty:
        st.info("لا توجد ماكينات مضافة حتى الآن. استخدم الشريط الجانبي لإضافة ماكينة جديدة.")
    else:
        # إحصائيات سريعة
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("إجمالي الماكينات", len(machines_df))
        
        with col2:
            need_maintenance = len(machines_df[machines_df['overall_status'].str.contains('⚠️')]) if 'overall_status' in machines_df.columns else 0
            st.metric("الماكينات التي تحتاج صيانة", need_maintenance, delta_color="inverse")
        
        with col3:
            total_hours = machines_df['total_hours'].sum() if 'total_hours' in machines_df.columns else 0
            st.metric("إجمالي ساعات التشغيل", f"{total_hours:,.0f}")
        
        with col4:
            avg_hours = machines_df['total_hours'].mean() if 'total_hours' in machines_df.columns else 0
            st.metric("متوسط ساعات التشغيل", f"{avg_hours:,.0f}")
        
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

with tab2:
    st.header("قائمة جميع الماكينات")
    
    if machines_df.empty:
        st.info("لا توجد ماكينات مضافة حتى الآن.")
    else:
        # عرض جميع الماكينات مع إمكانية التصفية
        search_term = st.text_input("🔍 بحث عن ماكينة", "")
        
        # تصفية البيانات إذا كان هناك بحث
        display_df = machines_df.copy()
        if search_term:
            mask = display_df.apply(lambda row: row.astype(str).str.contains(search_term, case=False).any(), axis=1)
            display_df = display_df[mask]
        
        # تحديد الأعمدة للعرض
        display_columns = [
            'machine_id', 'machine_name', 'machine_type', 'installation_date',
            'total_hours', 'last_maintenance_date', 'greasing_status',
            'oil_change_status', 'other_maintenance_status', 'overall_status'
        ]
        
        # عرض البيانات
        st.dataframe(
            display_df[[col for col in display_columns if col in display_df.columns]].rename(columns={
                'machine_id': 'رقم الماكينة',
                'machine_name': 'اسم الماكينة',
                'machine_type': 'النوع',
                'installation_date': 'تاريخ التركيب',
                'total_hours': 'ساعات التشغيل',
                'last_maintenance_date': 'تاريخ آخر صيانة',
                'greasing_status': 'حالة التشحيم',
                'oil_change_status': 'حالة تغيير الزيت',
                'other_maintenance_status': 'حالة الصيانة الأخرى',
                'overall_status': 'الحالة العامة'
            }),
            use_container_width=True,
            height=400
        )
        
        # خيارات التصدير
        st.markdown("---")
        col1, col2 = st.columns(2)
        
        with col1:
            # تصدير إلى Excel
            if st.button("📥 تصدير إلى Excel"):
                buffer = BytesIO()
                with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                    machines_df.to_excel(writer, index=False, sheet_name='Machines')
                
                st.download_button(
                    label="تحميل ملف Excel",
                    data=buffer.getvalue(),
                    file_name=f"machines_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )

with tab3:
    st.header("تسجيل عملية صيانة جديدة")
    
    if machines_df.empty:
        st.info("لا توجد ماكينات مضافة حتى الآن.")
    else:
        with st.form("maintenance_form"):
            # اختيار الماكينة
            machine_options = machines_df['machine_name'].tolist()
            selected_machine = st.selectbox("اختر الماكينة", machine_options)
            
            # نوع الصيانة
            maintenance_type = st.selectbox(
                "نوع الصيانة",
                ["تغيير زيت", "تشحيم", "صيانة دورية", "إصلاح عطل", "أخرى"]
            )
            
            col1, col2 = st.columns(2)
            with col1:
                maintenance_date = st.date_input("تاريخ الصيانة", datetime.now())
                current_hours = st.number_input(
                    "ساعات التشغيل الحالية",
                    min_value=0.0,
                    value=float(machines_df.loc[machines_df['machine_name'] == selected_machine, 'total_hours'].iloc[0]) if not machines_df.empty else 0.0,
                    step=10.0
                )
            
            with col2:
                technician = st.text_input("اسم الفني")
                cost = st.number_input("تكلفة الصيانة", min_value=0.0, value=0.0, step=100.0)
            
            description = st.text_area("وصف الصيانة/الملاحظات")
            
            submit_maintenance = st.form_submit_button("تسجيل الصيانة")
            
            if submit_maintenance:
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
                
                elif maintenance_type == "تشحيم":
                    next_greasing_hours = current_hours + machines_df.at[machine_idx, 'greasing_interval']
                    machines_df.at[machine_idx, 'next_greasing_hours'] = next_greasing_hours
                
                elif maintenance_type == "صيانة دورية":
                    next_other_hours = current_hours + machines_df.at[machine_idx, 'other_maintenance_interval']
                    machines_df.at[machine_idx, 'next_other_maintenance_hours'] = next_other_hours
                
                # حفظ التغييرات
                save_data(machines_df)
                st.session_state.changes_made = True
                st.success(f"تم تسجيل صيانة '{maintenance_type}' للماكينة '{selected_machine}' بنجاح!")
                st.rerun()

with tab4:
    st.header("التقارير والإحصائيات")
    
    if machines_df.empty:
        st.info("لا توجد بيانات لعرض التقارير.")
    else:
        # تقرير الصيانة القادمة
        st.subheader("📅 مواعيد الصيانة القادمة")
        
        # إنشاء تقرير بالماكينات الأقرب لموعد الصيانة
        upcoming_df = machines_df.copy()
        
        if 'greasing_countdown' in upcoming_df.columns:
            # ترتيب حسب الأقرب موعداً للصيانة
            upcoming_df = upcoming_df.sort_values('greasing_countdown')
            
            # عرض أول 10 ماكينات
            st.dataframe(
                upcoming_df[['machine_name', 'machine_type', 'total_hours', 
                           'greasing_countdown', 'oil_change_countdown', 
                           'other_maintenance_countdown']].head(10).rename(columns={
                    'machine_name': 'اسم الماكينة',
                    'machine_type': 'النوع',
                    'total_hours': 'ساعات التشغيل',
                    'greasing_countdown': 'متبقي للتشحيم',
                    'oil_change_countdown': 'متبقي لتغيير الزيت',
                    'other_maintenance_countdown': 'متبقي للصيانة الأخرى'
                }),
                use_container_width=True
            )
        
        # إحصائيات حسب نوع الماكينة
        st.markdown("---")
        st.subheader("📊 إحصائيات حسب نوع الماكينة")
        
        if 'machine_type' in machines_df.columns:
            type_stats = machines_df.groupby('machine_type').agg({
                'machine_name': 'count',
                'total_hours': 'mean',
                'total_hours': 'sum'
            }).rename(columns={'machine_name': 'عدد الماكينات', 'total_hours': 'إجمالي ساعات التشغيل'})
            
            st.dataframe(type_stats, use_container_width=True)

# قسم التحميل اليدوي لملف Excel
st.sidebar.markdown("---")
st.sidebar.subheader("تحميل ملف Excel يدوياً")

uploaded_file = st.sidebar.file_uploader("اختر ملف Excel", type=['xlsx', 'xls'])

if uploaded_file is not None:
    try:
        new_df = pd.read_excel(uploaded_file, engine='openpyxl')
        if not new_df.empty:
            save_data(new_df)
            st.sidebar.success("تم تحميل الملف بنجاح!")
            st.session_state.machines_df = new_df
            st.rerun()
    except Exception as e:
        st.sidebar.error(f"خطأ في تحميل الملف: {str(e)}")

# معلومات حول التعديلات غير المحفوظة
if st.session_state.get('changes_made', False):
    st.sidebar.warning("⚠️ لديك تغييرات غير محفوظة على GitHub")
    
    if st.sidebar.button("حفظ التغييرات محلياً"):
        save_data(machines_df)
        st.session_state.changes_made = False
        st.sidebar.success("تم الحفظ محلياً!")
        st.rerun()

# تذييل الصفحة
st.markdown("---")
st.markdown("""
<div style="text-align: center; color: gray;">
    <p>نظام تتبع صيانة الماكينات | تم التطوير باستخدام Streamlit</p>
    <p>لتشغيل النظام: <code>streamlit run app.py</code></p>
</div>
""", unsafe_allow_html=True)
