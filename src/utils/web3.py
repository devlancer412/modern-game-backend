from eth_abi import decode_abi
from hexbytes import HexBytes
from web3 import Web3
from web3.auto import w3

from config import cfg

web3_eth = Web3(provider=Web3.HTTPProvider(cfg.ETH_RPC_URL))

def compare_eth_address(address1: str, address2: str) -> bool:
  try:
    return Web3.toChecksumAddress(address1) == Web3.toChecksumAddress(address2)
  except:
    return False

def get_transaction_eth_value(tx_hash: str) -> object:
  try:
    tx = web3_eth.eth.get_transaction(tx_hash)

    return {
      "from": tx['from'],
      "to": tx['to'],
      "value": tx['value']
    }
  except Exception as ex:
    print(ex)
    return None

def uint256_to_address(input: str):
    return decode_abi(["address"], bytes(input))[0]

def get_transaction_token_value(tx_hash: str) -> object:
  try:
    tx = web3_eth.eth.get_transaction_receipt(tx_hash)
    print()

    return {
      "contract": tx["to"],
      "from": uint256_to_address(tx.logs[0].topics[1]),
      "to": uint256_to_address(tx.logs[0].topics[2]),
      "value": tx.logs[0].data
    }
  except Exception as ex:
    print(ex)
    return None

def wait_transaction_receipt(tx_hash: HexBytes) -> object:
  return web3_eth.eth.wait_for_transaction_receipt(tx_hash)