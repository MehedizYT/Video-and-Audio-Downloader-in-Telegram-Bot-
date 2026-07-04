import os
import asyncio
import logging
import yt_dlp
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    Message, 
    CallbackQuery, 
    InlineKeyboardButton, 
    InlineKeyboardMarkup, 
    LabeledPrice, 
    PreCheckoutQuery,
    FSInputFile
)
from config import API_TOKEN, REQUIRED_CHANNEL, PREMIUM_PRICE

# Logging setup
logging.basicConfig(level=logging.INFO)

bot = Bot(token=API_TOKEN)
dp = Dispatcher()

# Simple Database Mockup
# In production, use SQLite or MongoDB
user_data = {} # {user_id: {"is_premium": False, "downloads": 0}}

class DownloadState(StatesGroup):
    choosing_format = State()

# --- Keyboards ---

def get_format_keyboard(url: str):
    buttons = [
        [
            InlineKeyboardButton(text="🎥 Video (MP4)", callback_data=f"vid|{url}"),
            InlineKeyboardButton(text="🎵 Audio (MP3)", callback_data=f"aud|{url}")
        ],
        [InlineKeyboardButton(text="⭐ Get Premium (No Limits)", callback_data="buy_premium")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

# --- Downloader Logic ---

def progress_hook(d):
    if d['status'] == 'downloading':
        logging.info(f"Downloading: {d.get('_percent_str', '0%')}")

async def download_media(url: str, mode: str, is_premium: bool):
    """
    Advanced yt-dlp logic
    """
    file_id = f"{asyncio.get_event_loop().time()}"
    out_path = f"downloads/{file_id}.%(ext)s"
    
    # Premium vs Free Logic
    # Free users get capped quality to save server bandwidth
    format_selector = 'bestvideo[height<=720]+bestaudio/best' if is_premium else 'worstvideo[height<=480]+bestaudio/best'
    
    if mode == "aud":
        ydl_opts = {
            'format': 'bestaudio/best',
            'outtmpl': out_path,
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
        }
    else:
        ydl_opts = {
            'format': format_selector,
            'outtmpl': out_path,
            'merge_output_format': 'mp4',
        }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = await asyncio.to_thread(ydl.extract_info, url, download=True)
        filename = ydl.prepare_filename(info)
        
        if mode == "aud":
            filename = filename.rsplit('.', 1)[0] + ".mp3"
            
        return filename, info.get('title', 'Media')

# --- Handlers ---

@dp.message(Command("start"))
async def cmd_start(message: Message):
    uid = message.from_user.id
    if uid not in user_data:
        user_data[uid] = {"is_premium": False, "downloads": 0}
        
    welcome = (
        "👋 **Welcome to Ultra Downloader**\n\n"
        "1. Send any link (YouTube, X, TikTok, IG)\n"
        "2. Choose Format\n"
        "3. Download instantly!\n\n"
        "🌟 **Premium Status:** " + ("✅ Active" if user_data[uid]["is_premium"] else "❌ Inactive")
    )
    await message.answer(welcome, parse_mode="Markdown")

@dp.message(F.text.contains("http"))
async def link_handler(message: Message):
    uid = message.from_user.id
    
    # Force Subscribe Logic (Optional)
    if REQUIRED_CHANNEL:
        try:
            member = await bot.get_chat_member(REQUIRED_CHANNEL, uid)
            if member.status in ['left', 'kicked']:
                return await message.answer(f"⚠️ Please join our channel {REQUIRED_CHANNEL} to use the bot!")
        except Exception:
            pass

    await message.answer(
        "✨ **Link Detected!**\nChoose your preferred format:",
        reply_markup=get_format_keyboard(message.text),
        parse_mode="Markdown"
    )

@dp.callback_query(F.data.startswith("vid") | F.data.startswith("aud"))
async def process_download(callback: CallbackQuery):
    uid = callback.from_user.id
    mode, url = callback.data.split("|")
    
    await callback.message.edit_text("⏳ **Processing... Please wait.**")
    
    try:
        is_premium = user_data.get(uid, {}).get("is_premium", False)
        
        # Call Download Logic
        file_path, title = await download_media(url, mode, is_premium)
        
        await callback.message.edit_text("📤 **Download complete! Uploading to Telegram...**")
        
        media_file = FSInputFile(file_path)
        
        if mode == "vid":
            await bot.send_video(callback.message.chat.id, video=media_file, caption=f"🎬 {title}")
        else:
            await bot.send_audio(callback.message.chat.id, audio=media_file, caption=f"🎵 {title}")
            
        # Cleanup
        if os.path.exists(file_path):
            os.remove(file_path)
        await callback.message.delete()

    except Exception as e:
        logging.error(e)
        await callback.message.edit_text(f"❌ **Error:** File might be too large or link is private.\n\n`{str(e)[:50]}`", parse_mode="Markdown")

# --- Telegram Star System Logic ---

@dp.callback_query(F.data == "buy_premium")
async def send_star_invoice(callback: CallbackQuery):
    await bot.send_invoice(
        chat_id=callback.message.chat.id,
        title="Premium Membership",
        description="Unlock 4K Video, High Quality MP3, and No Daily Limits!",
        payload="premium_upgrade",
        provider_token="", # Empty for Telegram Stars
        currency="XTR",
        prices=[LabeledPrice(label="Premium", amount=PREMIUM_PRICE)] # e.g. 50 Stars
    )

@dp.pre_checkout_query()
async def pre_checkout_handler(query: PreCheckoutQuery):
    # Add logic here to check if your server is overloaded
    await query.answer(ok=True)

@dp.message(F.successful_payment)
async def payment_success(message: Message):
    uid = message.from_user.id
    if uid not in user_data:
        user_data[uid] = {}
    
    user_data[uid]["is_premium"] = True
    
    await message.answer(
        "🌟 **Payment Successful!**\n\n"
        "You now have Premium access:\n"
        "✅ Maximum Quality Enabled\n"
        "✅ No Speed Limits\n"
        "✅ Priority Support",
        parse_mode="Markdown"
    )

# --- Initialize ---

async def main():
    if not os.path.exists("downloads"):
        os.makedirs("downloads")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
