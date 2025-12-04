"""
KING Telegram Bot - Cloud Run webhook service.
Part of the Kingdom infrastructure.
"""
import os
import httpx
from fastapi import FastAPI, Request
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters
from contextlib import asynccontextmanager

KING_GATEWAY = os.getenv("KING_GATEWAY_URL", "https://king-gateway-250524159533.us-central1.run.app")
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

# Global bot application
ptb_app: Application = None


async def call_king(endpoint: str, payload: dict) -> dict:
    """Call KING Gateway API."""
    async with httpx.AsyncClient(timeout=120.0) as client:
        response = await client.post(f"{KING_GATEWAY}/{endpoint}", json=payload)
        response.raise_for_status()
        return response.json()


async def start_handler(update: Update, context):
    """Handle /start command."""
    user = update.effective_user
    await update.message.reply_text(
        f"👑 Welcome to KING, {user.first_name}!\n\n"
        "I'm your AI Kingdom. Just tell me what you need:\n\n"
        "• Write code\n• Plan videos\n• Analyze anything\n\n"
        "Commands:\n/code <task>\n/video <topic>\n\nOr just type naturally!"
    )


async def code_handler(update: Update, context):
    """Handle /code command."""
    if not context.args:
        await update.message.reply_text("Usage: /code <task>")
        return
    task = " ".join(context.args)
    user_id = f"tg_{update.effective_user.id}"
    await update.message.reply_text("⚙️ Generating code...")
    try:
        result = await call_king("execute/code_writer", {
            "agent_name": "code_writer",
            "input_data": {"user_id": user_id, "task": task}
        })
        code = result.get("code", str(result))[:3500]
        await update.message.reply_text(f"```python\n{code}\n```", parse_mode="Markdown")
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)[:200]}")


async def video_handler(update: Update, context):
    """Handle /video command."""
    if not context.args:
        await update.message.reply_text("Usage: /video <topic>")
        return
    topic = " ".join(context.args)
    user_id = f"tg_{update.effective_user.id}"
    await update.message.reply_text("🎬 Planning video...")
    try:
        result = await call_king("pipeline/run", {
            "steps": ["video_planner", "script_writer"],
            "initial_input": {"user_id": user_id, "topic": topic}
        })
        output = result.get("results", [{}])[-1].get("output", result)
        await update.message.reply_text(f"📹 Video Plan:\n\n{str(output)[:3500]}")
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)[:200]}")


def escape_html(text: str) -> str:
    """Escape HTML special characters."""
    return str(text).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def format_output(output: dict) -> str:
    """Format agent output for Telegram (HTML mode)."""
    if not isinstance(output, dict):
        return escape_html(str(output))[:3000]

    lines = []
    for key, value in output.items():
        if key == "confidence":
            continue
        title = key.replace("_", " ").title()
        if isinstance(value, list):
            lines.append(f"\n<b>{escape_html(title)}:</b>")
            for item in value[:5]:
                lines.append(f"• {escape_html(str(item))}")
        elif isinstance(value, dict):
            lines.append(f"\n<b>{escape_html(title)}:</b>")
            for k, v in list(value.items())[:5]:
                lines.append(f"• {escape_html(str(k))}: {escape_html(str(v))}")
        else:
            lines.append(f"\n<b>{escape_html(title)}:</b>\n{escape_html(str(value))}")

    return "\n".join(lines)[:3500]


async def message_handler(update: Update, context):
    """Handle any text message - smart spawn."""
    text = update.message.text
    user_id = f"tg_{update.effective_user.id}"
    await update.message.reply_text("👑 Thinking...")
    try:
        result = await call_king("spawn", {
            "task_description": text,
            "input_data": {"user_id": user_id}
        })

        decision = result.get("decision", "spawned")
        agent_spec = result.get("agent_spec") or {}
        agent_name = agent_spec.get("agent_name", "team" if decision == "team" else "unknown")
        output = result.get("output", {})
        confidence = output.get("confidence", "N/A")

        # Decision indicator
        decision_icons = {"reused": "♻️", "spawned": "🆕", "team": "👥"}
        icon = decision_icons.get(decision, "🤖")

        formatted = format_output(output)

        # Team mode shows team results
        if decision == "team":
            team_info = result.get("team_results", [])
            # Deduplicate team names
            team_names = list(dict.fromkeys([r.get("agent", "?") for r in team_info[:3]]))
            header = f"{icon} <b>Team</b>: {', '.join(team_names)}"
        else:
            header = f"{icon} <b>{escape_html(agent_name)}</b> ({decision})"

        await update.message.reply_text(
            f"{header}\n\n{formatted}",
            parse_mode="HTML"
        )
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)[:200]}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize bot on startup."""
    global ptb_app
    ptb_app = Application.builder().token(BOT_TOKEN).build()
    ptb_app.add_handler(CommandHandler("start", start_handler))
    ptb_app.add_handler(CommandHandler("code", code_handler))
    ptb_app.add_handler(CommandHandler("video", video_handler))
    ptb_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))
    await ptb_app.initialize()
    print(f"🚀 KING Telegram Bot ready. Gateway: {KING_GATEWAY}")
    yield
    await ptb_app.shutdown()


app = FastAPI(title="KING Telegram Bot", lifespan=lifespan)


@app.get("/health")
def health():
    return {"status": "ok", "service": "king-telegram"}


@app.post("/webhook")
async def webhook(request: Request):
    """Handle Telegram webhook."""
    data = await request.json()
    update = Update.de_json(data, ptb_app.bot)
    await ptb_app.process_update(update)
    return {"ok": True}

