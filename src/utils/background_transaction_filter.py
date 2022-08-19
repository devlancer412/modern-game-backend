import asyncio
import time
from threading import Thread

from solana.rpc.websocket_api import connect
from bip_utils import Base58Decoder

from config import cfg
from src.utils.wallet_dw import deposited_eth, deposited_eth_stabele_coin
from .web3 import (
    compare_eth_address,
    erc1155_data_dispatch,
    uint256_to_address,
    web3_eth,
    solana_client,
)
from src.utils.temp_wallets import eth_wallet_list, sol_wallet_list

ETH_ERC1155_TRANSFER_TOPIC = (
    "0xc3d58168c5ae7397731d063d5bbf3d657854427343f4c083240f7aacaa2d0f62"
)
ETH_NORMAL_TRANSFER_TOPIC = (
    "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"
)

SOL_PROGRAM_ID = "11111111111111111111111111111111"
# ethereum transaction filter setup
async def handle_block(block):
    block = web3_eth.eth.getBlock(block.hex(), full_transactions=True)
    transactions = block["transactions"]
    for tx in transactions:
        to_wallet = list(
            filter(
                lambda item: compare_eth_address(item.public_key, tx.to)
                and item.is_using == True,
                eth_wallet_list,
            )
        )
        if len(to_wallet) > 0:
            to_wallet = to_wallet[0]
            to_wallet.is_using = False
            await deposited_eth(wallet=to_wallet, amount=tx.value, hash=tx.hash)
            continue

        receipt = web3_eth.eth.get_transaction_receipt(tx.hash)

        transfer_logs = list(
            filter(
                lambda log: log.topics[0].hex() == ETH_NORMAL_TRANSFER_TOPIC
                or log.topics[0].hex() == ETH_ERC1155_TRANSFER_TOPIC,
                receipt.logs,
            )
        )
        if len(transfer_logs) == 0:
            continue

        for log in transfer_logs:
            if len(log.topics) <= 3:
                continue

            if log.topics[0] == ETH_ERC1155_TRANSFER_TOPIC:
                to_address = uint256_to_address(log.topics[3])
            else:
                to_address = uint256_to_address(log.topics[2])

            to_wallet = list(
                filter(
                    lambda item: compare_eth_address(item.public_key, to_address)
                    and item.is_using,
                    eth_wallet_list,
                )
            )

            if len(to_wallet) == 0:
                continue

            to_wallet = to_wallet[0]
            to_wallet = eth_wallet_list[0]

            contract_address = tx.to
            if compare_eth_address(
                contract_address, cfg.ETH_USDT_ADDRESS
            ) or compare_eth_address(contract_address, cfg.ETH_USDC_ADDRESS):
                to_wallet.is_using = False
                await deposited_eth_stabele_coin(
                    coin=contract_address,
                    wallet=to_wallet,
                    amount=int(log.data, 16),
                    hash=tx.hash,
                )
                continue


def decode_instruction_data(data: bytes):
    instructors = []
    for i in range(0, len(data), 4):
        new_instructor = 0
        j = 0
        while j < 3 and i + j < len(data):
            new_instructor += data[i + j] * 256**j
            j += 1

        instructors.append(new_instructor)

    return instructors


async def handle_log(context):
    signature = context.value.signature
    # signature = "4GJ69zcPvuHukPfcr7DtCq4RDvUwBYoscM8tkLi1p3S4kUwskn2enytbrADqLAZA8bxR1SgL24kMaLXQesLhM9LY"
    # signature = "2qNywZgfTNh22J6NRhezFfbay3MegU3di6SXFCBsP4S6XZeufYRD3v1pKRZrMUHT5dgaCwuQBya1h1yW7WmYWtaq"
    result = solana_client.get_transaction(signature)
    trx = result["result"]
    if trx == None:
        return

    accounts = trx["transaction"]["message"]["accountKeys"]
    instructions = trx["transaction"]["message"]["instructions"]
    for instruction in instructions:
        data = Base58Decoder.Decode(instruction["data"])
        if len(data) == 0:
            continue

        instructors = decode_instruction_data(data)
        program = accounts[instruction["programIdIndex"]]

        if program == SOL_PROGRAM_ID:
            if len(instructors) != 3 and instructors[0] != 2:
                continue

            amount = instructors[2] * 256**4 + instructors[1]
            if amount <= int(cfg.SOL_SWAP_FEE):
                continue

            print(
                "Sol transfer: {} -> {} : {}sol".format(
                    accounts[instruction["accounts"][0]],
                    accounts[instruction["accounts"][1]],
                    float(amount) / 10**9,
                )
            )
            continue

        if program == cfg.SOL_USDT_ADDRESS:
            print("usdt trnasfer ", instructors)
            continue

        if program == cfg.SOL_USDC_ADDRESS:
            print("usdc trnasfer ", instructors)
            continue


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
        try:
            resp = await wss.recv()
        except Exception:
            print("--closed error--")
            await wss.close()
            wss = await connect(cfg.SOL_WSS_URL)
            await wss.logs_subscribe()
            resp = await wss.recv()
            subscription_id = resp.result
            print("solana subscribe id: {}".format(subscription_id))
            continue

        result = resp.result
        await handle_log(result)
        # time.sleep(poll_interval)


def get_or_create_eventloop():
    try:
        return asyncio.get_event_loop()
    except RuntimeError as ex:
        if "There is no current event loop in thread" in str(ex):
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            return asyncio.get_event_loop()


def eth_transaction_filter_process():
    eth_block_filter = web3_eth.eth.filter("latest")
    loop = get_or_create_eventloop()
    print("Listening started -- ethereum")
    try:
        loop.run_until_complete(asyncio.gather(eth_log_loop(eth_block_filter, 2)))
    finally:
        # close loop to free up system resources
        print("Listening terminated")
        loop.close()


def sol_transaction_filter_process():
    loop = get_or_create_eventloop()
    print("Listening started -- solana")
    try:
        loop.run_until_complete(asyncio.gather(sol_log_loop(1)))
    finally:
        # close loop to free up system resources
        loop.close()
        print("error")


def create_transacion_filter():
    worker1 = Thread(target=eth_transaction_filter_process, args=(), daemon=True)
    worker2 = Thread(target=sol_transaction_filter_process, args=(), daemon=True)
    worker1.start()
    worker2.start()
