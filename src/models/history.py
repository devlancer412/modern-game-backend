from email.policy import default
from sqlalchemy import Column, Integer, String, TIMESTAMP, Boolean, text, ForeignKey, Enum as SAEnum, Float
from sqlalchemy.orm import relationship
from src.database import Base
from enum import Enum

class Direct(str, Enum):
  Deposit = "DEPOSIT"
  Withdraw = "WITHDRAW"

class DWHistory(Base):
  __tablename__ = "dw_history"
  id = Column(Integer, primary_key=True)
  user_id=ForeignKey('user.id')
  direct = Column(SAEnum(Direct), nullable=False, default=Direct.Deposit)
  amount = Column(Integer, nullable=False, default=0)

  user = relationship('User', back_populates='histories')