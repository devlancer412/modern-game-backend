from array import array
import asyncio
from datetime import datetime, timedelta
import time
from threading import Thread
from bip_utils import *

from config import cfg
from src.utils.wallet_dw import deposited_eth
from src.schemas.user import WalletData
from .web3 import web3_eth

eth_wallet_list = []
sol_wallet_list = []

def setup_eth_temp_wallets():
  seed_bytes = Bip39SeedGenerator(cfg.ETH_TEMP_MNEMONIC).Generate("")
  bip44_mst_ctx = Bip44.FromSeed(seed_bytes, Bip44Coins.ETHEREUM)
  bip44_acc_ctx = bip44_mst_ctx.Purpose().Coin().Account(0)
  for i in range(100):
    bip44_chg_ctx = bip44_acc_ctx.Change(Bip44Changes.CHAIN_EXT).AddressIndex(i)

    new_wallet = WalletData()
    new_wallet.public_key = bip44_chg_ctx.PublicKey().ToAddress()
    new_wallet.private_key = bip44_chg_ctx.PrivateKey().Raw().ToHex()
    new_wallet.timestamp = datetime.today().timestamp()
    new_wallet.user_id = -1
    new_wallet.is_using = False

    eth_wallet_list.append(new_wallet)

def setup_sol_temp_wallets():
  seed_bytes = Bip39SeedGenerator(cfg.ETH_TEMP_MNEMONIC).Generate()
  bip44_mst_ctx = Bip44.FromSeed(seed_bytes, Bip44Coins.SOLANA)
  for i in range(100):
    bip44_acc_ctx = bip44_mst_ctx.Purpose().Coin().Account(i)
    bip44_chg_ctx = bip44_acc_ctx.Change(Bip44Changes.CHAIN_EXT)

    new_wallet = WalletData()
    new_wallet.public_key = bip44_chg_ctx.PublicKey().ToAddress()
    new_wallet.private_key = Base58Encoder.Encode(
        bip44_chg_ctx.PrivateKey().Raw().ToBytes() + bip44_chg_ctx.PublicKey().RawCompressed().ToBytes()[1:]
    )
    new_wallet.timestamp = datetime.today().timestamp()
    new_wallet.user_id = -1
    new_wallet.is_using = False

    sol_wallet_list.append(new_wallet)

setup_eth_temp_wallets()
setup_sol_temp_wallets()

def get_eth_deposit_wallet():
  remove_time_stamp = (datetime.today() - timedelta(days=1)).timestamp()
  for wallet in eth_wallet_list:
    if wallet.timestamp < remove_time_stamp and wallet.is_using:
      wallet.is_using = False
    if wallet.is_using == False:
      return wallet

def get_sol_deposit_wallet():
  remove_time_stamp = (datetime() - timedelta(days=1)).timestamp()
  for wallet in sol_wallet_list:
    if wallet.timestamp < remove_time_stamp and wallet.is_using:
      wallet.is_using = False
    if wallet.is_using == False:
      return wallet

async def handle_block(block):
    block = web3_eth.eth.getBlock(block.hex(), full_transactions=True)
    transactions = block['transactions']
    for tx in transactions:
      wallet = list(filter(lambda item: item.public_key == tx.to and item.is_using == True, eth_wallet_list))
      if len(wallet) > 0:
        wallet = wallet[0]
        return await deposited_eth(wallet=wallet, amount=tx.value)

async def log_loop(block_filter, poll_interval):
    while True:
        for block in block_filter.get_new_entries():
            await handle_block(block)
        time.sleep(poll_interval)


def get_or_create_eventloop():
    try:
        return asyncio.get_event_loop()
    except RuntimeError as ex:
        if "There is no current event loop in thread" in str(ex):
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            return asyncio.get_event_loop()

def transaction_filter_process():
    eth_block_filter = web3_eth.eth.filter('latest')
    loop = get_or_create_eventloop()
    print("Listening started")
    try:
        loop.run_until_complete(
            asyncio.gather(
                log_loop(eth_block_filter, 2)))
        # log_loop(block_filter, 2),
        # log_loop(tx_filter, 2)))
    finally:
        # close loop to free up system resources
        print('Listening terminated')
        loop.close()

def create_transacion_filter():
    worker = Thread(target=transaction_filter_process, args=(), daemon=True)
    worker.start()
