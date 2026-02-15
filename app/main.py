from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.auth.router import router as auth_router
from app.bot.router import router as bot_router
from app.config import settings
from app.database import create_users_table_if_not_exists


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings.print_env_summary()
    # Create DynamoDB table on startup if it doesn't exist
    create_users_table_if_not_exists()
    yield


app = FastAPI(
    title="SamniLabs API",
    version="0.1.0",
    lifespan=lifespan,
)

allowed_origins = (
    ["*"]
    # if settings.app_env == "development"
    # else [str(settings.frontend_url).rstrip("/")]
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router, prefix="/auth", tags=["auth"])
app.include_router(bot_router, prefix="/api", tags=["bot"])


@app.get("/")
def read_root():
    return {"message": "Hello from SamniLabs API"}


@app.get("/health")
def health():
    return {"message": "OK"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
