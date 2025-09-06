#!/usr/bin/env python3
import asyncio
import json
import os
import pandas as pd
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import FSInputFile

from keep_alive import keep_alive  # Import keep_alive

API_TOKEN = "7992205107:AAEEDo71Ymk6r9DFyYrTCDSHznPziXaHnXM"  # Replace with your token

bot = Bot(token=API_TOKEN)
dp = Dispatcher()

# =====================
#  JSON → Excel Convert
# =====================
def json_to_excel(json_file: str) -> tuple[str, str]:
    try:
        # Read JSON file
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Check if data is a list of dictionaries
        if not (isinstance(data, list) and len(data) > 0 and isinstance(data[0], dict)):
            return None, "The JSON file must contain a list of objects/dictionaries."
        
        # Convert to DataFrame
        df = pd.DataFrame(data)
        
        # Check if any expected columns exist
        expected_cols = ["username", "password", "auth_code", "email"]
        available_cols = [col for col in expected_cols if col in df.columns]
        
        if not available_cols:
            return None, "None of the expected columns (username, password, auth_code, email) were found in the JSON file."
        
        # Keep only available columns
        df = df[available_cols]
        
        # Rename columns for better presentation
        rename_map = {
            "username": "Username",
            "password": "Password",
            "auth_code": "Authcode",
            "email": "Email"
        }
        df.rename(columns={k: v for k, v in rename_map.items() if k in df.columns}, inplace=True)
        
        # Generate output filename
        excel_file = os.path.splitext(json_file)[0] + ".xlsx"
        df.to_excel(excel_file, index=False)
        
        # Create a summary of what was converted
        summary = f"Converted {len(df)} rows with columns: {', '.join(df.columns)}"
        
        return excel_file, summary
        
    except json.JSONDecodeError:
        return None, "Invalid JSON format. Please provide a valid JSON file."
    except Exception as e:
        return None, f"Error processing file: {str(e)}"

# =========================
# Telegram Bot Handlers
# =========================
@dp.message(Command("start"))
async def start(message: types.Message):
    await message.answer(
        "👋 Send me a JSON file to convert it to Excel format.\n"
        "I'll automatically convert any JSON file you send me.\n\n"
        "Note: I look for these specific columns:\n"
        "- username\n- password\n- auth_code\n- email\n\n"
        "If these columns aren't found, I'll let you know."
    )

@dp.message(F.document & F.document.file_name.endswith(".json"))
async def handle_json(message: types.Message):
    # Download the file
    file = await bot.get_file(message.document.file_id)
    input_path = f"downloads/{message.document.file_name}"
    os.makedirs("downloads", exist_ok=True)
    await bot.download_file(file.file_path, input_path)
    
    # Process the file
    await message.answer("⏳ Converting JSON to Excel...")
    
    try:
        excel_file, summary = json_to_excel(input_path)
        
        if excel_file:
            await message.answer_document(
                FSInputFile(excel_file), 
                caption=f"✅ {summary}"
            )
            # Clean up files
            os.remove(excel_file)
        else:
            await message.answer(f"❌ {summary}")
            
    except Exception as e:
        await message.answer(f"❌ Unexpected error: {str(e)}")
    
    # Clean up input file
    try:
        os.remove(input_path)
    except Exception as e:
        print(f"Cleanup error: {e}")

# =========================
# Main Entry
# =========================
async def main():
    print("🤖 Bot is running...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    keep_alive()  # Start Flask keep-alive
    asyncio.run(main())
