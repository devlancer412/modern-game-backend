from email.policy import default
from sqlalchemy import Column, Integer, String, TIMESTAMP, Boolean, text, ForeignKey, Enum as SAEnum, Float
from sqlalchemy.orm import relationship
from src.database import Base
from enum import Enum

class RoleEnum(str, Enum):
  Dev = "DEV"
  Admin = "ADMIN"
  User = "USER"

class User(Base):
  __tablename__ = "user"
  id = Column(Integer, primary_key=True)
  first_name = Column(String(512), nullable=False, default="Unnamed")
  last_name = Column(String(512), nullable=True)
  email = Column(String(512), nullable=True)
  wallet = Column(String(64), nullable=True)
  hashed_password = Column(String(512), nullable=False)
  role = Column(SAEnum(RoleEnum), nullable=False, default=RoleEnum.User)
  avatar_url = Column(String(1024), nullable=True)
  
  created_at = Column(TIMESTAMP, nullable=False, server_default=text("CURRENT_TIMESTAMP"))
  updated_at = Column(TIMESTAMP, nullable=True, server_default=text("CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP"))
  deleted = Column(Boolean, default=False)
  
  access_key = relationship('UserAccessKey', back_populates='user')
  balance = relationship('UserBalance', back_populates='user')
  histories = relationship('DWHistroy', back_populates='user')
  
class UserAccessKey(Base):
  __tablename__ = "user_access_key"
  id = Column(Integer, primary_key=True)
  user_id = Column(Integer, ForeignKey('user.id'))
  is_pending = Column(Boolean, nullable=False, default=True)
  key = Column(String(6), nullable=False)
  
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