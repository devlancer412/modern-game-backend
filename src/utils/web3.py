from eth_abi import decode_abi, decode_single
from hexbytes import HexBytes
from web3 import Web3
from web3.middleware import construct_sign_and_send_raw_middleware
from web3.auto import w3

from config import cfg
from src.abis.ERC20 import abi as ERC20_abi
from src.abis.ERC721 import abi as ERC721_abi
from src.abis.ERC1155 import abi as ERC1155_abi

web3_eth = Web3(provider=Web3.HTTPProvider(cfg.ETH_RPC_URL))
web3_eth.middleware_onion.add(
    construct_sign_and_send_raw_middleware(cfg.ETH_TREASURY_PRIVATE_KEY)
)
web3_eth.eth.default_account = cfg.ETH_TREASURY_ADDRESS

ETH_ERC1155_TRANSFER_TOPIC = (
    "0xc3d58168c5ae7397731d063d5bbf3d657854427343f4c083240f7aacaa2d0f62"
)
ETH_NORMAL_TRANSFER_TOPIC = (
    "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"
)


def compare_eth_address(address1: str, address2: str) -> bool:
    try:
        return address1.lower() == address2.lower()
    except:
        return False


def get_transaction_eth_value(tx_hash: str) -> object:
    try:
        tx = web3_eth.eth.get_transaction(tx_hash)

        return {"from": tx["from"], "to": tx["to"], "value": tx["value"]}
    except Exception as ex:
        print(ex)
        return None


def uint256_to_address(input: str):
    return decode_single("address", HexBytes(input))


def erc1155_data_dispatch(input: str):
    return decode_abi(["uint256", "uint256"], HexBytes(input))


def get_transaction_token_value(tx_hash: str) -> object:
    try:
        tx = web3_eth.eth.get_transaction_receipt(tx_hash)

        if len(tx.logs) == 0:
            return

        return {
            "contract": tx["to"],
            "from": uint256_to_address(tx.logs[0].topics[1]),
            "to": uint256_to_address(tx.logs[0].topics[2]),
            "value": tx.logs[0].data,
        }
    except Exception as ex:
        print(ex)
        return None


def get_transaction_nft_data(tx_hash: str) -> object:
    try:
        tx = web3_eth.eth.get_transaction_receipt(tx_hash)
        transfer_logs = list(
            filter(
                lambda log: log.topics[0].hex() == ETH_NORMAL_TRANSFER_TOPIC
                or log.topics[0].hex() == ETH_ERC1155_TRANSFER_TOPIC,
                tx.logs,
            )
        )  # and log.topics[2] == cfg.ETH_TREASURY_ADDRESS

        if len(transfer_logs) == 0:
            return None

        return transfer_logs
    except Exception as ex:
        print(ex)
        return None


async def wait_transaction_receipt(tx_hash: HexBytes) -> object:
    return web3_eth.eth.wait_for_transaction_receipt(tx_hash)


def get_current_gas_price() -> int:
    return web3_eth.eth._gas_price()


def get_eth_erc20_contract(coin_address: str) -> object:
    contract_address = Web3.toChecksumAddress(coin_address)

    contract = web3_eth.eth.contract(contract_address, abi=ERC20_abi)
    return contract


def get_eth_erc721_contract(address: str) -> object:
    contract_address = Web3.toChecksumAddress(address)

    contract = web3_eth.eth.contract(contract_address, abi=ERC721_abi)
    return contract


def get_eth_erc1155_contract(address: str) -> object:
    contract_address = Web3.toChecksumAddress(address)

    contract = web3_eth.eth.contract(contract_address, abi=ERC1155_abi)
    return contract


async def send_eth_stable_to(token_address: str, wallet: str, amount: int) -> object:
    contract_address = Web3.toChecksumAddress(token_address)
    treasury_address = Web3.toChecksumAddress(cfg.ETH_TREASURY_ADDRESS)
    wallet_address = Web3.toChecksumAddress(wallet)

    # try:
    contract = web3_eth.eth.contract(contract_address, abi=ERC20_abi)
    decimal = contract.functions.decimals().call()

    amount_wei = int(amount * 10**decimal)
    transaction = contract.functions.transfer(
        wallet_address, amount_wei
    ).buildTransaction(
        {
            "type": "0x2",  # optional - defaults to '0x2' when dynamic fee transaction params are present
            "from": treasury_address,  # optional if w3.eth.default_account was set with acct.address
            "maxFeePerGas": 2000000000,  # required for dynamic fee transactions
            "maxPriorityFeePerGas": 1000000000,  # required for dynamic fee transactions
        }
    )

    hash_hex = web3_eth.eth.send_transaction(transaction)
    receipt = wait_transaction_receipt(hash_hex)

    return receipt


def send_eth_erc721_to(to_wallet: str, address: str, id: str) -> object:
    contract_address = Web3.toChecksumAddress(address)
    from_address = Web3.toChecksumAddress(cfg.ETH_TREASURY_ADDRESS)
    to_address = Web3.toChecksumAddress(to_wallet)

    # try:
    contract = get_eth_erc721_contract(contract_address)
    transaction = contract.functions.transfer(to_address, id).buildTransaction(
        {
            "type": "0x2",  # optional - defaults to '0x2' when dynamic fee transaction params are present
            "from": from_address,  # optional if w3.eth.default_account was set with acct.address
            "maxFeePerGas": 2000000000,  # required for dynamic fee transactions
            "maxPriorityFeePerGas": 1000000000,  # required for dynamic fee transactions
        }
    )

    hash_hex = web3_eth.eth.send_transaction(transaction)
    receipt = wait_transaction_receipt(hash_hex)

    return receipt


def send_eth_erc1155_to(to_wallet: str, address: str, id: str) -> object:
    contract_address = Web3.toChecksumAddress(address)
    from_address = Web3.toChecksumAddress(cfg.ETH_TREASURY_ADDRESS)
    to_address = Web3.toChecksumAddress(to_wallet)

    # try:
    contract = get_eth_erc1155_contract(contract_address)
    transaction = contract.functions.transfer(
        from_address, to_address, id
    ).buildTransaction(
        {
            "type": "0x2",  # optional - defaults to '0x2' when dynamic fee transaction params are present
            "from": from_address,  # optional if w3.eth.default_account was set with acct.address
            "maxFeePerGas": 2000000000,  # required for dynamic fee transactions
            "maxPriorityFeePerGas": 1000000000,  # required for dynamic fee transactions
        }
    )

    hash_hex = web3_eth.eth.send_transaction(transaction)
    receipt = wait_transaction_receipt(hash_hex)

    return receipt
