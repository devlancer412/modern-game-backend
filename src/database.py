from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base

from config import cfg

MYSQL_URL = "mysql+pymysql://{}:{}@{}:{}/{}?charset=utf8".format(cfg.DB_USER, cfg.DB_PASSWORD, cfg.DB_HOST, cfg.DB_PORT, cfg.DATABASE) 
POOL_SIZE = 20
POOL_RECYCLE = 3600
POOL_TIMEOUT = 15
MAX_OVERFLOW = 2
CONNECT_TIMEOUT = 60

class Database():
  def __init__(self) -> None:
    self.connection_is_active = False
    self.engine = None

  def get_db_connection(self):
    if self.connection_is_active == False:
      connect_args = {"connect_timeout":CONNECT_TIMEOUT}
      try:
        self.engine = create_engine(MYSQL_URL, pool_size=POOL_SIZE, pool_recycle=POOL_RECYCLE,
        pool_timeout=POOL_TIMEOUT, max_overflow=MAX_OVERFLOW, connect_args=connect_args)
        return self.engine
      except Exception as ex:
        print("Error connecting to DB : ", ex)
    return self.engine

  def get_db_session(self):
    try:
      Session = sessionmaker(bind=self.engine)
      session = Session()
      return session
    except Exception as ex:
      print("Error getting DB session : ", ex)
      return None
    
Base = declarative_base()