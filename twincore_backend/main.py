from fastapi import FastAPI

app = FastAPI(
    title="TwinCore API",
    description="Digital Twin Backend Service for Context Retrieval and User Representation",
    version="0.1.0"
)

@app.get("/")
async def root():
    """Root endpoint to verify API is running."""
    return {"status": "online", "service": "TwinCore API"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True) 