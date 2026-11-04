from fastapi import FastAPI

from app.schemas import HealthResponse
from app.paypal.webhooks import router as paypal_webhooks

app = FastAPI(title="Resolve API", version="0.1.0")
app.include_router(paypal_webhooks)


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(status="ok")
