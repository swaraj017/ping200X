from fastapi import FastAPI
from api.routes.monitors import router as monitors_router

app = FastAPI(title="Ping200X")


@app.get("/health")
def health():
    return {"status": "ok"}

app.include_router(monitors_router)