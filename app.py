#!/usr/bin/env python3
import asyncio
import aiohttp
import json
import os
import pandas as pd
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import FSInputFile, InlineKeyboardMarkup, InlineKeyboardButton

from keep_alive import keep_alive  # 👈 import keep_alive

API_TOKEN = "YOUR_API_TOKEN_HERE"  # ⚠️ replace with your token

bot = Bot(token=API_TOKEN)
dp = Dispatcher()

# =========================
#  Instagram Username Check
# =========================
async def check_username(session: aiohttp.ClientSession, username: str) -> str:
    url = f"https://i.instagram.com/api/v1/users/web_profile_info/?username={username}"
    try:
        async with session.get(url) as response:
            if response.status == 404:
                return f"⚪ [AVAILABLE] {username}"
            elif response.status == 200:
                data = await response.json()
                if data.get("data", {}).get("user"):
                    return f"🟢 [ACTIVE] {username}"
                else:
                    return f"⚪ [AVAILABLE] {username}"
            else:
                return f"⚠️ [ERROR {response.status}] {username}"
    except Exception as e:
        return f"⚠️ [EXCEPTION] {username}: {e}"


async def process_file(input_file: str) -> tuple[str, list[str]]:
    with open(input_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    headers = {
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) Chrome/115.0",
        "x-ig-app-id": "936619743392459",
        "Accept-Language": "en-US,en;q=0.9",
    }

    results_list = []
    active_accounts = []

    async with aiohttp.ClientSession(headers=headers) as session:
        tasks = [asyncio.create_task(check_username(session, entry.get("username")))
                 for entry in data if entry.get("username")]
        results = await asyncio.gather(*tasks)

        results_list.extend(results)

        # Collect only active accounts
        for entry, result in zip(data, results):
            if result.startswith("🟢 [ACTIVE]"):
                active_accounts.append(entry)

    # Save active accounts JSON
    output_file = f"active-{os.path.basename(input_file)}"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(active_accounts, f, indent=4)

    return output_file, results_list


# =====================
#  JSON → Excel Convert
# =====================
def json_to_excel(json_file: str) -> str:
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


# =========================
# Telegram Bot Handlers
# =========================
@dp.message(Command("start"))
async def start(message: types.Message):
    await message.answer(
        "👋 Send me a JSON file of Instagram accounts.\n"
        "Choose one of the following options:\n\n"
        "1️⃣ Only Check (filter active usernames)\n"
        "2️⃣ Only Convert (JSON → Excel)\n"
        "3️⃣ Check + Convert (default)"
    )


@dp.message(F.document & F.document.file_name.endswith(".json"))
async def handle_json(message: types.Message):
    file = await bot.get_file(message.document.file_id)
    input_path = f"downloads/{message.document.file_name}"
    os.makedirs("downloads", exist_ok=True)
    await bot.download_file(file.file_path, input_path)

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔍 Only Check", callback_data=f"check:{input_path}")],
        [InlineKeyboardButton(text="📊 Only Convert", callback_data=f"convert:{input_path}")],
        [InlineKeyboardButton(text="✅ Check + Convert", callback_data=f"both:{input_path}")]
    ])
    await message.answer("📂 File received! What do you want me to do?", reply_markup=kb)


@dp.message(F.reply_to_message & F.reply_to_message.document)
async def handle_reply_to_json(message: types.Message):
    doc = message.reply_to_message.document

    if not doc.file_name.endswith(".json"):
        await message.answer("⚠️ Please reply to a JSON file only.")
        return

    file = await bot.get_file(doc.file_id)
    input_path = f"downloads/{doc.file_name}"
    os.makedirs("downloads", exist_ok=True)
    await bot.download_file(file.file_path, input_path)

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔍 Only Check", callback_data=f"check:{input_path}")],
        [InlineKeyboardButton(text="📊 Only Convert", callback_data=f"convert:{input_path}")],
        [InlineKeyboardButton(text="✅ Check + Convert", callback_data=f"both:{input_path}")]
    ])
    await message.answer("📂 You replied to a file! What do you want me to do?", reply_markup=kb)


@dp.callback_query()
async def handle_action(callback: types.CallbackQuery):
    action, input_path = callback.data.split(":", 1)

    if action == "check":
        await callback.message.edit_text("⏳ Checking usernames, please wait...")
        active_json, results_list = await process_file(input_path)

        results_text = "\n".join(results_list)
        for chunk in [results_text[i:i+4000] for i in range(0, len(results_text), 4000)]:
            await callback.message.answer(f"```\n{chunk}\n```", parse_mode="Markdown")

        await callback.message.answer_document(FSInputFile(active_json), caption="🔍 Active accounts JSON")

        try:
            os.remove(input_path)
            os.remove(active_json)
        except Exception as e:
            print(f"Cleanup error: {e}")

    elif action == "convert":
        await callback.message.edit_text("⏳ Converting JSON to Excel...")
        excel_file = json_to_excel(input_path)
        await callback.message.answer_document(FSInputFile(excel_file), caption="📊 Excel file")

        try:
            os.remove(input_path)
            os.remove(excel_file)
        except Exception as e:
            print(f"Cleanup error: {e}")

    elif action == "both":
        await callback.message.edit_text("⏳ Checking + Converting, please wait...")
        active_json, results_list = await process_file(input_path)
        excel_file = json_to_excel(active_json)

        await callback.message.answer_document(FSInputFile(active_json), caption="🔍 Active accounts JSON")
        await callback.message.answer_document(FSInputFile(excel_file), caption="📊 Excel file")

        try:
            os.remove(input_path)
            os.remove(active_json)
            os.remove(excel_file)
        except Exception as e:
            print(f"Cleanup error: {e}")

    await callback.answer()


# =========================
# Main Entry
# =========================
async def main():
    print("🤖 Bot is running...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    keep_alive()  # 👈 start Flask keep-alive
    asyncio.run(main())
