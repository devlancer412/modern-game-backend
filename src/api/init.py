from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware

from app.__internal import Function
from src.database import Base, Database
from config import cfg


class Init(Function):
    def __init__(self, error):
        if cfg.has_unset():
            error(f"Cannot start with unset variables: {cfg.has_unset()}")

    def Bootstrap(self, app: FastAPI):
        app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
        app.add_middleware(SessionMiddleware, secret_key=cfg.JWT_SECRET_KEY)

        database = Database()
        engine = database.get_db_connection()
        database.get_db_session()

        Base.metadata.create_all(bind=engine, checkfirst=True)
