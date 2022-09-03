from binascii import hexlify
from distutils.command.build import build
from io import BytesIO
import json
from struct import unpack
from solana.publickey import PublicKey
from solana.keypair import Keypair
from solana.transaction import Transaction
from solana.rpc.async_api import AsyncClient
from spl.token.constants import TOKEN_PROGRAM_ID
from spl.token.instructions import (
    get_associated_token_address,
    transfer_checked,
    create_associated_token_account,
    TransferCheckedParams,
)
from based58 import b58decode
from config import cfg

client = AsyncClient(cfg.SOL_RPC_URL)


async def get_solana_nft_transaction_data(signature: str):
    await client.is_connected()
    await client.confirm_transaction(signature, "finalized")
    response = await client.get_transaction(signature)
    message = response["result"]["transaction"]["message"]
    accounts = list(message["accountKeys"])
    instructions = list(message["instructions"])

    data = []
    for instruction in instructions:
        if accounts[int(instruction["programIdIndex"])] == str(TOKEN_PROGRAM_ID):
            instruction_data = b58decode(bytes(instruction["data"], "utf-8"))
            buffer = BytesIO(instruction_data[1:]).read()
            if len(buffer) != 9:
                continue
            (amount, decimal) = unpack("qs", buffer)
            if instruction_data[0] != 12 and amount != 1 and decimal != 0:
                continue

            transfer_data = {
                "from": accounts[instruction["accounts"][0]],
                "to": accounts[instruction["accounts"][2]],
                "token": accounts[instruction["accounts"][1]],
            }

            data.append(transfer_data)
    return data


async def is_owner_of_nft(mint: str, owner: str, account: str) -> bool:
    await client.is_connected()
    ata = get_associated_token_address(PublicKey(owner), PublicKey(mint))
    return str(ata) == account


async def transfer_solana_nft(mint: str, to: str):
    await client.is_connected()
    transaction = Transaction()
    toAddress = PublicKey(to)
    mintAddress = PublicKey(mint)
    payer = Keypair.from_secret_key(
        b58decode(bytes(cfg.SOL_TREASURY_PRIVATE_KEY, "utf-8"))
    )
    fromAccount = get_associated_token_address(payer.public_key, mintAddress)
    toAccount = get_associated_token_address(toAddress, mintAddress)
    try:
        await client.get_account_info(toAccount)
    except:
        transaction.add(
            create_associated_token_account(
                payer=payer.public_key, owner=toAddress, mint=mintAddress
            )
        )

    transaction.add(
        transfer_checked(
            TransferCheckedParams(
                program_id=TOKEN_PROGRAM_ID,
                source=fromAccount,
                mint=mintAddress,
                dest=toAccount,
                owner=payer.public_key,
                amount=1,
                decimals=0,
            )
        )
    )

    response = await client.send_transaction(transaction, payer)
    return response["result"]
