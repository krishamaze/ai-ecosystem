from fastapi import FastAPI
from .api.tasks import router as tasks_router
from .api.meta import router as meta_router

app = FastAPI()

@app.get("/health")
def health():
    return {"status": "ok"}

app.include_router(tasks_router, prefix="/tasks")
app.include_router(meta_router, prefix="/meta")

