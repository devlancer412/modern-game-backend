from array import array
import asyncio
from datetime import datetime, timedelta
import time
from threading import Thread

from web3 import Web3

from config import cfg
from src.utils.wallet_dw import deposited_eth, deposited_eth_1155nft, deposited_eth_721nft, deposited_eth_stabele_coin
from .web3 import compare_eth_address, uint256_to_address, web3_eth
from src.utils.temp_wallets import eth_wallet_list, sol_wallet_list

ETH_ERC1155_TRANSFER_TOPIC = "0xc3d58168c5ae7397731d063d5bbf3d657854427343f4c083240f7aacaa2d0f62"
ETH_NORMAL_TRANSFER_TOPIC = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"
# setup acceptable token address list
# setup acceptable NFT address list
ETH_721NFT_LIST = []
ETH_1155NFT_LIST = []

# ethereum transaction filter setup
async def handle_block(block):
    block = web3_eth.eth.getBlock(block.hex(), full_transactions=True)
    transactions = block['transactions']
    for tx in transactions:
      to_wallet = list(filter(lambda item: compare_eth_address(item.public_key, tx.to) and item.is_using == True, eth_wallet_list))
      if len(to_wallet) > 0:
        to_wallet = to_wallet[0]
        to_wallet.is_using = False
        await deposited_eth(wallet=to_wallet, amount=tx.value)
        continue

      receipt = web3_eth.eth.get_transaction_receipt(tx.hash)

      transfer_logs = list(filter(lambda log: log.topics[0].hex() == ETH_NORMAL_TRANSFER_TOPIC or log.topics[0] == ETH_ERC1155_TRANSFER_TOPIC, receipt.logs))
      if len(transfer_logs) == 0:
        continue

      for log in transfer_logs:
        if log.topics[0] == ETH_ERC1155_TRANSFER_TOPIC:
          to_address = uint256_to_address(log.topics[3])
        else:
          to_address = uint256_to_address(log.topics[2])

        to_wallet = list(filter(lambda item: compare_eth_address(item.public_key, to_address) and item.is_using, eth_wallet_list))

        if len(to_wallet) == 0:
          continue

        to_wallet = to_wallet[0]

        contract_address = tx.to
        print(contract_address)
        if compare_eth_address(contract_address, cfg.ETH_USDT_ADDRESS) or compare_eth_address(contract_address, cfg.ETH_USDC_ADDRESS):
          await deposited_eth_stabele_coin(coin=contract_address, wallet=to_wallet, amount=int(log.data, 16))
          continue

        if ETH_721NFT_LIST.index(contract_address) >= 0:
          await deposited_eth_721nft(address=contract_address, wallet=to_wallet, id=log.topics[3])
          continue

        if ETH_1155NFT_LIST.index(contract_address) >= 0:
          await deposited_eth_1155nft(address=contract_address, wallet=to_wallet, id=log.topics[3])
          continue

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
