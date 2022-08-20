from passlib.context import CryptContext
import os
from datetime import datetime, timedelta
from typing import Union, Any
from jose import jwt
from random import choices
import string

from web3 import Web3
from web3.auto import w3
from eth_account.messages import defunct_hash_message
from base58 import b58decode, b58encode
from binascii import unhexlify
from nacl.signing import VerifyKey, SigningKey
from solana.publickey import PublicKey

from config import cfg

ACCESS_TOKEN_EXPIRE_MINUTES = 30  # 30 minutes
REFRESH_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 7 days
ALGORITHM = "HS256"
JWT_SECRET_KEY = cfg.JWT_SECRET_KEY
JWT_REFRESH_SECRET_KEY = cfg.JWT_REFRESH_SECRET_KEY

password_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def get_hashed_password(password: str) -> str:
    return password_context.hash(password)


def verify_password(password: str, hashed_pass: str) -> bool:
    return password_context.verify(password, hashed_pass)


def create_access_token(subject: Union[str, Any], expires_delta: int = None) -> str:
    if expires_delta is not None:
        expires_delta = datetime.utcnow() + expires_delta
    else:
        expires_delta = datetime.utcnow() + timedelta(
            minutes=ACCESS_TOKEN_EXPIRE_MINUTES
        )

    to_encode = {"exp": expires_delta, "sub": str(subject)}
    encoded_jwt = jwt.encode(to_encode, JWT_SECRET_KEY, ALGORITHM)
    return encoded_jwt


def create_refresh_token(subject: Union[str, Any], expires_delta: int = None) -> str:
    if expires_delta is not None:
        expires_delta = datetime.utcnow() + expires_delta
    else:
        expires_delta = datetime.utcnow() + timedelta(
            minutes=REFRESH_TOKEN_EXPIRE_MINUTES
        )

    to_encode = {"exp": expires_delta, "sub": str(subject)}
    encoded_jwt = jwt.encode(to_encode, JWT_REFRESH_SECRET_KEY, ALGORITHM)
    return encoded_jwt


def generate_accesskey() -> str:
    chars = string.ascii_uppercase + string.digits
    return "".join(choices(chars)[0] for _ in range(6))


def get_signer(message: str, signature: str) -> bool:
    try:
        message_hash = defunct_hash_message(text=message)
        signedAddress = w3.eth.account.recoverHash(message_hash, signature=signature)
        return signedAddress
    except Exception as ex:
        print(ex)
        return False


def validate_phantom_wallet(address: str, signature: str) -> bool:
    pubkey = bytes(PublicKey(address))
    msg = bytes("Modern Game", "utf8")
    signed = bytes(signature, "utf8")

    try:
        return VerifyKey(pubkey).verify(smessage=msg, signature=b58decode(signed))
    except Exception as ex:
        print(ex)
        return False
