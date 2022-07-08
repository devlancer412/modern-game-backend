from ..database import Database

database = Database()
engine = database.get_db_connection()

# Dependencies
async def get_db_session():
  session = database.get_db_session()
  try:
    yield session
  finally:
    session.commit()
    session.close()