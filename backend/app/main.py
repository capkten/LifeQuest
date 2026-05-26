from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.database import engine, Base
from app.api import auth, users, notes, todos, shop, backpack

# Create database tables
Base.metadata.create_all(bind=engine)

app = FastAPI(title="LifeQuest", version="1.0.0")

# Mount static files directory for uploaded files
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(notes.router)
app.include_router(todos.router)
app.include_router(shop.router)
app.include_router(backpack.router)


@app.get("/")
def root():
    return {"message": "Welcome to LifeQuest API"}
