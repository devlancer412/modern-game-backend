from email.policy import default
from sqlalchemy import Column, Integer, String, TIMESTAMP, Boolean, text, ForeignKey, Enum as SAEnum, Float
from sqlalchemy.orm import relationship
from src.database import Base
from enum import Enum

class RoleEnum(str, Enum):
  Dev = "DEV"
  Admin = "ADMIN"
  User = "USER"

class SignMethod(str, Enum):
  Email = "EMAIL"
  MWallet = "METAMASK_WALLET"
  PWallet = "PHANTOM_WALLET"

class User(Base):
  __tablename__ = "user"
  id = Column(Integer, primary_key=True)
  first_name = Column(String(512), nullable=False, default="Unnamed")
  last_name = Column(String(512), nullable=True)
  address = Column(String(512), nullable=True)
  sign_method = Column(SAEnum(SignMethod), nullable=False, default=SignMethod.Email)
  hashed_password = Column(String(512), nullable=True)
  role = Column(SAEnum(RoleEnum), nullable=False, default=RoleEnum.User)
  avatar_url = Column(String(1024), nullable=True)
  
  created_at = Column(TIMESTAMP, nullable=False, server_default=text("CURRENT_TIMESTAMP"))
  updated_at = Column(TIMESTAMP, nullable=True, server_default=text("CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP"))
  deleted = Column(Boolean, default=False)
  
  access_key = relationship('UserAccessKey', back_populates='user', uselist=False)
  balance = relationship('UserBalance', back_populates='user', uselist=False)
  histories = relationship('DWHistory', back_populates='user')
  
class UserAccessKey(Base):
  __tablename__ = "user_access_key"
  id = Column(Integer, primary_key=True)
  user_id = Column(Integer, ForeignKey('user.id'))
  is_pending = Column(Boolean, nullable=False, default=True)
  key = Column(String(6), nullable=False)
  updated_at = Column(TIMESTAMP, nullable=True, server_default=text("CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP"))
  
  user = relationship('User', back_populates='access_key')
  
  
class UserBalance(Base):
  __tablename__ = "user_balance"
  id = Column(Integer, primary_key=True)
  user_id = Column(Integer, ForeignKey('user.id'))
  balance = Column(Float, nullable=False, default=0)
  rollback = Column(Float, nullable=False, default=0)
  deposit_balance = Column(Float, nullable=False, default=0)
  withdraw_balance = Column(Float, nullable=False, default=0)
  
  user = relationship('User', back_populates='balance')

class Direct(str, Enum):
  Deposit = "DEPOSIT"
  Withdraw = "WITHDRAW"

class DWHistory(Base):
  __tablename__ = "dw_history"
  id = Column(Integer, primary_key=True)
  user_id = Column(Integer, ForeignKey('user.id'))
  direct = Column(SAEnum(Direct), nullable=False, default=Direct.Deposit)
  amount = Column(Integer, nullable=False, default=0)
  created_at = Column(TIMESTAMP, nullable=False, server_default=text("CURRENT_TIMESTAMP"))

  user = relationship('User', back_populates='histories')