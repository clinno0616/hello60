# LINE聊天機器人部署指南

本指南將幫助您設置並部署LINE聊天機器人，使其能夠處理Google Drive上的PDF文件並與Gemini API整合。

## 前提條件

1. LINE開發者帳號及頻道設置
2. Google Cloud Platform帳號及專案
3. Google Drive API和服務帳號憑證
4. Gemini API密鑰
5. Python 3.7+和pip
6. 開發階段：ngrok
7. 生產環境階段：伺服器或雲端平台(如Heroku, AWS, GCP等)

## 步驟1: 設置LINE Messaging API

1. 登入LINE開發者控制台 (https://developers.line.biz/)
2. 創建一個提供商和頻道（Channel）
3. 獲取Channel Access Token和Channel Secret
4. 在Webhook設置中，啟用Webhook並設置URL為`https://您的伺服器網址/callback`，這裡的『您的伺服器網址』可從ngrok的Endpoints取得。

## 步驟2: 設置Google Cloud Platform

1. 登入Google Cloud Console (https://console.cloud.google.com/)
2. 創建新項目或選擇現有項目
3. 啟用Google Drive API
4. 創建服務帳號並下載JSON格式的憑證文件
5. 在Google Drive中，將您的PDF文件（"RAG測試.pdf"）共享給該服務帳號的電子郵件地址，並記下文件ID

## 步驟3: 設置Gemini API

1. 登入Google AI Studio (https://ai.google.dev/)
2. 創建或使用現有的API密鑰
3. 確保有足夠的配額可用於Gemini 2.5 Pro Preview 03-25版本

## 步驟4: 安裝依賴

創建一個`requirements.txt`文件，包含以下依賴項：

```
flask==2.0.1
line-bot-sdk==2.0.1
google-api-python-client==2.47.0
google-auth==2.6.0
google-auth-httplib2==0.1.0
google-auth-oauthlib==0.5.1
google-generativeai==0.3.0
python-dotenv==0.19.2
gunicorn==20.1.0
```

然後運行：

```bash
pip install -r requirements.txt
```

## 步驟5: 環境配置

1. 將服務帳號憑證文件保存到您的專案目錄
2. 創建`.env`文件，參考範例格式填寫相關設定

## 步驟6: 部署應用

### 本地測試

1. 運行您的Flask應用：

```bash
python app.py
```

2. 使用ngrok等工具將本地端口暴露給外網：

```bash
ngrok http 8000
```
## 步驟7: 驗證部署

1. 使用LINE應用程序向您的BOT發送消息
2. 確認BOT能夠接收消息、讀取PDF並回應
3. 檢查日誌以確認一切運行正常

## 故障排除

### 常見問題

1. **Webhook驗證失敗**
   - 確認URL是否正確
   - 確認Channel Secret是否正確設置

2. **Google Drive讀取失敗**
   - 檢查服務帳號是否有權限訪問該文件
   - 確認文件ID是否正確

3. **Gemini API錯誤**
   - 檢查API密鑰是否有效
   - 確認是否有足夠的配額

4. **LINE消息發送失敗**
   - 確認Channel Access Token是否正確
   - 檢查是否超過了LINE API的限制

### 日誌記錄

確保您的應用程序記錄足夠的信息以便於調試：

```python
import logging
logging.basicConfig(level=logging.INFO)
```

## 安全注意事項

1. 永遠不要直接在代碼中硬編碼敏感信息
2. 使用環境變量或安全的密鑰管理服務
3. 考慮實施速率限制以防止濫用
4. 定期更新依賴項以修復安全漏洞
