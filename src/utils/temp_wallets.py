from bip_utils import *
from datetime import datetime, timedelta

from src.schemas.user import WalletData
from config import cfg

# setup temporary wallets
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

# get available temporary wallets
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