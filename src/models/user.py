from email.policy import default
from sqlalchemy import Column, Integer, String, TIMESTAMP, Boolean, text, ForeignKey, Enum
from sqlalchemy.orm import relationship
from src.database import Base

from config import cfg

class RoleEnum(Enum):
  Dev = "DEV"
  Admin = "ADMIN"
  User = "USER"

class User(Base):
  __tablename__ = "user"
  id = Column(Integer, primary_key=True)
  first_name = Column(String(512), nullable=False)
  last_name = Column(String(512), nullable=False)
  email = Column(String(512), nullable=True)
  wallet = Column(String(64), nullable=True)
  hashed_password = Column(String(512), nullable=False)
  role = Column(RoleEnum, nullable=False, default=RoleEnum.User)
  avatar = Column(String, nullable=False, default=cfg.DEFAULT_AVATAR)
  
  created_at = Column(TIMESTAMP, nullable=False, server_default=text("CURRENT_TIMESTAMP"))
  updated_at = Column(TIMESTAMP, nullable=True, server_default=text("CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP"))
  deleted = Column(Boolean, default=False)
  
  access_key = relationship('UserAccessKey', back_populates='user')
  
class UserAccessKey(Base):
  __tablename__ = "user_access_key"
  id = Column(Integer, primary_key=True)
  user_id = Column(Integer, ForeignKey('user.id'))
  is_pending = Column(Boolean, nullable=False, default=True)
  key = Column(String(6), nullable=False)
  
  user = relationship('User', back_populates='access_key')