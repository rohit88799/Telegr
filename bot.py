import os
import time
from flask import Flask, request
from google import genai
from google.genai import types
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

TELEGRAM_TOKEN = "9200127015:AAH728H-TxkVpuqCshxFF190mydK4HuxdEo"
GEMINI_API_KEY = "gen-lang-client-0546027036"

# Your Render public URL (from your Render dashboard, e.g. https://your-app-name.onrender.com)
RENDER_URL = "https://YOUR-RENDER-APP-NAME.onrender.com"

YOUR_PERSONALITY = """
You are a Telegram chatbot modeled after your creator's personality.
- Style: Direct, witty, grounded, and observant. Talk like a real human texting on Telegram—keep messages natural, punchy, and never sound like a corporate assistant.
- Emotions: React naturally to the user's vibe. Get genuinely excited about cool topics, playfully sarcastic if someone asks something obvious, warm/empathetic if they're stressed, and curious during good conversations.
"""

client = genai.Client(api_key=GEMINI_API_KEY)
user_chats = {}
bot_state = {"energy": 100, "cooldown_until": 0}

def get_user_chat(user_id):
    if user_id not in user_chats:
        user_chats[user_id] = client.chats.create(
            model="gemini-2.5-flash",
            config=types.GenerateContentConfig(system_instruction=YOUR_PERSONALITY)
        )
    return user_chats[user_id]

app_flask = Flask(__name__)
telegram_app = Application.builder().token(TELEGRAM_TOKEN).build()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Hey! I'm awake and ready to talk. What's on your mind?")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_name = update.effective_user.first_name or "Friend"
    user_text = update.message.text
    now = time.time()

    if now < bot_state["cooldown_until"]:
        mins_left = int((bot_state["cooldown_until"] - now) // 60) + 1
        await update.message.reply_text(f"😴 *Zzz...* Brain is fried. Give me ~{mins_left} min to recharge!")
        return
    elif bot_state["cooldown_until"] != 0:
        bot_state["energy"] = 100
        bot_state["cooldown_until"] = 0

    bot_state["energy"] -= 10
    energy = bot_state["energy"]
    chat = get_user_chat(user_id)

    if energy <= 0:
        bot_state["cooldown_until"] = now + 300
        system_note = f"[SYSTEM: Energy hit 0%. Tell {user_name} you are exhausted, yawn, and need 5 minutes to rest.]"
    elif energy <= 30:
        system_note = f"[SYSTEM: Energy is low ({energy}%). Act tired, yawn, and warn {user_name} of a break soon.]"
    else:
        system_note = f"[SYSTEM: Energy: {energy}%. Talk naturally with emotion.]"

    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
    response = chat.send_message(f"{system_note}\nUser message: {user_text}")
    await update.message.reply_text(response.text)

telegram_app.add_handler(CommandHandler("start", start))
telegram_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

@app_flask.route('/')
def home():
    return "Bot is alive and running on Webhooks!"

@app_flask.route(f"/{TELEGRAM_TOKEN}", methods=["POST"])
def webhook():
    update = Update.de_json(request.get_json(force=True), telegram_app.bot)
    async def process():
        await telegram_app.initialize()
        await telegram_app.process_update(update)
    import asyncio
    asyncio.run(process())
    return "OK", 200

if __name__ == "__main__":
    import asyncio
    async def setup_webhook():
        await telegram_app.initialize()
        await telegram_app.bot.set_webhook(url=f"{RENDER_URL}/{TELEGRAM_TOKEN}")
    asyncio.run(setup_webhook())
    
    port = int(os.environ.get("PORT", 10000))
    app_flask.run(host="0.0.0.0", port=port)
