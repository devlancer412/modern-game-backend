from __future__ import annotations
from operator import and_
from typing import Callable

from app.__internal import Function
from fastapi import FastAPI, APIRouter, status, HTTPException, Depends
from sqlalchemy.orm import Session
from src.dependencies.auth_deps import get_current_user_from_oauth
from src.dependencies.database_deps import get_db_session
from src.models import User, UserBalance
from src.schemas.auth import TokenPayload


class UserAPI(Function):

    def __init__(self, error: Callable):
        self.log.info("This is where the initialization code go")
        
    def Bootstrap(self, app: FastAPI):
        router = APIRouter(
          prefix='/user',
          tags=['user'],
          responses={404: {"description": "Not found"}},
        )
        
        @router.get('/', summary='Get user data')
        async def get_user_data(payload: TokenPayload = Depends(get_current_user_from_oauth), session: Session = Depends(get_db_session)):
          user: User = session.query(User).filter(and_(User.id == payload.sub, User.deleted == False)).one()

          return {
            "user_name": user.first_name + " " + user.last_name,
            "address": user.address,
            "avatar": user.avatar_url,
            "sign_method": user.sign_method,
            "balance": user.balance,
            "rollback": user.rollback
          }

        app.include_router(router)