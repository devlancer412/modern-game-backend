from uniswap import Uniswap
from sqlalchemy.orm import Session

from src.models import DWHistory, Direct, UserBalance
from src.schemas.user import WalletData
from config import cfg
from src.utils.web3 import get_current_gas_price
from src.database import database

eth = "0x0000000000000000000000000000000000000000"
eth_usdt = cfg.ETH_USDT_ADDRESS

async def deposited_eth(wallet: WalletData, amount: int):
  swap = Uniswap(address=wallet.public_key, private_key=wallet.private_key, version=2, provider=cfg.ETH_RPC_URL)
  fee =  get_current_gas_price() * int(cfg.ETH_SWAP_FEE)

  swap.make_trade(eth, eth_usdt, amount - fee, cfg.ETH_TREASURY_ADDRESS)
  deposit_amount = float(swap.get_price_input(eth, eth_usdt, amount - fee))/10**6

  session: Session = database.get_db_session()
  balance: UserBalance = session.query(UserBalance).filter(UserBalance.user_id == wallet.user_id).one()
  balance.balance += deposit_amount
  balance.deposit_balance += deposit_amount

  new_history = DWHistory()
  new_history.user_id = wallet.user_id
  new_history.amount = deposit_amount
  new_history.direct = Direct.Deposit

  session.add(new_history)
  session.commit()
  session.close()

  print("eth deposit {}:{}".format(wallet.user_id, deposit_amount))

  WalletData.is_using = False
  return 0

# def deposited_eth_usdt(wallet: W)