from uniswap import Uniswap
from sqlalchemy.orm import Session

from src.models import NFT, DWHistory, DepositMethod, Direct, NFTHistory, NFTNote, NFTType, Network, UserBalance
from src.schemas.user import WalletData
from config import cfg
from src.utils.web3 import get_current_gas_price, get_eth_erc1155_contract, get_eth_erc20_contract
from src.database import database

eth = "0x0000000000000000000000000000000000000000"
eth_usdt = cfg.ETH_USDT_ADDRESS
eth_usdc = cfg.ETH_USDC_ADDRESS

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
  new_history.deposit_method = DepositMethod.Eth

  session.add(new_history)
  session.commit()
  session.close()

  print("eth deposit {}:{}".format(wallet.user_id, deposit_amount))
  return 0

async def deposited_eth_stabele_coin(coin:str, wallet: WalletData, amount, hash):
  swap = Uniswap(address=wallet.public_key, private_key=wallet.private_key, version=2, provider=cfg.ETH_RPC_URL)
  fee =  get_current_gas_price() * int(cfg.ETH_SWAP_FEE)
  fee_price = float(swap.get_price_output(coin, eth, fee))

  contract = get_eth_erc20_contract(coin)
  function = contract.functions.transfer(cfg.ETH_TREASURY_ADDRESS, amount)
  decimals = contract.functions.decimals().call()

  params = swap._get_tx_params()
  swap._build_and_send_tx(function=function, tx_params=params)
  deposit_amount = float(amount - fee_price)/10**decimals

  session: Session = database.get_db_session()

  try:
    last_history = list(session.query(DWHistory).filter(DWHistory.tx_hash == hash).first())
    if len(last_history) == 0:
      return

    balance: UserBalance = session.query(UserBalance).filter(UserBalance.user_id == wallet.user_id).one()
  except Exception as ex:
    print(ex)
    return

  balance.balance += deposit_amount
  balance.deposit_balance += deposit_amount

  new_history = DWHistory()
  new_history.user_id = wallet.user_id
  new_history.amount = deposit_amount
  new_history.direct = Direct.Deposit
  if coin == cfg.ETH_USDT_ADDRESS:
    new_history.deposit_method = DepositMethod.Usdt
  elif coin == cfg.ETH_USDC_ADDRESS:
    new_history.deposit_method = DepositMethod.Usdc

  new_history.tx_hash = hash

  session.add(new_history)
  session.commit()
  session.close()

  print("stable coin deposit {}:{}".format(wallet.user_id, deposit_amount))
  return
