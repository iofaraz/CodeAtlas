
from fastapi import FastAPI

app = FastAPI(
    title="CodeAtlas API",
    description="Navigate the World of Technical Knowledge",
    version="1.0.0"
)


@app.get("/")
def home():
    return {
        "message": "Welcome to CodeAtlas!",
        "status": "API is running"
    }


@app.get("/health")
def health_check():
    return {
        "status": "healthy"
    }
