from fastapi import FastAPI

from app.api.memories import router as memories_router

app = FastAPI(
    title="Receipts AI",
    version="0.1.0",
    description="Persistent memory for commitments and decisions.",
)


@app.get("/health")
def health():
    return {"status": "ok"}


app.include_router(memories_router)