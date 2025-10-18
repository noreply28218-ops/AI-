#!/usr/bin/env python3
import os
import logging
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    ContextTypes,
    CommandHandler,
    MessageHandler,
    filters,
)
from openai import OpenAI

# --- Setup Logging ---
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# --- Environment Variables ---
TELEGRAM_TOKEN = os.getenv("7091051118:AAGH5QQgCPS52-l724N16U2l8gUVlQYmuyo")
OPENAI_API_KEY = os.getenv("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")

if not TELEGRAM_TOKEN or not OPENAI_API_KEY:
    raise SystemExit("Missing TELEGRAM_TOKEN or OPENAI_API_KEY environment variables.")

# --- OpenAI Client ---
client = OpenAI(api_key=OPENAI_API_KEY)

# --- Memory Store ---
user_contexts = {}


# --- Commands ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 Hello! I'm your AI assistant. Type anything to chat!")


async def clear(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user_contexts.pop(chat_id, None)
    await update.message.reply_text("✅ Chat history cleared.")


# --- Chat Handler ---
async def chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    text = update.message.text

    # Prepare context
    if chat_id not in user_contexts:
        user_contexts[chat_id] = [
            {"role": "system", "content": "You are a friendly and helpful AI assistant."}
        ]
    user_contexts[chat_id].append({"role": "user", "content": text})

    # Typing indicator
    await update.message.chat.send_action(action="typing")

    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=user_contexts[chat_id],
            max_tokens=600,
            temperature=0.7,
        )
        reply = response.choices[0].message.content
    except Exception as e:
        logger.error(e)
        reply = "⚠️ Sorry, I couldn't reach OpenAI right now."

    user_contexts[chat_id].append({"role": "assistant", "content": reply})
    await update.message.reply_text(reply)


# --- Main Bot Setup ---
def main():
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("clear", clear))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, chat))

    logger.info("🤖 Bot is running...")
    app.run_polling()


if __name__ == "__main__":
    main()
  
