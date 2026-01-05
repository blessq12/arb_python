import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # DB configurations
    DB_CONNECTION = os.getenv('DB_CONNECTION', 'mysql')
    DB_HOST = os.getenv('DB_HOST', '127.0.0.1')
    DB_PORT = int(os.getenv('DB_PORT', 3306))
    DB_DATABASE = os.getenv('DB_DATABASE', 'pairs')
    DB_USERNAME = os.getenv('DB_USERNAME', 'root')
    DB_PASSWORD = os.getenv('DB_PASSWORD', '')
    
    # Telegram configurations
    TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', '7348995171:AAEZ4eWSVwQIVpvsMohziriWzycxqCdj6bU')
    TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID', '-4872143459')
    
