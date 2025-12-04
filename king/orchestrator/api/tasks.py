from fastapi import APIRouter
from pydantic import BaseModel
from agents.agent_runner import AgentRunner
from services.supabase_client import supabase

router = APIRouter()
runner = AgentRunner()


class CreateTaskRequest(BaseModel):
    title: str


@router.post("/create")
def create_task(request: CreateTaskRequest):
    """Create a new task and return its ID."""
    data = supabase.table("tasks").insert({"title": request.title}).execute()
    return {"task_id": data.data[0]["id"]}


@router.post("/planner/{task_id}")
def planner_run(task_id: str, input_data: dict):
    """Run video planner agent for a specific task, store results in DB."""
    response = runner.run("video_planner", input_data)

    # Store agent run trace
    supabase.table("agent_runs").insert({
        "task_id": task_id,
        "agent_role": "video_planner",
        "input_json": input_data,
        "output_json": response.output,
        "confidence": response.confidence
    }).execute()

    # Store latest context (if successful)
    if response.output and response.output.get("known_context"):
        # Get current version
        existing = supabase.table("task_context") \
            .select("version") \
            .eq("task_id", task_id) \
            .eq("is_active", True) \
            .order("version", desc=True) \
            .limit(1) \
            .execute()

        next_version = 1
        if existing.data:
            # Deactivate old version
            supabase.table("task_context") \
                .update({"is_active": False}) \
                .eq("task_id", task_id) \
                .eq("is_active", True) \
                .execute()
            next_version = existing.data[0]["version"] + 1

        supabase.table("task_context").insert({
            "task_id": task_id,
            "context_json": response.output.get("known_context", {}),
            "version": next_version,
            "is_active": True
        }).execute()

    return response.dict()


@router.get("/")
def list_tasks():
    """List all tasks with latest context."""
    tasks = supabase.table("tasks").select("*").order("created_at", desc=True).execute()
    return {"tasks": tasks.data}


@router.get("/{task_id}")
def get_task(task_id: str):
    """Get task with latest context and last planner question."""
    task = supabase.table("tasks").select("*").eq("id", task_id).single().execute()
    context = supabase.table("task_context") \
        .select("*") \
        .eq("task_id", task_id) \
        .eq("is_active", True) \
        .order("created_at", desc=True) \
        .limit(1) \
        .execute()

    # Get last agent run for planner question
    last_run = supabase.table("agent_runs") \
        .select("*") \
        .eq("task_id", task_id) \
        .order("created_at", desc=True) \
        .limit(1) \
        .execute()

    return {
        "task": task.data,
        "context": context.data[0] if context.data else None,
        "last_run": last_run.data[0] if last_run.data else None
    }


@router.get("/{task_id}/runs")
def get_task_runs(task_id: str):
    """Get all agent runs for a task."""
    runs = supabase.table("agent_runs") \
        .select("*") \
        .eq("task_id", task_id) \
        .order("created_at", desc=False) \
        .execute()

    return {"runs": runs.data}

