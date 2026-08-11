from contextlib import asynccontextmanager

from fastapi import FastAPI

from database import engine
from models.base import Base
from routers import stocks


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        pass
    yield
    await engine.dispose()


app = FastAPI(
    title="NIR Backend",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(stocks.router)

@app.get("/health")
async def health_check():
    return {"status": "ok"}
