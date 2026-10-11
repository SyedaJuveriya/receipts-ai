
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.memories import router as memories_router

app = FastAPI(
    title="Receipts AI",
    version="0.1.0",
    description="Persistent memory for commitments and decisions.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    return {"status": "ok"}


app.include_router(memories_router)
