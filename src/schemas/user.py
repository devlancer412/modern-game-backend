from turtle import title
from xmlrpc.client import boolean
from pydantic import BaseModel, EmailStr, Field


class UserBase(BaseModel):
    first_name: str = Field(None, title="First name", max_length=512)
    last_name: str = Field(None, title="First name", max_length=512)


class EmailUserBase(BaseModel):
    email: EmailStr = Field(title="Email address")
    password: str = Field(title="Password")


class WalletUserBase(BaseModel):
    wallet: str = Field(title="Wallet address")
    signature: str = Field(title="Singnature")


class UserUpdateData(BaseModel):
    name: str = Field(title="User name")
    avatar: str = Field(title="Avatar url")
    isPrivacy: bool = (Field(title="Privacy mode"),)


class WalletData:
    user_id: int
    public_key: str
    private_key: str
    timestamp: int
    is_using: bool
