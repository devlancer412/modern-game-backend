from datetime import datetime, timedelta
from celery import Celery
from celery.utils.log import get_task_logger
from src.database import database, Database
from src.models import Transaction
from src.changenow_api.client import api_wrapper as cnio_api
from config import cfg

celery = Celery(
    __name__, broker="redis://127.0.0.1:6379/0", backend="redis://127.0.0.1:6379/0"
)

database = Database()
engine = database.get_db_connection()
session = database.get_db_session()

celery_log = get_task_logger(__name__)


@celery.task
async def dispatch_transaction(id: str):
    transaction: Transaction = (
        session.query(Transaction).filter(Transaction.transaction_id == id).one()
    )
    endTime = datetime.strptime(
        transaction.created_at, "%Y-%m-%d %H:%M:%S"
    ) + timedelta(days=1)
    while transaction.status != "finished":
        try:
            response = cnio_api(
                "TX_STATUS", id=transaction.transaction_id, api_key=cfg.CN_API_KEY
            )
            celery_log.info(transaction.transaction_id, response["status"])
            transaction.status = response["status"]

            if datetime.now() > endTime:
                break
        except Exception as ex:
            celery_log.error(ex)
