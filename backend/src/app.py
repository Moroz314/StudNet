from fastapi import FastAPI
from contextlib import asynccontextmanager
from .database.core import engine
from .database.models import Base
from .routers import register_routers
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import asyncio
from .tests.fill import generate_users
from .database.s3.base import create_s3_buckets


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    await create_s3_buckets()
    yield


app = FastAPI(lifespan=lifespan)

# CORS configuration - allow all origins for development
# In production, specify allowed origins explicitly
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

register_routers(app)

if __name__ == '__main__':
    uvicorn.run(
        app,
        host='0.0.0.0',
        port=8000,
    )
