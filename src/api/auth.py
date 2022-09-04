from __future__ import annotations
import json
from typing import Callable
from app.__internal import Function
from fastapi import (
    FastAPI,
    APIRouter,
    status,
    HTTPException,
    Depends,
)
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from operator import and_

import requests
from src.dependencies.auth_deps import (
    get_current_user_from_oauth,
    get_current_user_from_refresh_token,
)

from src.utils.auth import (
    generate_accesskey,
    get_hashed_password,
    create_access_token,
    create_refresh_token,
    get_signer,
    validate_phantom_wallet,
    verify_password,
)
from src.schemas.user import EmailUserBase, WalletUserBase
from src.schemas.auth import TokenPayload, TokenSchema
from src.models import Avatar, SignMethod, User, UserAccessKey
from src.dependencies.database_deps import get_db_session

from config import cfg
from src.utils.web3 import compare_eth_address

scopes = [
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/userinfo.profile",
]


class AuthAPI(Function):
    def __init__(self, error: Callable):
        self.log.info("This is where the initialization code go")

    def Bootstrap(self, app: FastAPI):
        router = APIRouter(
            prefix="/auth",
            tags=["auth"],
            responses={404: {"description": "Not found"}},
        )

        @router.post(
            "/signup/email",
            summary="Create new user",
        )
        async def create_user_by_email(
            data: EmailUserBase, session: Session = Depends(get_db_session)
        ):
            # querying database to check if user already exist
            user = (
                session.query(User)
                .filter(and_(User.address == data.email, User.deleted == False))
                .first()
            )
            if user is not None:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="User with this email already exist",
                )

            new_user = User()
            new_user.address = data.email
            new_user.sign_method = SignMethod.Email
            new_user.hashed_password = get_hashed_password(data.password)

            session.add(new_user)
            session.flush()
            session.refresh(new_user, attribute_names=["id"])
            data = {"user_id": new_user.id}
            new_access_key = UserAccessKey()
            new_access_key.is_pending = True
            new_access_key.key = generate_accesskey()
            new_access_key.user_id = new_user.id
            session.add(new_access_key)

            session.commit()
            return data

        @router.post(
            "/signup/metamask",
            summary="Create new user",
        )
        async def create_user_by_metamask(
            data: WalletUserBase, session: Session = Depends(get_db_session)
        ):
            # querying database to check if user already exist
            user = (
                session.query(User)
                .filter(and_(User.address == data.wallet, User.deleted == False))
                .first()
            )
            if user is not None:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="User with this wallet already exist",
                )

            if not compare_eth_address(
                get_signer("Modern Game", data.signature), data.wallet
            ):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid signature"
                )

            new_user = User()
            new_user.address = data.wallet
            new_user.sign_method = SignMethod.MWallet

            session.add(new_user)
            session.flush()
            session.refresh(new_user, attribute_names=["id"])
            new_access_key = UserAccessKey()
            new_access_key.is_pending = False
            new_access_key.key = generate_accesskey()
            new_access_key.user_id = new_user.id
            session.add(new_access_key)

            session.commit()

            return {
                "access_token": create_access_token(new_user.id),
                "refresh_token": create_refresh_token(new_user.id),
            }

        @router.post(
            "/signup/phantom",
            summary="Create new user",
        )
        async def create_user_by_phantom(
            data: WalletUserBase, session: Session = Depends(get_db_session)
        ):
            # querying database to check if user already exist
            user = (
                session.query(User)
                .filter(and_(User.address == data.wallet, User.deleted == False))
                .first()
            )
            if user is not None:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="User with this wallet already exist",
                )

            if validate_phantom_wallet(data.wallet, data.signature) == False:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid signature"
                )

            new_user = User()
            new_user.address = data.wallet
            new_user.sign_method = SignMethod.PWallet

            session.add(new_user)
            session.flush()
            session.refresh(new_user, attribute_names=["id"])
            new_access_key = UserAccessKey()
            new_access_key.is_pending = False
            new_access_key.key = generate_accesskey()
            new_access_key.user_id = new_user.id
            session.add(new_access_key)

            session.commit()

            return {
                "access_token": create_access_token(new_user.id),
                "refresh_token": create_refresh_token(new_user.id),
            }

        @router.post(
            "/login/email",
            summary="Create access and refresh tokens for user",
            response_model=TokenSchema,
        )
        async def login_with_email(
            form_data: OAuth2PasswordRequestForm = Depends(),
            session: Session = Depends(get_db_session),
        ):
            user: User = (
                session.query(User)
                .filter(and_(User.address == form_data.username, User.deleted == False))
                .first()
            )
            if user is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Can't find such user",
                )

            if not verify_password(form_data.password, user.hashed_password):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Incorrect email or password",
                )

            return {
                "access_token": create_access_token(user.id),
                "refresh_token": create_refresh_token(user.id),
            }

        @router.post(
            "/login/metamask",
            summary="Create access and refresh tokens for user",
            response_model=TokenSchema,
        )
        async def login_with_metamask(
            data: WalletUserBase,
            session: Session = Depends(get_db_session),
        ):
            user: User = (
                session.query(User)
                .filter(and_(User.address == data.wallet, User.deleted == False))
                .first()
            )
            if user is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Can't find such user",
                )

            if not compare_eth_address(
                get_signer("Modern Game", data.signature), data.wallet
            ):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid signature"
                )

            return {
                "access_token": create_access_token(user.id),
                "refresh_token": create_refresh_token(user.id),
            }

        @router.post(
            "/login/phantom",
            summary="Create access and refresh tokens for user",
            response_model=TokenSchema,
        )
        async def login_with_phantom(
            form_data: WalletUserBase,
            session: Session = Depends(get_db_session),
        ):
            user: User = (
                session.query(User)
                .filter(and_(User.address == form_data.wallet, User.deleted == False))
                .first()
            )
            if user is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Can't find such user",
                )

            if not validate_phantom_wallet(form_data.wallet, form_data.signature):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Incorrect email or password",
                )

            return {
                "access_token": create_access_token(user.id),
                "refresh_token": create_refresh_token(user.id),
            }

        @router.post(
            "/signup/google",
            summary="Create a account with google account",
            response_model=TokenSchema,
        )
        async def signup_with_google(
            access_token: str, session: Session = Depends(get_db_session)
        ):
            url = (
                "https://www.googleapis.com/oauth2/v3/userinfo?access_token={}".format(
                    access_token
                )
            )
            response = requests.get(url)

            if response.status_code != 200:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invaild access token",
                )

            user_data = json.loads(response.content.decode("utf-8"))

            user = (
                session.query(User)
                .filter(and_(User.address == user_data["email"], User.deleted == False))
                .first()
            )

            if user is not None:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="User with this account already exist",
                )

            new_user = User()
            new_user.address = user_data["email"]
            new_user.name = user_data["name"]
            new_user.sign_method = SignMethod.Google

            session.add(new_user)
            session.flush()
            session.refresh(new_user, attribute_names=["id"])

            new_access_key = UserAccessKey()
            new_access_key.is_pending = False
            new_access_key.key = generate_accesskey()
            new_access_key.user_id = new_user.id
            session.add(new_access_key)

            avatar = Avatar()
            avatar.owner_id = new_user.id
            avatar.url = user_data["picture"]

            session.add(avatar)
            session.flush()
            session.refresh(avatar, attribute_names=["id"])

            new_user.avatar_id = avatar.id

            session.commit()

            return {
                "access_token": create_access_token(new_user.id),
                "refresh_token": create_refresh_token(new_user.id),
            }

        @router.post(
            "/login/google",
            summary="Create access and refresh tokens with google account",
            response_model=TokenSchema,
        )
        async def login_with_google(
            access_token: str, session: Session = Depends(get_db_session)
        ):
            try:
                url = "https://www.googleapis.com/oauth2/v3/userinfo?access_token={}".format(
                    access_token
                )
                response = requests.get(url)

                if response.status_code != 200:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Invaild access token",
                    )

                user_data = json.loads(response.content.decode("utf-8"))

                user: User = (
                    session.query(User)
                    .filter(
                        and_(User.address == user_data["email"], User.deleted == False)
                    )
                    .first()
                )
                if user is None:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail="You need to sign up",
                    )

                user.is_pending = False
                session.commit()

                return {
                    "access_token": create_access_token(user.id),
                    "refresh_token": create_refresh_token(user.id),
                }

            except Exception as ex:
                print(ex)
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST, detail=str(ex)
                )

        @router.get(
            "/refresh",
            summary="Create new access and refresh tokens with refresh token",
            response_model=TokenSchema,
        )
        async def refresh_token(
            payload: TokenPayload = Depends(get_current_user_from_refresh_token),
        ):
            return {
                "access_token": create_access_token(payload.sub),
                "refresh_token": create_refresh_token(payload.sub),
            }

        @router.post("/confirm", summary="Confirm user")
        async def confirm(
            code: str,
            payload: TokenPayload = Depends(get_current_user_from_oauth),
            session: Session = Depends(get_db_session),
        ):
            user: User = (
                session.query(User)
                .filter(and_(User.id == payload.sub, User.deleted == False))
                .one()
            )

            if user is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Can't find such user",
                )

            if user.access_key.key != code:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invaild verification code",
                )

            return True

        app.include_router(router)
