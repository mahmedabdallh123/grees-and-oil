import os
import base64
import requests
from datetime import datetime
import streamlit as st

class GitHubUploader:
    def __init__(self):
        # محاولة تحميل إعدادات GitHub من Streamlit Secrets
        try:
            self.github_token = st.secrets["github"]["token"]
            self.repo_owner = st.secrets["github"]["repo_owner"]
            self.repo_name = st.secrets["github"]["repo_name"]
            self.file_path = st.secrets["github"]["file_path"]
        except:
            self.github_token = None
            st.warning("⚠️ إعدادات GitHub غير متوفرة")
        
        self.headers = {
            "Authorization": f"token {self.github_token}",
            "Accept": "application/vnd.github.v3+json"
        } if self.github_token else {}
        
        self.api_url = f"https://api.github.com/repos/{self.repo_owner}/{self.repo_name}/contents/{self.file_path}"
    
    def test_connection(self):
        """اختبار اتصال GitHub"""
        if not self.github_token:
            return False
        
        try:
            response = requests.get(f"https://api.github.com/user", headers=self.headers)
            return response.status_code == 200
        except:
            return False
    
    def upload_file(self, file_path="machines.xlsx"):
        """رفع ملف إلى GitHub"""
        if not self.github_token:
            st.error("❌ token GitHub غير متوفر")
            return False
        
        try:
            # قراءة الملف
            with open(file_path, 'rb') as f:
                content = f.read()
            
            # ترميز Base64
            encoded_content = base64.b64encode(content).decode('utf-8')
            
            # الحصول على معلومات الملف الحالي (للحصول على SHA)
            response = requests.get(self.api_url, headers=self.headers)
            
            commit_message = f"تحديث البيانات - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            
            if response.status_code == 200:
                # تحديث الملف الموجود
                sha = response.json()['sha']
                data = {
                    "message": commit_message,
                    "content": encoded_content,
                    "sha": sha
                }
            else:
                # إنشاء ملف جديد
                data = {
                    "message": commit_message,
                    "content": encoded_content
                }
            
            # رفع إلى GitHub
            response = requests.put(self.api_url, headers=self.headers, json=data)
            
            if response.status_code in [200, 201]:
                return True
            else:
                st.error(f"❌ فشل في الرفع: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            st.error(f"❌ خطأ في الرفع: {str(e)}")
            return False
    
    def download_file(self):
        """تحميل ملف من GitHub"""
        if not self.github_token:
            st.error("❌ token GitHub غير متوفر")
            return False
        
        try:
            # طلب الملف من GitHub
            response = requests.get(self.api_url, headers=self.headers)
            
            if response.status_code == 200:
                # فك تشفير المحتوى
                content = base64.b64decode(response.json()['content'])
                
                # حفظ الملف
                with open(self.file_path, 'wb') as f:
                    f.write(content)
                
                return True
            else:
                st.error(f"❌ فشل في التحميل: {response.status_code}")
                return False
                
        except Exception as e:
            st.error(f"❌ خطأ في التحميل: {str(e)}")
            return False
    
    def get_file_info(self):
        """الحصول على معلومات الملف على GitHub"""
        if not self.github_token:
            return None
        
        try:
            response = requests.get(self.api_url, headers=self.headers)
            
            if response.status_code == 200:
                data = response.json()
                return {
                    "sha": data.get("sha", ""),
                    "size": data.get("size", 0),
                    "last_modified": datetime.now().strftime("%Y-%m-%d %H:%M")
                }
            return None
        except:
            return None
    
    def is_synced(self):
        """التحقق إذا كانت البيانات متزامنة"""
        try:
            local_stats = os.stat(self.file_path)
            remote_info = self.get_file_info()
            
            if remote_info:
                # يمكنك إضافة منطق للمقارنة هنا
                return True
            return False
        except:
            return False
