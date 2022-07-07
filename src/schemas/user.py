from turtle import title
from pydantic import BaseModel, EmailStr, Field

class UserBase(BaseModel):
  first_name: str = Field(None, title='First name', max_length=512)
  last_name: str = Field(None, title='First name', max_length=512)
  
class EmailUserBase(UserBase):
  email: EmailStr = Field(title = 'Email address')
  password: str = Field(title = 'Password')
  
class WalletUserBase(UserBase):
  wallet: str = Field(title = 'Wallet address',  regex='0x[a-zA-Z0-9]{40}')
  signature: str = Field(title = 'Singnature', regex='0x[a-z0-9]{130}')
  
class WalletSign(BaseModel):
  wallet: str = Field(title = 'Wallet address',  regex='0x[a-zA-Z0-9]{40}')
  signature: str = Field(title = 'Singnature', regex='0x[a-z0-9]{130}')

class AccessKey(BaseModel):
  id: int
  is_pending: bool
  key: str

class User(UserBase):
  id: int
  deleted: bool
  access_key: AccessKey
  
  class Config:
    orm_mode = True