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
GOOGLE_DRIVE_PDF1_ID = os.environ.get('GOOGLE_DRIVE_PDF1_ID')
GOOGLE_DRIVE_PDF2_ID = os.environ.get('GOOGLE_DRIVE_PDF2_ID')
GOOGLE_DRIVE_PDF3_ID = os.environ.get('GOOGLE_DRIVE_PDF3_ID')
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
    # 設置 API 金鑰
    client = genai.Client(api_key=GEMINI_API_KEY)
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

        # 重要: 將文件指針重置到開始位置，這樣Gemini API才能正確讀取內容
        file_content.seek(0)

        return file_content
    except Exception as e:
        logger.error(f"從Google Drive獲取PDF時出錯: {e}")
        raise

# 使用Gemini API處理查詢
def process_with_gemini(pdf_data1, pdf_data2, pdf_data3, user_query):
    """
    使用Gemini API處理PDF內容和用戶查詢
    
    Args:
        pdf_data1-3: PDF文件的BytesIO對象
        user_query: 用戶的查詢文本
        
    Returns:
        str: Gemini的回應文本
    """
    try:
        # 確保文件指針在開始位置
        pdf_data1.seek(0)
        pdf_data2.seek(0)
        pdf_data3.seek(0)
        
        # 初始化Gemini客戶端
        client = initialize_gemini_client()
        
        # 上傳PDF文件
        logger.info("開始上傳PDF文件1到Gemini API")
        pdf_file1 = client.files.upload(
            file=pdf_data1,
            config=dict(mime_type='application/pdf')
        )
        logger.info("PDF文件1上傳成功")
        
        logger.info("開始上傳PDF文件2到Gemini API")
        pdf_file2 = client.files.upload(
            file=pdf_data2,
            config=dict(mime_type='application/pdf')
        )
        logger.info("PDF文件2上傳成功")
        
        logger.info("開始上傳PDF文件3到Gemini API")
        pdf_file3 = client.files.upload(
            file=pdf_data3,
            config=dict(mime_type='application/pdf')
        )
        logger.info("PDF文件3上傳成功")
        
        # 增加超時處理
        import httpx
        
        logger.info("開始生成Gemini API響應")
        try:
            # 直接使用generate_content，不嘗試獲取模型實例
            response = client.models.generate_content(
                model="gemini-2.0-flash",
                contents=[pdf_file1, pdf_file2, pdf_file3, user_query]
            )
            logger.info("Gemini API響應生成成功")
            return response.text
        except httpx.TimeoutException:
            logger.error("Gemini API請求超時")
            return "處理您的查詢時發生超時，請嘗試簡化您的問題或稍後再試。"
        except Exception as e:
            logger.error(f"生成Gemini API響應時出錯: {e}")
            raise
            
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
        # 發送處理中的消息
        line_bot_api.push_message(
            user_id, 
            TextSendMessage(text="正在處理您的查詢，請稍候...")
        )
        
        # 1. 獲取Google Drive上的PDF文件
        logger.info("開始從Google Drive獲取PDF文件")
        pdf_data1 = get_pdf_from_drive(GOOGLE_DRIVE_PDF1_ID)
        pdf_data2 = get_pdf_from_drive(GOOGLE_DRIVE_PDF2_ID)
        pdf_data3 = get_pdf_from_drive(GOOGLE_DRIVE_PDF3_ID)
        logger.info("所有PDF文件獲取完成")
        
        # 添加簡單的PDF檢查
        if pdf_data1.getbuffer().nbytes == 0 or pdf_data2.getbuffer().nbytes == 0 or pdf_data3.getbuffer().nbytes == 0:
            logger.error("有PDF文件為空")
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text="無法處理您的請求：有PDF文件為空。")
            )
            return
            
       
        gemini_response = process_with_gemini(pdf_data1, pdf_data2, pdf_data3, user_query)
        logger.info(gemini_response)
        
        # 3. 將回應發送回LINE
        # 檢查回應長度，LINE消息有字符限制
        if len(gemini_response) > 5000:  # LINE消息上限約為5000字符
            # 分段發送
            chunks = [gemini_response[i:i+4000] for i in range(0, len(gemini_response), 4000)]
            
            # 回复第一段
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text=chunks[0])
            )
            
            # 推送剩餘段落
            for chunk in chunks[1:]:
                line_bot_api.push_message(
                    user_id,
                    TextSendMessage(text=chunk)
                )
        else:
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