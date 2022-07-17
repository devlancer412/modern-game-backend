import asyncio
import time
from threading import Thread

from web3 import Web3
from solana.rpc.websocket_api import connect

from config import cfg
from src.schemas.user import WalletData
from src.utils.wallet_dw import deposited_eth, deposited_eth_1155nft, deposited_eth_721nft, deposited_eth_stabele_coin
from .web3 import compare_eth_address, erc1155_data_dispatch, uint256_to_address, web3_eth
from src.utils.temp_wallets import eth_wallet_list, sol_wallet_list

ETH_ERC1155_TRANSFER_TOPIC = "0xc3d58168c5ae7397731d063d5bbf3d657854427343f4c083240f7aacaa2d0f62"
ETH_NORMAL_TRANSFER_TOPIC = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"
# setup acceptable token address list
# setup acceptable NFT address list
ETH_721NFT_LIST = list(map(lambda address: address.lower(), ["0x2E399B75F61B16D558453EC644c7B1d10e1d9f0a"]))
ETH_1155NFT_LIST = list(map(lambda address: address.lower(), ["0x7f6c8bAdcE624DAc296C738F65cA2AB7EFD2b27F"]))

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

      transfer_logs = list(filter(lambda log: log.topics[0].hex() == ETH_NORMAL_TRANSFER_TOPIC or log.topics[0].hex() == ETH_ERC1155_TRANSFER_TOPIC, receipt.logs))
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
        to_wallet = eth_wallet_list[0]

        contract_address = tx.to
        if compare_eth_address(contract_address, cfg.ETH_USDT_ADDRESS) or compare_eth_address(contract_address, cfg.ETH_USDC_ADDRESS):
          to_wallet.is_using = False
          await deposited_eth_stabele_coin(coin=contract_address, wallet=to_wallet, amount=int(log.data, 16))
          continue

        if contract_address.lower() in ETH_721NFT_LIST:
          to_wallet.is_using = False
          await deposited_eth_721nft(address=contract_address, wallet=to_wallet, id=int(log.topics[3].hex(), 16))
          continue

        if contract_address.lower() in ETH_1155NFT_LIST:
          to_wallet.is_using = False
          await deposited_eth_1155nft(address=contract_address, wallet=to_wallet, data=erc1155_data_dispatch(log.data))
          continue

async def handle_log(log):
  print(type(log))


async def eth_log_loop(block_filter, poll_interval):
  while True:
    for block in block_filter.get_new_entries():
      await handle_block(block)
    time.sleep(poll_interval)


async def sol_log_loop(poll_interval):
  wss = await connect(cfg.SOL_WSS_URL)
  await wss.logs_subscribe()
  resp = await wss.recv()
  subscription_id = resp.result
  print("solana subscribe id: {}".format(subscription_id))
  while True:
    resp = await wss.recv()
    result = resp.result
    print(result)
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
    eth_block_filter = web3_eth.eth.filter('latest')
    loop = get_or_create_eventloop()
    print("Listening started -- ethereum")
    try:
        loop.run_until_complete(asyncio.gather(eth_log_loop(eth_block_filter, 2)))
    finally:
        # close loop to free up system resources
        print('Listening terminated')
        loop.close()

def sol_transaction_filter_process():
    loop = get_or_create_eventloop()
    print("Listening started -- solana")
    try:
        loop.run_until_complete(asyncio.gather(sol_log_loop(1)))
    finally:
        # close loop to free up system resources
        print('Listening terminated')
        loop.close()

def create_transacion_filter():
    worker1 = Thread(target=eth_transaction_filter_process, args=(), daemon=True)
    worker2 = Thread(target=sol_transaction_filter_process, args=(), daemon=True)
    worker1.start()
    worker2.start()
