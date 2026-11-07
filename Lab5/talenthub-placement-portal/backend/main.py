import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import applications, auth, companies, coordinator, interviews, jobs, offers, students
from app.api.errors import domain_error_handler
from app.core.database import AsyncSessionLocal, init_db
from app.domain.exceptions import DomainError
from app.seed import seed_if_empty


@asynccontextmanager
async def lifespan(_: FastAPI):
    await init_db()
    async with AsyncSessionLocal() as db:
        await seed_if_empty(db)
    yield


app = FastAPI(title="TalentHub Placement Management API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("TALENTHUB_CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_exception_handler(DomainError, domain_error_handler)


@app.get("/")
def read_root():
    return {"message": "Welcome to TalentHub Campus Placement Management API"}


for module in (auth, students, companies, jobs, applications, interviews, offers, coordinator):
    app.include_router(module.router)
