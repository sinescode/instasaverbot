#!/usr/bin/env python3
import json
import os
import pandas as pd
import requests
from flask import Flask, request, Response, render_template_string
import hashlib
import time

# Replace with your actual token and webhook URL
API_TOKEN = "7992205107:AAEEDo71Ymk6r9DFyYrTCDSHznPziXaHnXM"
WEBHOOK_URL = "https://instasaverbot-qxlt.onrender.com/webhook"

app = Flask(__name__)

# HTML template for the landing page
LANDING_PAGE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Insta Saver Tool</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
        }
        
        body {
            background: linear-gradient(135deg, #6e8efb, #a777e3);
            min-height: 100vh;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            color: #fff;
            padding: 20px;
        }
        
        .container {
            max-width: 800px;
            width: 100%;
            background: rgba(255, 255, 255, 0.1);
            backdrop-filter: blur(10px);
            border-radius: 20px;
            padding: 40px;
            box-shadow: 0 15px 35px rgba(0, 0, 0, 0.2);
            text-align: center;
        }
        
        h1 {
            font-size: 3.5rem;
            margin-bottom: 20px;
            text-shadow: 2px 2px 4px rgba(0, 0, 0, 0.3);
        }
        
        .highlight {
            color: #ffdd59;
            font-weight: bold;
        }
        
        p {
            font-size: 1.2rem;
            line-height: 1.6;
            margin-bottom: 30px;
        }
        
        .features {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin: 40px 0;
        }
        
        .feature {
            background: rgba(255, 255, 255, 0.15);
            padding: 20px;
            border-radius: 15px;
            transition: transform 0.3s ease;
        }
        
        .feature:hover {
            transform: translateY(-5px);
        }
        
        .feature h3 {
            margin-bottom: 15px;
            font-size: 1.4rem;
        }
        
        .cta {
            margin-top: 30px;
        }
        
        .btn {
            display: inline-block;
            background: #ffdd59;
            color: #333;
            padding: 15px 30px;
            border-radius: 50px;
            text-decoration: none;
            font-weight: bold;
            font-size: 1.2rem;
            transition: all 0.3s ease;
            box-shadow: 0 5px 15px rgba(0, 0, 0, 0.2);
        }
        
        .btn:hover {
            transform: translateY(-3px);
            box-shadow: 0 8px 20px rgba(0, 0, 0, 0.3);
            background: #ffd32a;
        }
        
        .logo {
            font-size: 5rem;
            margin-bottom: 20px;
            animation: pulse 2s infinite;
        }
        
        @keyframes pulse {
            0% { transform: scale(1); }
            50% { transform: scale(1.1); }
            100% { transform: scale(1); }
        }
        
        footer {
            margin-top: 40px;
            text-align: center;
            font-size: 0.9rem;
            opacity: 0.8;
        }
        
        @media (max-width: 768px) {
            h1 {
                font-size: 2.5rem;
            }
            
            .container {
                padding: 25px;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="logo">📁</div>
        <h1>Hello <span class="highlight">Insta Saver Tool</span> User!</h1>
        <p>Welcome to our powerful JSON to Excel converter Telegram bot. Easily convert your JSON files to Excel format with just a few clicks!</p>
        
        <div class="features">
            <div class="feature">
                <h3>⚡ Fast Conversion</h3>
                <p>Convert JSON files to Excel format in seconds with our optimized algorithm.</p>
            </div>
            <div class="feature">
                <h3>🔒 Secure Processing</h3>
                <p>Your files are processed securely and deleted immediately after conversion.</p>
            </div>
            <div class="feature">
                <h3>📱 Telegram Integration</h3>
                <p>Use our bot directly through Telegram - no additional apps required!</p>
            </div>
        </div>
        
        <div class="cta">
            <p>Ready to get started?</p>
            <a href="https://t.me/@instasavertoolbot" class="btn">Start Converting Now</a>
        </div>
    </div>
</body>
</html>
"""

# In-memory storage for file paths
file_storage = {}

# Telegram API base URL
TELEGRAM_API = f"https://api.telegram.org/bot{API_TOKEN}"

# =====================
# JSON → Excel Convert
# =====================
def json_to_excel(json_file: str) -> str:
    try:
        df = pd.read_json(json_file)
        
        expected_cols = ["username", "password", "auth_code", "email"]
        available_cols = [col for col in expected_cols if col in df.columns]
        df = df[available_cols]

        rename_map = {
            "username": "Username",
            "password": "Password",
            "auth_code": "Authcode",
            "email": "Email"
        }
        df.rename(columns={k: v for k, v in rename_map.items() if k in df.columns}, inplace=True)

        excel_file = os.path.splitext(json_file)[0] + ".xlsx"
        df.to_excel(excel_file, index=False)

        return excel_file
    except Exception as e:
        raise Exception(f"Error converting JSON to Excel: {str(e)}")

# =====================
# Telegram API Helpers
# =====================
def send_message(chat_id: int, text: str):
    url = f"{TELEGRAM_API}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text
    }
    try:
        response = requests.post(url, json=payload)
        response.raise_for_status()
    except Exception as e:
        print(f"Error sending message: {e}")

def send_document(chat_id: int, document_path: str, caption: str):
    url = f"{TELEGRAM_API}/sendDocument"
    try:
        with open(document_path, "rb") as file:
            files = {"document": file}
            payload = {
                "chat_id": chat_id,
                "caption": caption
            }
            response = requests.post(url, data=payload, files=files)
            response.raise_for_status()
    except Exception as e:
        print(f"Error sending document: {e}")

def download_file(file_id: str, file_path: str):
    try:
        # Get file info
        url = f"{TELEGRAM_API}/getFile?file_id={file_id}"
        response = requests.get(url)
        response.raise_for_status()
        file_data = response.json()
        
        if not file_data.get("ok"):
            raise Exception("Failed to get file info")
        
        file_url = f"https://api.telegram.org/file/bot{API_TOKEN}/{file_data['result']['file_path']}"
        response = requests.get(file_url)
        response.raise_for_status()
        
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, "wb") as f:
            f.write(response.content)
    except Exception as e:
        raise Exception(f"Error downloading file: {e}")

def generate_file_id(file_path: str) -> str:
    """Generate a short unique ID for the file path."""
    return hashlib.md5(f"{file_path}{time.time()}".encode()).hexdigest()[:8]

# =====================
# Flask Routes
# =====================
@app.route("/")
def index():
    return render_template_string(LANDING_PAGE)

@app.route("/webhook", methods=["POST"])
def webhook():
    try:
        # Get the update from Telegram
        update = request.get_json()
        
        if not update or "message" not in update:
            return Response(status=200)

        message = update["message"]
        chat_id = message["chat"]["id"]

        # Handle /start command
        if "text" in message and message["text"] == "/start":
            send_message(
                chat_id,
                "👋 Send me a JSON file to convert to Excel.\n"
                "You can also reply to a JSON file with any message to convert it."
            )
            return Response(status=200)

        # Handle JSON file directly sent
        if "document" in message and message["document"]["file_name"].endswith(".json"):
            file_id = message["document"]["file_id"]
            file_name = message["document"]["file_name"]
            input_path = f"downloads/{file_name}"

            try:
                # Download file
                download_file(file_id, input_path)
                send_message(chat_id, "⏳ Converting JSON to Excel...")
                
                # Convert to Excel
                excel_file = json_to_excel(input_path)
                
                # Send the Excel file
                send_document(chat_id, excel_file,"")
                
                # Clean up
                try:
                    os.remove(input_path)
                    os.remove(excel_file)
                except:
                    pass
                    
            except Exception as e:
                send_message(chat_id, f"❌ Error: {str(e)}")
                
            return Response(status=200)

        # Handle reply to a JSON file
        if "reply_to_message" in message:
            replied_message = message["reply_to_message"]
            
            if "document" in replied_message and replied_message["document"]["file_name"].endswith(".json"):
                file_id = replied_message["document"]["file_id"]
                file_name = replied_message["document"]["file_name"]
                input_path = f"downloads/{file_name}"

                try:
                    # Download file
                    download_file(file_id, input_path)
                    send_message(chat_id, "⏳ Converting JSON to Excel...")
                    
                    # Convert to Excel
                    excel_file = json_to_excel(input_path)
                    
                    # Send the Excel file
                    send_document(chat_id, excel_file, "")
                    
                    # Clean up
                    try:
                        os.remove(input_path)
                        os.remove(excel_file)
                    except:
                        pass
                        
                except Exception as e:
                    send_message(chat_id, f"❌ Error: {str(e)}")
                    
                return Response(status=200)

        # If it's not a JSON file or start command
        send_message(chat_id, "Please send a JSON file or reply to a JSON file to convert it to Excel format.")
        return Response(status=200)
        
    except Exception as e:
        print(f"Webhook error: {e}")
        return Response(status=200)

@app.route("/webhook", methods=["GET"])
def verify_webhook():
    # For webhook verification
    return Response(status=200)

# =====================
# Set up Webhook
# =====================
def set_webhook():
    try:
        url = f"{TELEGRAM_API}/setWebhook"
        payload = {"url": WEBHOOK_URL}
        response = requests.post(url, json=payload)
        if response.status_code == 200:
            print("Webhook set successfully")
        else:
            print(f"Failed to set webhook: {response.text}")
    except Exception as e:
        print(f"Error setting webhook: {e}")

# =====================
# Main Entry
# =====================
if __name__ == "__main__":
    # Create downloads directory if it doesn't exist
    os.makedirs("downloads", exist_ok=True)
    
    set_webhook()
    app.run(host="0.0.0.0", port=10000)
