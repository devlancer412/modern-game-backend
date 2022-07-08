from __future__ import annotations
from operator import and_
from typing import Callable
from eth_abi import decode_abi

from eth_utils import to_wei
from web3 import Web3
from web3.auto import w3

from app.__internal import Function
from fastapi import FastAPI, APIRouter, Query, status, HTTPException, Depends
from sqlalchemy.orm import Session
from src.dependencies.auth_deps import get_current_user_from_oauth
from src.dependencies.database_deps import get_db_session
from src.models import DWHistory, Direct, User, UserBalance
from src.schemas.auth import TokenPayload
from uniswap import Uniswap

from config import cfg
from src.utils.web3 import compare_eth_address, get_current_gas_price, get_transaction_eth_value, get_transaction_token_value, wait_transaction_receipt

eth = "0x0000000000000000000000000000000000000000"
usdt = cfg.ETH_USDT_ADDRESS

class UserAPI(Function):

    def __init__(self, error: Callable):
        self.log.info("Swap api initailized")
        self.uniswap = Uniswap(address=cfg.ETH_TREASURY_ADDRESS, private_key=cfg.ETH_TREASURY_PRIVATE_KEY, version=2, provider=cfg.ETH_RPC_URL)

    def Bootstrap(self, app: FastAPI):
        router = APIRouter(
          prefix='/user',
          tags=['user'],
          responses={404: {"description": "Not found"}},
        )

        @router.get('/', summary='Get user data')
        async def get_user_data(payload: TokenPayload = Depends(get_current_user_from_oauth), session: Session = Depends(get_db_session)):
          user: User = session.query(User).filter(and_(User.id == payload.sub, User.deleted == False)).one()

          return {
            "user_name": user.first_name + " " + user.last_name,
            "address": user.address,
            "avatar": user.avatar_url,
            "sign_method": user.sign_method,
            "balance": user.balance,
            "rollback": user.rollback
          }

        @router.get('/price/eth/input', summary='Returns the amount of USDT you get for exact eth')
        async def get_price_eth_input(amount: float) -> float:
          fee = get_current_gas_price() * int(cfg.ETH_SWAP_FEE)
          print(fee / 10**18)
          return (float(self.uniswap.get_price_input(eth, usdt, int(amount*(10**18)) + fee)))/10**6

        @router.get('/price/eth/output', summary='Returns the amount of USDT you get for exact eth')
        async def get_price_eth_input(amount: float) -> float:
          fee = get_current_gas_price() * int(cfg.ETH_SWAP_FEE)
          return (float(self.uniswap.get_price_output(eth, usdt, int(amount*(10**6)))) + fee)/10**18

        @router.post('/deposit/eth', summary="Deposit eth to user account")
        async def deposit_eth(tx_hash: str = Query(default = None, regex='0x[a-z0-9]{64}'), payload: TokenPayload = Depends(get_current_user_from_oauth), session:Session = Depends(get_db_session)) -> float:

          if tx_hash == None:
            raise HTTPException(
              status_code=status.HTTP_400_BAD_REQUEST,
              detail="You need to set hash"
            )

          if len(list(session.query(DWHistory).filter(DWHistory.tx_hash == tx_hash))) > 0:
            raise HTTPException(
              status_code=status.HTTP_400_BAD_REQUEST,
              detail="Already registered"
            )

          tx_data = get_transaction_eth_value(tx_hash)
          if not compare_eth_address(tx_data["to"], cfg.ETH_TREASURY_ADDRESS):
            raise HTTPException(
              status_code=status.HTTP_400_BAD_REQUEST,
              detail="Invalid transfer-didn't send to treasury"
            )

          fee = get_current_gas_price() * int(cfg.ETH_SWAP_FEE)
          tx = self.uniswap.make_trade(eth, usdt, int(to_wei(tx_data['value'], 'wei') - fee))
          receipt = wait_transaction_receipt(tx)

          received = float(int(receipt.logs[2].data, 16))/10**6

          new_history = DWHistory()
          new_history.tx_hash = tx_hash
          new_history.user_id = payload.sub
          new_history.direct = Direct.Deposit
          new_history.amount = received

          session.add(new_history)

          user_balance: UserBalance = session.query(UserBalance).filter(UserBalance.user_id == payload.sub).one()
          user_balance.balance += received

          return new_history

        @router.post('/deposit/usdt', summary="Deposit eth to user account")
        async def deposit_usdt(tx_hash: str = Query(default = None, regex='0x[a-z0-9]{64}'), payload: TokenPayload = Depends(get_current_user_from_oauth), session:Session = Depends(get_db_session)) -> float:

          if tx_hash == None:
            raise HTTPException(
              status_code=status.HTTP_400_BAD_REQUEST,
              detail="You need to set hash"
            )

          if len(list(session.query(DWHistory).filter(DWHistory.tx_hash == tx_hash))) > 0:
            raise HTTPException(
              status_code=status.HTTP_400_BAD_REQUEST,
              detail="Already registered"
            )

          tx_data = get_transaction_token_value(tx_hash)

          if not compare_eth_address(tx_data["contract"], cfg.ETH_USDT_ADDRESS):
            raise HTTPException(
              status_code=status.HTTP_400_BAD_REQUEST,
              detail="Invalid transfer-not USDT"
            )

          if not compare_eth_address(tx_data["to"], cfg.ETH_TREASURY_ADDRESS):
            raise HTTPException(
              status_code=status.HTTP_400_BAD_REQUEST,
              detail="Invalid transfer-didn't send to treasury"
            )

          received = float(int(tx_data['value'], 16))/10**6

          new_history = DWHistory()
          new_history.tx_hash = tx_hash
          new_history.user_id = payload.sub
          new_history.direct = Direct.Deposit
          new_history.amount = received

          session.add(new_history)

          user_balance: UserBalance = session.query(UserBalance).filter(UserBalance.user_id == payload.sub).one()
          user_balance.balance += received

          return new_history

        app.include_router(router)