from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from app.schemas import HealthResponse, EchoRequest, EchoResponse
from app.config import settings

app = FastAPI(
    title="AI Resume Generator & Smart Apply API",
    version="1.0.0",
    description="Backend API services for resume extraction, tailoring, job search, and auto-applying."
)

# CORS middleware configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict this to the frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """
    Health check endpoint to verify backend status.
    """
    return HealthResponse(status="ok")

@app.post("/echo", response_model=EchoResponse)
async def echo_message(payload: EchoRequest):
    """
    Echo endpoint to verify API data serialization.
    """
    return EchoResponse(
        message=payload.message,
        status="success"
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=settings.BACKEND_PORT,
        reload=True
    )
