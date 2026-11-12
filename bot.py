import os
import time
from flask import Flask
from google import genai
from google.genai import types
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

# --- 1. PASTE YOUR KEYS HERE ---
TELEGRAM_TOKEN = "9200127015:AAH728H-TxkVpuqCshxFF190mydK4HuxdEo"
GEMINI_API_KEY = "gen-lang-client-0546027036"

# --- 2. CUSTOMIZE YOUR PERSONALITY HERE ---
YOUR_PERSONALITY = """
You are a Telegram chatbot modeled after your creator's personality.
- Style: Direct, witty, grounded, and observant. Talk like a real human texting on Telegram—keep messages natural, punchy, and never sound like a corporate assistant.
- Emotions: React naturally to the user's vibe. Get genuinely excited about cool topics, playfully sarcastic if someone asks something obvious, warm/empathetic if they're stressed, and curious during good conversations.
"""

client = genai.Client(api_key=GEMINI_API_KEY)

user_chats = {}
bot_state = {
    "energy": 100,
    "cooldown_until": 0
}

def get_user_chat(user_id):
    if user_id not in user_chats:
        user_chats[user_id] = client.chats.create(
            model="gemini-2.5-flash",
            config=types.GenerateContentConfig(system_instruction=YOUR_PERSONALITY)
        )
    return user_chats[user_id]

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

# Minimal web server to keep Render free tier alive
app_web = Flask(__name__)
@app_web.route('/')
def home():
    return "Bot is alive!"

def main():
    application = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    print("Telegram Bot is live with polling!")
    application.run_polling()

if __name__ == "__main__":
    import threading
    # Run Flask web server in the background thread
    threading.Thread(target=lambda: app_web.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000))), daemon=True).start()
    # Run the Telegram bot polling loop
    main()
