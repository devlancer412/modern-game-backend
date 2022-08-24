import asyncio
from operator import and_
import time
from threading import Thread
from tokenize import Number

from sqlalchemy.orm import Session
from config import cfg
from src.database import database
from src.models import DepositTransaction
from src.changenow_api.client import api_wrapper as cnio_api


async def handle_block(transaction: DepositTransaction):
    try:
        response = cnio_api(
            "TX_STATUS", id=transaction.transaction_id, api_key=cfg.CN_API_KEY
        )
        print(transaction.transaction_id, response["status"])
        transaction.status = 1
        return
    except Exception as ex:
        print(ex)
        return


async def eth_log_loop(session: Session, poll_interval: int):
    while True:
        transactions = list(
            session.query(DepositTransaction)
            .filter(DepositTransaction.status == False)
            .all()
        )
        for transaction in transactions:
            await handle_block(transaction)

        session.commit()
        session.flush()
        time.sleep(poll_interval)


def get_or_create_eventloop():
    try:
        return asyncio.get_event_loop()
    except RuntimeError as ex:
        if "There is no current event loop in thread" in str(ex):
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            return asyncio.get_event_loop()


def eth_transaction_filter_process():
    session = database.get_db_session()
    loop = get_or_create_eventloop()
    print("Changenow transaction listing started")
    try:
        loop.run_until_complete(asyncio.gather(eth_log_loop(session, 10)))
    finally:
        # close loop to free up system resources
        print("Listening terminated")
        loop.close()


def create_transacion_filter():
    worker = Thread(target=eth_transaction_filter_process, args=(), daemon=True)
    worker.start()
