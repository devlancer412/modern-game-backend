from uniswap import Uniswap
from sqlalchemy.orm import Session

from src.models import NFT, DWHistory, Direct, NFTHistory, NFTNote, NFTType, Network, UserBalance
from src.schemas.user import WalletData
from config import cfg
from src.utils.web3 import get_current_gas_price, get_eth_usdc_contract, get_eth_usdt_contract
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

  session.add(new_history)
  session.commit()
  session.close()

  print("eth deposit {}:{}".format(wallet.user_id, deposit_amount))
  return 0

async def deposited_eth_usdt(wallet: WalletData, amount):
  swap = Uniswap(address=wallet.public_key, private_key=wallet.private_key, version=2, provider=cfg.ETH_RPC_URL)
  fee =  get_current_gas_price() * int(cfg.ETH_SWAP_FEE)
  fee_price = float(swap.get_price_output(eth_usdc, eth, fee))

  contract = get_eth_usdt_contract()
  function = contract.transfer(cfg.ETH_TREASURY_ADDRESS, amount)
  params = {
    "from": wallet.public_key,
    "value": 0
  }
  swap._build_and_send_tx(function=function, tx_params=params)
  deposit_amount = float(amount - fee_price)/10*6

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

  print("usdt deposit {}:{}".format(wallet.user_id, deposit_amount))

async def deposited_eth_usdc(wallet: WalletData, amount):
  swap = Uniswap(address=wallet.public_key, private_key=wallet.private_key, version=2, provider=cfg.ETH_RPC_URL)
  fee =  get_current_gas_price() * int(cfg.ETH_SWAP_FEE)
  fee_price = float(swap.get_price_output(eth_usdt, eth, fee))

  contract = get_eth_usdc_contract()
  function = contract.transfer(cfg.ETH_TREASURY_ADDRESS, amount)
  params = {
    "from": wallet.public_key,
    "value": 0
  }
  swap._build_and_send_tx(function=function, tx_params=params)
  deposit_amount = float(amount - fee_price)/10*6

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

  print("usdt deposit {}:{}".format(wallet.user_id, deposit_amount))

def deposited_eth_721nft(address, wallet, id):
  session: Session = database.get_db_session()
  new_nft = NFT()
  new_nft.network = Network.Ethereum
  new_nft.user_id = wallet.user_id
  new_nft.token_address = address
  new_nft.token_id = id
  new_nft.temp_address = wallet.public_key
  new_nft.nft_type = NFTType.ERC721
  # need to calculate nft price
  new_nft.price = 0

  session.add(new_nft)
  session.flush()
  session.refresh(new_nft, attribute_names=['id'])

  new_history = NFTHistory()
  new_history.nft_id = new_nft.id
  new_history.after_user = wallet.user_id
  new_history.note = NFTNote.Deposit
  new_history.price = new_nft.price

  session.add(new_history)
  session.commit()
  session.close()

  print("ERC721 NFT deposited to {}:{}-{}", wallet.user_id, address, id)
  return

def deposited_eth_1155nft(address, wallet, id):
  session: Session = database.get_db_session()
  new_nft = NFT()
  new_nft.network = Network.Ethereum
  new_nft.user_id = wallet.user_id
  new_nft.token_address = address
  new_nft.token_id = id
  new_nft.temp_address = wallet.public_key
  new_nft.nft_type = NFTType.ERC1155
  # need to calculate nft price
  new_nft.price = 0

  session.add(new_nft)
  session.flush()
  session.refresh(new_nft, attribute_names=['id'])

  new_history = NFTHistory()
  new_history.nft_id = new_nft.id
  new_history.after_user = wallet.user_id
  new_history.note = NFTNote.Deposit
  new_history.price = new_nft.price

  session.add(new_history)
  session.commit()
  session.close()

  print("ERC1155 NFT deposited to {}:{}-{}", wallet.user_id, address, id)
  return