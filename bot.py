import os
import asyncio
import yt_dlp
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import LabeledPrice, PreCheckoutQuery, InlineKeyboardButton, InlineKeyboardMarkup
from config import API_TOKEN, ADMIN_ID, REQUIRED_CHANNEL, PREMIUM_PRICE

bot = Bot(token=API_TOKEN)
dp = Dispatcher()

# Database Mockup (Use SQLite/Redis for production)
users_db = {} # {user_id: {"premium": False}}

# --- Utility Functions ---

async def check_subscription(user_id):
    if not REQUIRED_CHANNEL:
        return True
    try:
        member = await bot.get_chat_member(chat_id=REQUIRED_CHANNEL, user_id=user_id)
        return member.status in ["member", "administrator", "creator"]
    except Exception:
        return False

def download_media(url, mode="video"):
    """Core logic using yt-dlp"""
    ydl_opts = {
        'format': 'bestaudio/best' if mode == "audio" else 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
        'outtmpl': 'downloads/%(id)s.%(ext)s',
        'max_filesize': 50 * 1024 * 1024, # 50MB limit for standard Telegram bots
        'quiet': True
    }
    
    if mode == "audio":
        ydl_opts['postprocessors'] = [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }]

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        filename = ydl.prepare_filename(info)
        if mode == "audio":
            filename = filename.rsplit('.', 1)[0] + ".mp3"
        return filename, info.get('title', 'Media')

# --- Handlers ---

@dp.message(Command("start"))
async def start_cmd(message: types.Message):
    welcome_text = (
        "🚀 **Advanced Downloader Bot**\n\n"
        "Send me any link from YouTube, TikTok, Instagram, or X!\n\n"
        "⭐ /premium - Get Premium via Telegram Stars\n"
        "⚙️ /settings - Configure preferences"
    )
    await message.answer(welcome_text, parse_mode="Markdown")

@dp.message(Command("premium"))
async def premium_cmd(message: types.Message):
    prices = [LabeledPrice(label="Premium Lifetime Access", amount=PREMIUM_PRICE)]
    await bot.send_invoice(
        chat_id=message.chat.id,
        title="Upgrade to Premium",
        description="Unlock faster downloads and higher quality!",
        payload="premium_sub",
        provider_token="", # Empty for Telegram Stars
        currency="XTR",
        prices=prices
    )

@dp.pre_checkout_query()
async def process_pre_checkout(pre_checkout_query: PreCheckoutQuery):
    await bot.answer_pre_checkout_query(pre_checkout_query.id, ok=True)

@dp.message(F.successful_payment)
async def success_payment(message: types.Message):
    user_id = message.from_user.id
    users_db[user_id] = {"premium": True}
    await message.answer("🎉 Payment Successful! You are now a Premium Member.")

@dp.message(F.text.contains("http"))
async def handle_download(message: types.Message):
    user_id = message.from_user.id
    
    # 1. Check Force Sub
    if not await check_subscription(user_id):
        return await message.answer(f"❌ Please join {REQUIRED_CHANNEL} to use this bot.")

    url = message.text
    msg = await message.answer("🔍 Processing link...")

    try:
        # Create download directory if not exists
        if not os.path.exists('downloads'):
            os.makedirs('downloads')

        # Logic: Default to Video
        file_path, title = await asyncio.to_thread(download_media, url, "video")
        
        await msg.edit_text("📤 Uploading to Telegram...")
        
        video = types.FSInputFile(file_path)
        await message.answer_video(video=video, caption=f"✅ {title}")
        
        # Cleanup
        os.remove(file_path)
        await msg.delete()

    except Exception as e:
        await msg.edit_text(f"❌ Error: {str(e)[:100]}")

# --- Main Entry ---

async def main():
    print("Bot is running...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
