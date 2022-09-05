from fastapi import status, HTTPException, Depends
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from operator import and_
from datetime import datetime
from jose import jwt
from pydantic import ValidationError
from .database_deps import get_db_session
from ..models import User

from ..utils.auth import ALGORITHM, JWT_REFRESH_SECRET_KEY, JWT_SECRET_KEY
from ..schemas.auth import TokenPayload

email_oauth = OAuth2PasswordBearer(
    tokenUrl="/api/v1/auth/login/email",
    # tokenUrl="/auth/login/email",
    scheme_name="JWT",
)


async def get_current_user_from_oauth(token: str = Depends(email_oauth)) -> int:
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[ALGORITHM])
        token_data = TokenPayload(**payload)

        if datetime.fromtimestamp(token_data.exp) < datetime.now():
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token expired",
                headers={"WWW-Authenticate": "Bearer"},
            )
    except (jwt.JWTError, ValidationError):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return token_data


async def get_current_user_from_refresh_token(token: str = Depends(email_oauth)) -> int:
    try:
        payload = jwt.decode(token, JWT_REFRESH_SECRET_KEY, algorithms=[ALGORITHM])
        token_data = TokenPayload(**payload)

        if datetime.fromtimestamp(token_data.exp) < datetime.now():
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token expired",
                headers={"WWW-Authenticate": "Bearer"},
            )
    except (jwt.JWTError, ValidationError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return token_data
