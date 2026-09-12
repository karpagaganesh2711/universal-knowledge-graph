from fastapi import FastAPI

app = FastAPI(
    title="Universal Knowledge Graph Generator",
    description="An AI-powered system that converts documents into interactive knowledge graphs.",
    version="0.1.0"
)


@app.get("/")
def root():
    return {
        "message": "Universal Knowledge Graph Generator API is running!"
    }


@app.get("/health")
def health():
    return {
        "status": "healthy"
    }