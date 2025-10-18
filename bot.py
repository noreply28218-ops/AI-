#!/usr/bin/env python3
"""
Telegram bot that forwards messages to OpenAI gpt-3.5-turbo and returns replies.

Usage:
  - Set environment variables TELEGRAM_TOKEN and OPENAI_API_KEY
  - Run: python bot.py
"""

import os
import logging
import time
from typing import Dict, List

import openai
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    ContextTypes,
    CommandHandler,
    MessageHandler,
    filters,
)

# Logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# Load keys from environment variables (do NOT hardcode keys)
TELEGRAM_TOKEN = os.getenv("7091051118:AAGH5QQgCPS52-l724N16U2l8gUVlQYmuyo")
OPENAI_API_KEY = os.getenv("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")

if not TELEGRAM_TOKEN or not OPENAI_API_KEY:
    logger.error(
        "Missing TELEGRAM_TOKEN or OPENAI_API_KEY. Set them as environment variables."
    )
    raise SystemExit("Set TELEGRAM_TOKEN and OPENAI_API_KEY environment variables.")

openai.api_key = OPENAI_API_KEY

# Chat state: keep a small per-chat message history (in-memory).
# For production, use a persistent DB if you need long histories or multi-instance.
CONTEXTS: Dict[int, List[dict]] = {}
MAX_HISTORY_MESSAGES = 10  # number of rounds to keep per chat


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Hi! I'm an AI chat bot. Send me a message and I'll reply using gpt-3.5-turbo."
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Just send any message — I'll forward it to the AI.")


def _ensure_chat_history(chat_id: int):
    if chat_id not in CONTEXTS:
        CONTEXTS[chat_id] = [
            {"role": "system", "content": "You are a helpful assistant."}
        ]


def _append_user_message(chat_id: int, text: str):
    _ensure_chat_history(chat_id)
    CONTEXTS[chat_id].append({"role": "user", "content": text})
    # Trim history
    if len(CONTEXTS[chat_id]) > MAX_HISTORY_MESSAGES + 1:  # +1 for system
        # keep the system message and the last MAX_HISTORY_MESSAGES messages
        CONTEXTS[chat_id] = [CONTEXTS[chat_id][0]] + CONTEXTS[chat_id][-MAX_HISTORY_MESSAGES:]


def _append_assistant_message(chat_id: int, text: str):
    _ensure_chat_history(chat_id)
    CONTEXTS[chat_id].append({"role": "assistant", "content": text})
    if len(CONTEXTS[chat_id]) > MAX_HISTORY_MESSAGES + 1:
        CONTEXTS[chat_id] = [CONTEXTS[chat_id][0]] + CONTEXTS[chat_id][-MAX_HISTORY_MESSAGES:]


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text.strip()
    chat_id = update.effective_chat.id

    # Optional: quick blocking / safety
    if user_text.lower() in ("/start", "/help"):
        return

    # Acknowledge to user to avoid Telegram timeouts for slow AI calls
    # We keep this quick; if you want a spinner you can send ChatAction.
    await update.message.chat.send_action(action="typing")

    # Build / update history
    _append_user_message(chat_id, user_text)

    try:
        # Call OpenAI Chat Completions
        resp = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=CONTEXTS[chat_id],
            max_tokens=600,
            temperature=0.7,
            n=1,
        )
        # Extract assistant reply
        assistant_text = resp["choices"][0]["message"]["content"].strip()
    except openai.error.OpenAIError as e:
        logger.exception("OpenAI API error")
        assistant_text = "Sorry, I couldn't get a response from the AI service. Try again later."

    # Save to history and reply
    _append_assistant_message(chat_id, assistant_text)

    # Telegram messages must be < 4096 chars; if longer, split
    MAX_TG = 4000
    if len(assistant_text) <= MAX_TG:
        await update.message.reply_text(assistant_text)
    else:
        for i in range(0, len(assistant_text), MAX_TG):
            await update.message.reply_text(assistant_text[i : i + MAX_TG])


async def clear_history_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if chat_id in CONTEXTS:
        CONTEXTS[chat_id] = [{"role": "system", "content": "You are a helpful assistant."}]
    await update.message.reply_text("Conversation history cleared.")


def main():
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("clear", clear_history_command))
    app.add_handler(
        MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message)
    )

    logger.info("Bot started. Listening for messages...")
    app.run_polling(stop_signals=None)


if __name__ == "__main__":
    main()
