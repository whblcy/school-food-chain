"""API配置"""
import os


class Settings:
    API_BASE_URL = os.environ.get('API_BASE_URL', 'http://localhost:8000/api/v1')
    APP_NAME = '学校食材供应链管理平台'
    APP_VERSION = '2.0.0'


settings = Settings()
