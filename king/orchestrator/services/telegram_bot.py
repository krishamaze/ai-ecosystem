"""
Telegram Bot Adapter for AI Ecosystem.

Thin layer that forwards messages to /converse and renders responses.
"""
import os
import logging
import httpx
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Internal API endpoint (container-to-container or localhost)
API_BASE = os.getenv("API_BASE_URL", "http://localhost:8000")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")


async def call_converse(message: str, user_id: str, context: dict = None) -> dict:
    """Call the /converse endpoint."""
    async with httpx.AsyncClient(timeout=120.0) as client:
        response = await client.post(
            f"{API_BASE}/meta/converse",
            json={
                "message": message,
                "medium": "telegram",
                "user_id": f"tg_{user_id}",
                "context": context or {}
            }
        )
        return response.json()


def build_keyboard(ui_elements: list) -> InlineKeyboardMarkup | None:
    """Convert UI elements to Telegram inline keyboard."""
    buttons = [el for el in ui_elements if el.get("type") == "button"]
    if not buttons:
        return None
    
    keyboard = []
    for btn in buttons:
        callback_data = f"{btn.get('payload', {}).get('next', 'unknown')}"
        keyboard.append([InlineKeyboardButton(btn["label"], callback_data=callback_data)])
    
    return InlineKeyboardMarkup(keyboard)


def format_response(result: dict) -> str:
    """Format API response for Telegram."""
    reply = result.get("reply", "No response")
    
    # Add code block if present
    for el in result.get("ui_elements", []):
        if el.get("type") == "code_block" and el.get("content"):
            code = el["content"]
            # Telegram has 4096 char limit - truncate if needed
            if len(code) > 3000:
                code = code[:3000] + "\n... (truncated)"
            reply += f"\n\n```\n{code}\n```"
            break
    
    return reply


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command."""
    await update.message.reply_text(
        "🤖 *AI Ecosystem Bot*\n\n"
        "I can help you:\n"
        "• Generate code in any language\n"
        "• Create video scripts\n"
        "• Review and deploy code\n\n"
        "Just tell me what you need!",
        parse_mode="Markdown"
    )


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle incoming text messages."""
    user_id = str(update.effective_user.id)
    message = update.message.text
    
    # Show typing indicator
    await update.message.chat.send_action("typing")
    
    try:
        result = await call_converse(message, user_id)
        reply_text = format_response(result)
        keyboard = build_keyboard(result.get("ui_elements", []))
        
        await update.message.reply_text(
            reply_text,
            parse_mode="Markdown",
            reply_markup=keyboard
        )
    except Exception as e:
        logger.error(f"Error calling /converse: {e}")
        await update.message.reply_text(f"❌ Error: {str(e)}")


async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle inline button presses."""
    query = update.callback_query
    await query.answer()
    
    user_id = str(update.effective_user.id)
    action = query.data
    
    # Map callback to message
    action_messages = {
        "generate_code": "I want to generate code",
        "generate_video": "I want to create a video script",
        "check_status": "Show me the system status",
        "deploy": "Deploy the code",
    }
    
    message = action_messages.get(action, f"Execute {action}")
    
    try:
        result = await call_converse(message, user_id)
        reply_text = format_response(result)
        keyboard = build_keyboard(result.get("ui_elements", []))
        
        await query.message.reply_text(
            reply_text,
            parse_mode="Markdown",
            reply_markup=keyboard
        )
    except Exception as e:
        logger.error(f"Error handling callback: {e}")
        await query.message.reply_text(f"❌ Error: {str(e)}")


async def preferences(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /preferences command."""
    user_id = str(update.effective_user.id)
    
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{API_BASE}/meta/user/tg_{user_id}/preferences")
        prefs = response.json()
    
    await update.message.reply_text(
        f"⚙️ *Your Preferences*\n\n"
        f"Language: `{prefs.get('preferred_language', 'python')}`\n"
        f"Code Style: `{prefs.get('code_style', 'clean')}`\n"
        f"Include Tests: `{prefs.get('include_tests', True)}`\n"
        f"Tone: `{prefs.get('content_tone', 'professional')}`\n\n"
        f"_Use /setlang <language> to change_",
        parse_mode="Markdown"
    )


async def set_language(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /setlang command."""
    user_id = str(update.effective_user.id)

    if not context.args:
        await update.message.reply_text("Usage: /setlang python|typescript|go|rust")
        return

    lang = context.args[0].lower()

    async with httpx.AsyncClient() as client:
        await client.put(
            f"{API_BASE}/meta/user/tg_{user_id}/preferences",
            json={"preferred_language": lang}
        )

    await update.message.reply_text(f"✅ Language set to `{lang}`", parse_mode="Markdown")


def create_bot_application() -> Application:
    """Create and configure the bot application."""
    if not TELEGRAM_BOT_TOKEN:
        raise ValueError("TELEGRAM_BOT_TOKEN not set")

    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    # Register handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("preferences", preferences))
    app.add_handler(CommandHandler("setlang", set_language))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(CallbackQueryHandler(handle_callback))

    return app


async def process_webhook_update(update_data: dict) -> None:
    """Process a webhook update from Telegram."""
    app = create_bot_application()
    async with app:
        update = Update.de_json(update_data, app.bot)
        await app.process_update(update)


def run_bot():
    """Run the bot in polling mode (blocking)."""
    logger.info("Starting Telegram bot in polling mode...")
    app = create_bot_application()
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    run_bot()

