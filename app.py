"""
LINE聊天機器人與Google Drive PDF處理系統
此代碼實現了一個LINE聊天機器人，可讀取Google Drive上的PDF文件，
使用Gemini API進行查詢處理，並將結果傳回LINE用戶。
"""

import os
from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from google import genai
from google.genai import types
from dotenv import load_dotenv
load_dotenv()


import io
import logging

# 配置日誌
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# 環境變數配置
LINE_CHANNEL_ACCESS_TOKEN = os.environ.get('LINE_CHANNEL_ACCESS_TOKEN')
LINE_CHANNEL_SECRET = os.environ.get('LINE_CHANNEL_SECRET')
GOOGLE_CREDENTIALS_PATH = os.environ.get('GOOGLE_CREDENTIALS_PATH')
GOOGLE_DRIVE_PDF_ID = os.environ.get('GOOGLE_DRIVE_PDF_ID')  # "RAG測試.pdf"的Drive ID
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')

# 初始化LINE API
line_bot_api = LineBotApi(LINE_CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(LINE_CHANNEL_SECRET)

# 初始化Google API客戶端
def initialize_google_drive_client():
    """初始化Google Drive客戶端"""
    creds = service_account.Credentials.from_service_account_file(
        GOOGLE_CREDENTIALS_PATH, 
        scopes=['https://www.googleapis.com/auth/drive.readonly']
    )
    return build('drive', 'v3', credentials=creds)

# 初始化Gemini API客戶端
def initialize_gemini_client():
    """初始化Gemini API客戶端"""
    # 設置 API 金鑰 (新版方法)
    client = genai.GenerativeModel(model_name="gemini-2.5-pro-preview-0325", api_key=GEMINI_API_KEY)
    return client

# 從Google Drive獲取PDF內容
def get_pdf_from_drive(file_id):
    """
    從Google Drive獲取PDF文件內容
    
    Args:
        file_id: Google Drive上PDF的文件ID
        
    Returns:
        bytes: PDF文件的二進制內容
    """
    try:
        drive_service = initialize_google_drive_client()
        request = drive_service.files().get_media(fileId=file_id)
        
        file_content = io.BytesIO()
        downloader = MediaIoBaseDownload(file_content, request)
        
        done = False
        while not done:
            status, done = downloader.next_chunk()
            logger.info(f"下載進度: {int(status.progress() * 100)}%")
            
        return file_content.getvalue()
    except Exception as e:
        logger.error(f"從Google Drive獲取PDF時出錯: {e}")
        raise

# 使用Gemini API處理查詢
def process_with_gemini(pdf_data, user_query):
    """
    使用Gemini API處理PDF內容和用戶查詢
    
    Args:
        pdf_data: PDF文件的二進制內容
        user_query: 用戶的查詢文本
        
    Returns:
        str: Gemini的回應文本
    """
    try:
        # 新的初始化方式
        client = genai.Client(api_key=GEMINI_API_KEY)
        
        # 使用模型生成內容
        response = client.models.generate_content(
            model="gemini-2.0-flash",  # 使用Gemini 2.5 Pro Preview 03-25
            contents=[
                types.Part.from_bytes(
                    data=pdf_data,
                    mime_type='application/pdf',
                ),
                user_query
            ]
        )
        
        return response.text
    except Exception as e:
        logger.error(f"處理Gemini API查詢時出錯: {e}")
        return f"處理您的查詢時發生錯誤: {str(e)}"

@app.route("/callback", methods=['POST'])
def callback():
    """LINE Webhook回調處理器"""
    signature = request.headers['X-Line-Signature']
    body = request.get_data(as_text=True)
    
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
        
    return 'OK'

@handler.add(MessageEvent, message=TextMessage)
def handle_text_message(event):
    """處理文本消息事件"""
    user_id = event.source.user_id
    user_query = event.message.text
    
    try:
        # 1. 獲取Google Drive上的PDF文件
        pdf_data = get_pdf_from_drive(GOOGLE_DRIVE_PDF_ID)
        
        # 2. 發送處理中的消息
        line_bot_api.push_message(
            user_id, 
            TextSendMessage(text="正在處理您的查詢，請稍候...")
        )
        
        # 3. 使用Gemini API處理查詢
        gemini_response = process_with_gemini(pdf_data, user_query)
        
        # 4. 將回應發送回LINE
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=gemini_response)
        )
        
    except Exception as e:
        logger.error(f"處理消息時出錯: {e}")
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=f"處理您的請求時發生錯誤: {str(e)}")
        )

if __name__ == "__main__":
    # 本地測試時使用
    app.run(host='0.0.0.0', port=8080, debug=True)