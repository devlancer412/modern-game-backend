from solana.rpc.async_api import AsyncClient
from config import cfg

client: AsyncClient


async def main():
    client = AsyncClient(cfg.SOL_RPC_URL)
    await client.is_connected()


main()


async def get_transaction_data(signature: str):
    transaction = await client.get_transaction(signature)
    return transaction
