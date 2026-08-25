from fastapi import FastAPI
from pydantic import BaseModel
from fastapi.responses import FileResponse
from pathlib import Path

from .agent import chat
from google.genai.errors import ClientError, ServerError


app = FastAPI(
    title="Trendly Customer Support Agent",
    version="1.0.0",
)


class ChatRequest(BaseModel):
    conversation_id: str
    message: str
    customer_id: str | None = None


class ChatResponse(BaseModel):
    response: str


@app.get("/")
def home():
    return FileResponse(
        Path(__file__).parent / "static" / "index.html"
    )


@app.get("/health")
def health():
    return {
        "status": "ok"
    }

@app.post("/chat", response_model=ChatResponse)
def chat_endpoint(request: ChatRequest):

    try:
        response = chat(
            conversation_id=request.conversation_id,
            message=request.message,
            customer_id=request.customer_id,
        )

        return ChatResponse(
            response=response
        )

    except (ClientError, ServerError) as e:

        status_code = getattr(e, "code", None)

        if status_code == 429:
            return ChatResponse(
                response=(
                    "The AI service has temporarily reached "
                    "its usage limit. Please try again shortly."
                )
            )

        if status_code == 503:
            return ChatResponse(
                response=(
                    "The AI service is temporarily busy. "
                    "Please try again in a moment."
                )
            )

        raise

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host="127.0.0.1",
        port=8000,
        reload=True,
    )