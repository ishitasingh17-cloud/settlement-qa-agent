"""
server/main.py

FastAPI Application Entrypoint for PS-8 Settlement Q&A Agent.
Exposes the Backend Investigation API with CORS and standardized error handlers.
"""

import logging
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from server.api.routes import router as api_router
from server.config.settings import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("settlement_qa_agent")

app = FastAPI(
    title="PS-8 Settlement Q&A Agent API",
    description="Deterministic fintech reconciliation and AI investigation assistant for payment platform support.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from starlette.exceptions import HTTPException as StarletteHTTPException

# Standardized Exception Handling
@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    if isinstance(exc.detail, dict):
        return JSONResponse(
            status_code=exc.status_code,
            content=exc.detail,
        )
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": "HTTP_ERROR", "message": str(exc.detail)},
    )


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled server exception on %s", request.url.path)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"error": "INTERNAL_SERVER_ERROR", "message": "An unexpected internal server error occurred."},
    )

app.include_router(api_router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server.main:app", host=settings.HOST, port=settings.PORT, reload=True)
