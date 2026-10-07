from fastapi import FastAPI

app = FastAPI(title="Receipts AI")

@app.get("/health")
def health():
    return {"status": "ok"}
