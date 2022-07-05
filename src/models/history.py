from email.policy import default
from sqlalchemy import Column, Integer, String, TIMESTAMP, Boolean, text, ForeignKey, Enum, Float
from sqlalchemy.orm import relationship
from src.database import Base

class Direct(str, Enum):
  Deposit = "DEPOSIT"
  Withdraw = "WITHDRAW"

class MomeyHistory(Base):
  __tablename__ = "user"
  id = Column(Integer, primary_key=True)
  user_id=ForeignKey('user.id')
  direct = Column(Direct, nullable=False, default=True)
  amount = 