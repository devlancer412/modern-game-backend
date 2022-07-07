from __future__ import annotations
from typing import Callable
from app.__internal import Function
from fastapi import FastAPI, APIRouter, status, HTTPException, Depends, BackgroundTasks
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from operator import and_

from src.utils.auth import (
    generate_accesskey,
    get_hashed_password,
    create_access_token,
    create_refresh_token,
    validate_metamask_wallet,
    validate_phantom_wallet,
    verify_password
)
from src.schemas.user import EmailUserBase, AccessKey, WalletSign, WalletUserBase
from src.schemas.auth import TokenSchema
from src.models import SignMethod, User, UserAccessKey, UserBalance
from src.dependencies.database_deps import get_db_session


class AuthAPI(Function):

    def __init__(self, error: Callable):
        self.log.info("This is where the initialization code go")
        
    def Bootstrap(self, app: FastAPI):
        router = APIRouter(
          prefix='/auth',
          tags=['auth'],
          responses={404: {"description": "Not found"}},
        )
        
        @router.post('/signup/email', summary="Create new user",)
        async def create_user_by_email(data: EmailUserBase, session: Session = Depends(get_db_session)):
          # querying database to check if user already exist
          user = session.query(User).filter(and_(User.address == data.email, User.deleted == False)).first()
          if user is not None:
            raise HTTPException(
              status_code=status.HTTP_400_BAD_REQUEST,
              detail="User with this email already exist"
            )
          
          new_user = User()
          new_user.first_name = data.first_name
          new_user.last_name = data.last_name
          new_user.address = data.email
          new_user.sign_method = SignMethod.Email
          new_user.hashed_password = get_hashed_password(data.password)
          
          session.add(new_user)
          session.flush()
          session.refresh(new_user, attribute_names=['id'])
          data = {'user_id': new_user.id}
          new_access_key = UserAccessKey()
          new_access_key.is_pending = True
          new_access_key.key = generate_accesskey()
          new_access_key.user_id = new_user.id
          session.add(new_access_key)

          new_balance = UserBalance()
          new_balance.user_id = new_user.id
          
          session.add(new_balance)
          session.commit()
          return data

        @router.post('/signup/metamask', summary="Create new user",)
        async def create_user_by_email(data: WalletUserBase, session: Session = Depends(get_db_session)):
          # querying database to check if user already exist
          user = session.query(User).filter(and_(User.address == data.wallet, User.deleted == False)).first()
          if user is not None:
            raise HTTPException(
              status_code=status.HTTP_400_BAD_REQUEST,
              detail="User with this email already exist"
            )
          
          if validate_metamask_wallet(data.wallet, data.signature) == False:
            raise HTTPException(
              status_code=status.HTTP_400_BAD_REQUEST,
              detail="Invalid signature"
            )

          new_user = User()
          new_user.first_name = data.first_name
          new_user.last_name = data.last_name
          new_user.address = data.wallet
          new_user.sign_method = SignMethod.MWallet
          
          session.add(new_user)
          session.flush()
          session.refresh(new_user, attribute_names=['id'])
          data = {'user_id': new_user.id}
          new_access_key = UserAccessKey()
          new_access_key.is_pending = False
          new_access_key.key = generate_accesskey()
          new_access_key.user_id = new_user.id
          session.add(new_access_key)

          new_balance = UserBalance()
          new_balance.user_id = new_user.id
          
          session.add(new_balance)
          session.commit()
          return data

        @router.post('/signup/phantom', summary="Create new user",)
        async def create_user_by_email(data: WalletUserBase, session: Session = Depends(get_db_session)):
          # querying database to check if user already exist
          user = session.query(User).filter(and_(User.address == data.wallet, User.deleted == False)).first()
          if user is not None:
            raise HTTPException(
              status_code=status.HTTP_400_BAD_REQUEST,
              detail="User with this email already exist"
            )
          
          if validate_phantom_wallet(data.wallet, data.signature) == False:
            raise HTTPException(
              status_code=status.HTTP_400_BAD_REQUEST,
              detail="Invalid signature"
            )

          new_user = User()
          new_user.first_name = data.first_name
          new_user.last_name = data.last_name
          new_user.address = data.wallet
          new_user.sign_method = SignMethod.PWallet
          
          session.add(new_user)
          session.flush()
          session.refresh(new_user, attribute_names=['id'])
          data = {'user_id': new_user.id}
          new_access_key = UserAccessKey()
          new_access_key.is_pending = False
          new_access_key.key = generate_accesskey()
          new_access_key.user_id = new_user.id
          session.add(new_access_key)

          new_balance = UserBalance()
          new_balance.user_id = new_user.id
          
          session.add(new_balance)
          session.commit()
          return data

        @router.post('/login/email', summary="Create access and refresh tokens for user", response_model=TokenSchema)
        async def login(form_data: OAuth2PasswordRequestForm = Depends(), session: Session = Depends(get_db_session)):
          user: User = session.query(User).filter(and_(User.address == form_data.username, User.deleted == False)).first()
          if user is None:
            raise HTTPException(
              status_code=status.HTTP_400_BAD_REQUEST,
              detail="Incorrect email or password"
            )

          if not verify_password(form_data.password, user.hashed_password):
            raise HTTPException(
              status_code=status.HTTP_400_BAD_REQUEST,
              detail="Incorrect email or password"
            )

          if user.is_pending:
            # send_email_background(background_tasks, 'Hello your reaching out to Modern time', user.email, {'name': user.first_name + user.last_name, 'code': user.access_key.key})
            raise HTTPException(
              status_code=status.HTTP_403_FORBIDDEN,
              detail="You need to verify email"
            )
          
          return {
            "access_token": create_access_token(user.id),
            "refresh_token": create_refresh_token(user.id),
          }
      
        @router.post('/login/metamask', summary="Create access and refresh tokens for user", response_model=TokenSchema)
        async def login(form_data: WalletSign = Depends(), session: Session = Depends(get_db_session)):
          user: User = session.query(User).filter(and_(User.address == form_data.wallet, User.deleted == False)).first()
          if user is None:
            raise HTTPException(
              status_code=status.HTTP_400_BAD_REQUEST,
              detail="Incorrect email or password"
            )

          if not validate_metamask_wallet(form_data.wallet, form_data.signature):
            raise HTTPException(
              status_code=status.HTTP_400_BAD_REQUEST,
              detail="Incorrect email or password"
            )
            
          if user.is_pending:
            # send_email_background(background_tasks, 'Hello your reaching out to Modern time', user.email, {'name': user.first_name + user.last_name, 'code': user.access_key.key})
            raise HTTPException(
              status_code=status.HTTP_403_FORBIDDEN,
              detail="You need to verify email"
            )
          
          return {
            "access_token": create_access_token(user.id),
            "refresh_token": create_refresh_token(user.id),
          }
         
        @router.post('/login/phantom', summary="Create access and refresh tokens for user", response_model=TokenSchema)
        async def login(form_data: WalletSign = Depends(), session: Session = Depends(get_db_session)):
          user: User = session.query(User).filter(and_(User.address == form_data.wallet, User.deleted == False)).first()
          if user is None:
            raise HTTPException(
              status_code=status.HTTP_400_BAD_REQUEST,
              detail="Incorrect email or password"
            )

          if not validate_phantom_wallet(form_data.wallet, form_data.signature):
            raise HTTPException(
              status_code=status.HTTP_400_BAD_REQUEST,
              detail="Incorrect email or password"
            )
            
          if user.is_pending:
            # send_email_background(background_tasks, 'Hello your reaching out to Modern time', user.email, {'name': user.first_name + user.last_name, 'code': user.access_key.key})
            raise HTTPException(
              status_code=status.HTTP_403_FORBIDDEN,
              detail="You need to verify email"
            )
          
          return {
            "access_token": create_access_token(user.id),
            "refresh_token": create_refresh_token(user.id),
          }

        app.include_router(router)