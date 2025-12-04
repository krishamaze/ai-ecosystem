from fastapi import FastAPI
from api.tasks import router as tasks_router
from api.meta import router as meta_router
from api.decide import router as decide_router

app = FastAPI(title="KING Orchestrator", description="Strategic brain of the Kingdom")

@app.get("/health")
def health():
    return {"status": "ok", "service": "king-orchestrator"}

app.include_router(decide_router, prefix="/king", tags=["Strategic Decisions"])
app.include_router(tasks_router, prefix="/tasks", tags=["Tasks"])
app.include_router(meta_router, prefix="/meta", tags=["Meta Operations"])

