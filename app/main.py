import logging

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError

from app.routes.employees import router as employees_router

logger = logging.getLogger(__name__)

app = FastAPI()
app.include_router(employees_router, prefix="/api/v1")


@app.exception_handler(SQLAlchemyError)
async def sqlalchemy_error_handler(request: Request, exc: SQLAlchemyError):
    logger.exception("Database error handling request %s", request.url)
    return JSONResponse(
        status_code=500,
        content={"error": "Unable to retrieve employees"},
    )
