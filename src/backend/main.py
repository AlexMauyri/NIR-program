import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from dependencies import engine
from models.base import Base
from routers import stocks, predictor, ml_models


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

origins = os.getenv("CORS_ALLOWED_ORIGINS", "http://localhost:8080").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(stocks.router)
app.include_router(predictor.router)
app.include_router(ml_models.router)

@app.get("/health")
async def health_check():
    return {"status": "ok"}
