"""
KING Background Task Queue - Async task execution with user notifications.

For long-running tasks (video creation, complex reviews, data analysis):
1. User gets immediate acknowledgment
2. Task runs in background
3. User notified on completion
"""
import os
import asyncio
import uuid
from datetime import datetime
from typing import Dict, Any, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum


class TaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class BackgroundTask:
    task_id: str
    user_id: str
    session_id: str
    task_type: str  # agent name
    input_data: Dict[str, Any]
    status: TaskStatus = TaskStatus.PENDING
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None


# In-memory task store (use Redis/DB in production)
_task_store: Dict[str, BackgroundTask] = {}
_running_tasks: Dict[str, asyncio.Task] = {}


async def enqueue_task(
    user_id: str,
    session_id: str,
    task_type: str,
    input_data: Dict[str, Any],
    executor: Callable
) -> str:
    """Enqueue a background task. Returns task_id for tracking."""
    task_id = str(uuid.uuid4())[:8]
    
    task = BackgroundTask(
        task_id=task_id,
        user_id=user_id,
        session_id=session_id,
        task_type=task_type,
        input_data=input_data
    )
    _task_store[task_id] = task
    
    # Start background execution
    async_task = asyncio.create_task(_execute_task(task, executor))
    _running_tasks[task_id] = async_task
    
    print(f"📋 Task queued: {task_id} ({task_type}) for user {user_id}")
    return task_id


async def _execute_task(task: BackgroundTask, executor: Callable):
    """Execute task in background and update status."""
    task.status = TaskStatus.RUNNING
    
    try:
        result = await executor(task.input_data)
        task.result = result
        task.status = TaskStatus.COMPLETED
        task.completed_at = datetime.utcnow()
        print(f"✅ Task completed: {task.task_id}")
        
        # Notify user (fire and forget)
        asyncio.create_task(_notify_user(task))
        
    except Exception as e:
        task.error = str(e)
        task.status = TaskStatus.FAILED
        task.completed_at = datetime.utcnow()
        print(f"❌ Task failed: {task.task_id} - {e}")
        
        # Notify user of failure
        asyncio.create_task(_notify_user(task))
    
    finally:
        _running_tasks.pop(task.task_id, None)


async def _notify_user(task: BackgroundTask):
    """Send notification to user via Telegram (or other channel)."""
    try:
        # Get bot token and send message
        bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
        if not bot_token:
            print(f"⚠️ No bot token for notification")
            return
        
        # Strip any whitespace/newlines from token
        bot_token = bot_token.strip()
        
        import httpx
        
        if task.status == TaskStatus.COMPLETED:
            # Format result for user
            result_preview = str(task.result)[:500] if task.result else "Done!"
            message = f"✅ Task completed!\n\n{result_preview}"
        else:
            message = f"❌ Task failed: {task.error}"
        
        # Extract chat_id from user_id (format: tg_CHATID)
        chat_id = task.user_id.replace("tg_", "") if task.user_id.startswith("tg_") else None
        if not chat_id:
            return
        
        async with httpx.AsyncClient() as client:
            await client.post(
                f"https://api.telegram.org/bot{bot_token}/sendMessage",
                json={"chat_id": chat_id, "text": message, "parse_mode": "Markdown"}
            )
        print(f"🔔 Notified user {task.user_id}")
    except Exception as e:
        print(f"⚠️ Notification failed: {e}")


def get_task(task_id: str) -> Optional[BackgroundTask]:
    """Get task by ID."""
    return _task_store.get(task_id)


def get_user_tasks(user_id: str, limit: int = 10) -> list:
    """Get recent tasks for a user."""
    user_tasks = [t for t in _task_store.values() if t.user_id == user_id]
    return sorted(user_tasks, key=lambda t: t.created_at, reverse=True)[:limit]


def get_pending_count(user_id: str) -> int:
    """Get count of pending/running tasks for user."""
    return sum(1 for t in _task_store.values() 
               if t.user_id == user_id and t.status in (TaskStatus.PENDING, TaskStatus.RUNNING))

