from __future__ import annotations
from datetime import datetime
from operator import and_
from typing import Callable

from app.__internal import Function
from fastapi import FastAPI, APIRouter, Query, status, HTTPException, Depends
from sqlalchemy.orm import Session
from uniswap import Uniswap

from src.dependencies.auth_deps import get_current_user_from_oauth
from src.dependencies.database_deps import get_db_session
from src.models import User, UserBalance
from src.schemas.auth import TokenPayload

from config import cfg
from src.utils.background_transaction_filter import WalletData, create_transacion_filter, get_eth_deposit_wallet
from src.utils.web3 import get_current_gas_price, send_eth_token_to, wait_transaction_receipt

eth = "0x0000000000000000000000000000000000000000"
eth_usdt = cfg.ETH_USDT_ADDRESS

class UserAPI(Function):

    def __init__(self, error: Callable):
        self.log.info("Swap api initailized")
        self.uniswap = Uniswap(address=cfg.ETH_TREASURY_ADDRESS, private_key=cfg.ETH_TREASURY_PRIVATE_KEY, version=2, provider=cfg.ETH_RPC_URL)
        create_transacion_filter()

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

        @router.get('/price/eth/usdt/input', summary='Returns the amount of USDT you get for exact ETH')
        async def get_price_eth_usdt_input(amount: float) -> float:
          fee = get_current_gas_price() * int(cfg.ETH_SWAP_FEE)
          print(fee / 10**18)
          return (float(self.uniswap.get_price_input(eth, eth_usdt, int(amount*(10**18)) + fee)))/10**6

        @router.get('/price/eth/usdt/output', summary='Returns the amount of ETH need to deposit for exact USDT')
        async def get_price_eth_usdt_output(amount: float) -> float:
          fee = get_current_gas_price() * int(cfg.ETH_SWAP_FEE)
          return (float(self.uniswap.get_price_output(eth, eth_usdt, int(amount*(10**6)))) + fee)/10**18

        @router.get('/price/usdt/eth/input', summary='Returns the amount of ETH you get for exact USDT')
        async def get_price_usdt_eth_input(amount: float) -> float:
          fee = get_current_gas_price() * int(cfg.ETH_SWAP_FEE)
          print(fee / 10**18)
          return (float(self.uniswap.get_price_input(eth_usdt, eth, int(amount*(10**6)))) + fee)/10**18

        @router.get('/price/usdt/eth/output', summary='Returns the amount of USDT need to deposit for exact ETH')
        async def get_price_usdt_eth_output(amount: float) -> float:
          fee = get_current_gas_price() * int(cfg.ETH_SWAP_FEE)
          return (float(self.uniswap.get_price_output(eth_usdt, eth, int(amount*(10**18))+ fee)))/10**6

        @router.post('/deposit_wallet/eth', summary="Return deposit wallet data")
        async def deposit_eth_eth(payload: TokenPayload = Depends(get_current_user_from_oauth), session:Session = Depends(get_db_session)) -> float:

          wallet: WalletData = get_eth_deposit_wallet()
          wallet.user_id = payload.sub
          wallet.timestamp = datetime.today().timestamp()
          wallet.is_using = True

          return wallet.public_key

        @router.post('/withdraw/eth/eth', summary="Withdraw money with ETH")
        async def withdraw_eth_eth(amount: float = Query(default=0), wallet: str = Query(default=None, regex='0x[A-Za-z0-9]{40}'), payload: TokenPayload = Depends(get_current_user_from_oauth), session:Session = Depends(get_db_session)) -> float:
          if amount == 0:
            raise HTTPException(
              status_code=status.HTTP_400_BAD_REQUEST,
              detail="You need to set amount more than 0"
            )

          user_balance: UserBalance = session.query(UserBalance).filter(UserBalance.user_id == payload.sub).one()

          fee = get_current_gas_price() * int(cfg.ETH_SWAP_FEE)
          total_eth = self.uniswap.get_price_input(eth_usdt, eth, (user_balance.balance) * 10**6) - fee

          if amount > total_eth:
            raise HTTPException(
              status_code=status.HTTP_400_BAD_REQUEST,
              detail="Much than real amount"
            )

          user_balance.balance -= float(self.uniswap.get_price_output(eth_usdt, eth, amount*10**18) + fee)/10**6

          tx = self.uniswap.make_trade_output(eth_usdt, eth, amount*10**18, wallet)
          receipt = wait_transaction_receipt(tx)

          return receipt

        @router.post('/withdraw/eth/usdt', summary="Withdraw money with USDT")
        async def withdraw_eth(amount: float = Query(default=0), wallet: str = Query(default=None, regex='0x[A-Za-z0-9]{40}'), payload: TokenPayload = Depends(get_current_user_from_oauth), session:Session = Depends(get_db_session)) -> float:
          if amount == 0:
            raise HTTPException(
              status_code=status.HTTP_400_BAD_REQUEST,
              detail="You need to set amount more than 0"
            )

          user_balance: UserBalance = session.query(UserBalance).filter(UserBalance.user_id == payload.sub).one()

          fee = get_current_gas_price() * int(cfg.ETH_SWAP_FEE)
          fee_usdt = float(self.uniswap.get_price_output(eth_usdt, eth, fee))/10**6

          if amount + fee_usdt > user_balance.balance:
            raise HTTPException(
              status_code=status.HTTP_400_BAD_REQUEST,
              detail="Much than real amount"
            )

          try:
            receipt = send_eth_token_to(eth_usdt, wallet, amount)
          except Exception as ex:
            print(ex)
            raise HTTPException(
              status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
              detail="Some error occured in server side"
            )

          user_balance.balance -= amount + fee_usdt
          return receipt['blockHash'].hex()


        app.include_router(router)