from __future__ import annotations
from dataclasses import Field
from operator import and_, or_
from typing import Callable

from eth_utils import to_wei

from app.__internal import Function
from fastapi import FastAPI, APIRouter, Query, status, HTTPException, Depends
from sqlalchemy.orm import Session
import requests
import json

from src.dependencies.auth_deps import get_current_user_from_oauth
from src.dependencies.database_deps import get_db_session
from src.models import (
    Avatar,
    DWMethod,
    Direct,
    Transaction,
    User,
)
from src.schemas.auth import TokenPayload

from config import cfg
from src.schemas.user import UserUpdateData

from src.changenow_api.client import api_wrapper as cnio_api
from opensea import OpenseaAPI

from src.utils.web3 import send_eth_stable_to


class UserAPI(Function):
    def __init__(self, error: Callable):
        self.log.info("user api initailized")
        self.opensea = OpenseaAPI(apikey=cfg.OPENSEA_API)

    def Bootstrap(self, app: FastAPI):
        router = APIRouter(
            prefix="/user",
            tags=["user"],
            responses={404: {"description": "Not found"}},
        )

        @router.get("/avatars", summary="return available avatars")
        async def get_avatars(
            payload: TokenPayload = Depends(get_current_user_from_oauth),
            session: Session = Depends(get_db_session),
        ):
            avatars = list(
                session.query(Avatar)
                .filter(
                    or_(
                        Avatar.owner_id == None,
                        Avatar.owner_id == payload.sub,
                    )
                )
                .add_columns()
            )

            return avatars

        @router.get("/", summary="Get user data")
        async def get_user_data(
            payload: TokenPayload = Depends(get_current_user_from_oauth),
            session: Session = Depends(get_db_session),
        ):
            user: User = (
                session.query(User)
                .filter(and_(User.id == payload.sub, User.deleted == False))
                .first()
            )

            if user is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="User doesn't exist",
                )

            return {
                "name": user.name,
                "address": user.address,
                "avatar": user.avatar_url,
                "signMethod": user.sign_method,
                "balance": user.balance,
                "rollback": user.rollback,
                "isPrivacy": user.is_privacy,
                "isPending": user.is_pending,
            }

        @router.post("/", summary="Set user settings")
        async def set_user_data(
            data: UserUpdateData,
            payload: TokenPayload = Depends(get_current_user_from_oauth),
            session: Session = Depends(get_db_session),
        ):
            user: User = (
                session.query(User)
                .filter(and_(User.id == payload.sub, User.deleted == False))
                .first()
            )

            if user is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="User doesn't exist",
                )

            user.name = data.name
            user.is_privacy = data.isPrivacy

            avatar: Avatar = (
                session.query(Avatar).filter(Avatar.url == data.avatar).first()
            )

            if avatar is not None:
                user.avatar_id = avatar.id
            else:
                new_avatar = Avatar()
                new_avatar.url = data.avatar
                new_avatar.owner_id = user.id

                session.add(new_avatar)
                session.flush()
                session.refresh(new_avatar, attribute_names=["id"])

                user.avatar_id = new_avatar.id

            return True

        @router.get("/price/eth", summary="return current eth price")
        async def get_price_eth():
            try:
                url = "https://api.coingecko.com/api/v3/simple/price?ids=ethereum&vs_currencies=usd"
                response = requests.get(url)

                if response.status_code != 200:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Invaild access token",
                    )

                data = json.loads(response.content.decode("utf-8"))

                return data["ethereum"]["usd"]
            except Exception as ex:
                print(ex)
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Something went wrong in server side",
                )

        @router.get("/price/sol", summary="return current eth price")
        async def get_price_sol():
            try:
                url = "https://api.coingecko.com/api/v3/simple/price?ids=solana&vs_currencies=usd"
                response = requests.get(url)

                if response.status_code != 200:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Invaild access token",
                    )

                data = json.loads(response.content.decode("utf-8"))

                return data["solana"]["usd"]
            except Exception as ex:
                print(ex)
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Something went wrong in server side",
                )

        @router.get(
            "/price/eth/usdt/input",
            summary="Returns the amount of USDT you get for exact ETH",
        )
        async def get_price_eth_usdt_input(amount: float) -> float:
            try:
                url = "https://vip-api.changenow.io/v1.2/exchange/estimate?fromCurrency=eth&fromNetwork=eth&fromAmount={}&toCurrency=usdt&toNetwork=eth&type=direct".format(
                    amount
                )
                response = requests.get(url)

            except Exception as ex:
                print(ex)
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Something went wrong in server side",
                )

            if response.status_code != 200:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invaild access token",
                )

            data = json.loads(response.content.decode("utf-8"))

            if data["summary"]["estimatedAmount"] == None:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST, detail="Too low amount"
                )

            return data["summary"]["estimatedAmount"]

        @router.get(
            "/price/eth/usdt/output",
            summary="Returns the amount of ETH need to deposit for exact USDT",
        )
        async def get_price_eth_usdt_output(amount: float) -> float:
            try:
                url = "https://vip-api.changenow.io/v1.2/exchange/estimate?fromCurrency=eth&fromNetwork=eth&toAmount={}&toCurrency=usdt&toNetwork=eth&flow=fixed-rate&type=reverse".format(
                    amount
                )
                response = requests.get(url)

            except Exception as ex:
                print(ex)
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Something went wrong in server side",
                )
            if response.status_code != 200:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invaild access token",
                )

            data = json.loads(response.content.decode("utf-8"))

            if data["summary"]["estimatedAmount"] == None:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST, detail="Too low amount"
                )
            return data["summary"]["estimatedAmount"]

        @router.get(
            "/price/sol/usdt/input",
            summary="Returns the amount of USDT you get for exact SOL",
        )
        async def get_price_sol_usdt_input(amount: float) -> float:
            try:
                url = "https://vip-api.changenow.io/v1.2/exchange/estimate?fromCurrency=sol&fromNetwork=sol&fromAmount={}&toCurrency=usdt&toNetwork=eth&type=direct".format(
                    amount
                )
                response = requests.get(url)

            except Exception as ex:
                print(ex)
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Something went wrong in server side",
                )

            if response.status_code != 200:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invaild access token",
                )

            data = json.loads(response.content.decode("utf-8"))

            if data["summary"]["estimatedAmount"] == None:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST, detail="Too low amount"
                )

            return data["summary"]["estimatedAmount"]

        @router.get(
            "/price/sol/usdt/output",
            summary="Returns the amount of SOL need to deposit for exact USDT",
        )
        async def get_price_sol_usdt_output(amount: float) -> float:
            try:
                url = "https://vip-api.changenow.io/v1.2/exchange/estimate?fromCurrency=sol&fromNetwork=sol&toCurrency=usdt&toNetwork=eth&toAmount={}&flow=fixed-rate&type=reverse".format(
                    amount
                )
                print(url)
                response = requests.get(url)

            except Exception as ex:
                print(ex)
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Something went wrong in server side",
                )

            if response.status_code != 200:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invaild access token",
                )

            data = json.loads(response.content.decode("utf-8"))

            if data["summary"]["estimatedAmount"] == None:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST, detail="Too low amount"
                )

            return data["summary"]["estimatedAmount"]

        @router.get(
            "/price/usdt/eth/input",
            summary="Returns the amount of USDT you get for exact ETH",
        )
        async def get_price_usdt_eth_input(amount: float) -> float:
            try:
                url = "https://vip-api.changenow.io/v1.2/exchange/estimate?fromCurrency=usdt&fromNetwork=eth&fromAmount={}&toCurrency=eth&toNetwork=eth&type=direct".format(
                    amount
                )
                response = requests.get(url)

            except Exception as ex:
                print(ex)
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Something went wrong in server side",
                )

            if response.status_code != 200:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invaild access token",
                )

            data = json.loads(response.content.decode("utf-8"))

            if data["summary"]["estimatedAmount"] == None:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST, detail="Too low amount"
                )

            return data["summary"]["estimatedAmount"]

        @router.get(
            "/price/usdt/eth/output",
            summary="Returns the amount of ETH need to deposit for exact USDT",
        )
        async def get_price_usdt_eth_output(amount: float) -> float:
            try:
                url = "https://vip-api.changenow.io/v1.2/exchange/estimate?fromCurrency=usdt&fromNetwork=eth&toAmount={}&toCurrency=eth&toNetwork=eth&flow=fixed-rate&type=reverse".format(
                    amount
                )
                response = requests.get(url)

            except Exception as ex:
                print(ex)
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Something went wrong in server side",
                )
            if response.status_code != 200:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invaild access token",
                )

            data = json.loads(response.content.decode("utf-8"))

            if data["summary"]["estimatedAmount"] == None:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST, detail="Too low amount"
                )
            return data["summary"]["estimatedAmount"]

        @router.get(
            "/price/usdt/sol/input",
            summary="Returns the amount of USDT you get for exact SOL",
        )
        async def get_price_usdt_sol_input(amount: float) -> float:
            try:
                url = "https://vip-api.changenow.io/v1.2/exchange/estimate?fromCurrency=usdt&fromNetwork=eth&fromAmount={}&toCurrency=sol&toNetwork=sol&type=direct".format(
                    amount
                )
                response = requests.get(url)

            except Exception as ex:
                print(ex)
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Something went wrong in server side",
                )

            if response.status_code != 200:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invaild access token",
                )

            data = json.loads(response.content.decode("utf-8"))

            if data["summary"]["estimatedAmount"] == None:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST, detail="Too low amount"
                )

            return data["summary"]["estimatedAmount"]

        @router.get(
            "/price/usdt/sol/output",
            summary="Returns the amount of SOL need to deposit for exact USDT",
        )
        async def get_price_usdt_sol_output(amount: float) -> float:
            try:
                url = "https://vip-api.changenow.io/v1.2/exchange/estimate?fromCurrency=usdt&fromNetwork=eth&toCurrency=sol&toNetwork=sol&toAmount={}&flow=fixed-rate&type=reverse".format(
                    amount
                )
                print(url)
                response = requests.get(url)

            except Exception as ex:
                print(ex)
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Something went wrong in server side",
                )

            if response.status_code != 200:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invaild access token",
                )

            data = json.loads(response.content.decode("utf-8"))

            if data["summary"]["estimatedAmount"] == None:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST, detail="Too low amount"
                )

            return data["summary"]["estimatedAmount"]

        @router.get("/deposit_wallet/eth", summary="Return deposit wallet data")
        async def deposit_eth(
            amount: float,
            payload: TokenPayload = Depends(get_current_user_from_oauth),
            session: Session = Depends(get_db_session),
        ) -> float:
            if amount == 0:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Amount must be more than 0",
                )
            response = cnio_api(
                "CREATE_TX",
                api_key=cfg.CN_API_KEY,
                from_ticker="eth",
                to_ticker="usdterc20",
                address=cfg.ETH_TREASURY_ADDRESS,
                amount=amount,
            )

            transaction = Transaction()
            transaction.user_id = payload.sub
            transaction.amount_in = amount
            transaction.amount_out = response["amount"]
            transaction.method = DWMethod.Eth
            transaction.transaction_id = response["id"]

            session.add(transaction)

            return response["payinAddress"]

        @router.get("/deposit_wallet/sol", summary="Return deposit wallet data")
        async def deposit_sol(
            amount: float,
            payload: TokenPayload = Depends(get_current_user_from_oauth),
            session: Session = Depends(get_db_session),
        ) -> float:
            if amount == 0:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Amount must be more than 0",
                )
            response = cnio_api(
                "CREATE_TX",
                api_key=cfg.CN_API_KEY,
                from_ticker="sol",
                to_ticker="usdterc20",
                address=cfg.ETH_TREASURY_ADDRESS,
                amount=amount,
            )

            transaction = Transaction()
            transaction.user_id = payload.sub
            transaction.amount_in = amount
            transaction.amount_out = response["amount"]
            transaction.method = DWMethod.Sol
            transaction.transaction_id = response["id"]

            session.add(transaction)

            return response["payinAddress"]

        @router.post("/withdraw/eth", summary="Withdraw crypto with eth")
        async def withdraw_eth(
            amount: float,
            address: str = Query(regex="0x[a-zA-Z0-9]{40}"),
            payload: TokenPayload = Depends(get_current_user_from_oauth),
            session: Session = Depends(get_db_session),
        ):
            if amount == 0:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Amount must be more than 0",
                )
            response = cnio_api(
                "CREATE_TX",
                api_key=cfg.CN_API_KEY,
                from_ticker="usdterc20",
                to_ticker="eth",
                address=address,
                amount=amount,
            )

            send_eth_stable_to(cfg.ETH_USDT_ADDRESS, response["payinAddress"], amount)

            transaction = Transaction()
            transaction.user_id = payload.sub
            transaction.amount_in = amount
            transaction.amount_out = response["amount"]
            transaction.method = DWMethod.Eth
            transaction.direct = Direct.Withdraw
            transaction.transaction_id = response["id"]

            session.add(transaction)

            user: User = session.query(User).filter(User.id == payload.sub).one()
            user.balance -= amount
            user.withdraw_balance += amount

            return

        @router.get("/records", summary="Return all records of user")
        async def get_records(
            offset: int = 0,
            count: int = 10,
            payload: TokenPayload = Depends(get_current_user_from_oauth),
            session: Session = Depends(get_db_session),
        ):
            records = list(
                session.query(Transaction)
                .filter(Transaction.user_id == payload.sub)
                .offset(offset)
                .limit(count)
            )
            return records

        @router.get("/nft/wallet/eth", summary="Get all nft data from wallet address")
        async def get_nft_eth(
            address: str = Query(regex="0x[a-zA-Z0-9]{40}"),
            payload: TokenPayload = Depends(get_current_user_from_oauth),
            session: Session = Depends(get_db_session),
        ):
            nfts = self.opensea.assets(owner=address, order_by="sale_date")

            response_data = []

            try:
                for nft in list(nfts["assets"]):
                    data = {
                        "imageUrl": nft["image_url"],
                        "name": nft["name"],
                        "openseaId": nft["id"],
                        "contractAddress": nft["asset_contract"]["address"],
                        "contractType": nft["asset_contract"]["schema_name"],
                        "tokenId": nft["token_id"],
                        "price": 0,
                    }

                    if nft["last_sale"] != None:
                        data["price"] = (
                            float(nft["last_sale"]["total_price"])
                            / (10 ** nft["last_sale"]["payment_token"]["decimals"])
                            * float(nft["last_sale"]["payment_token"]["usd_price"])
                        )

                        response_data.append(data)
            except:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Too many request",
                )

            return response_data

        @router.get("/nft/wallet/sol", summary="Get all nft data from wallet address")
        async def get_nft_sol(
            address: str,
            payload: TokenPayload = Depends(get_current_user_from_oauth),
            session: Session = Depends(get_db_session),
        ):
            url = (
                "https://api-mainnet.magiceden.dev/v2/wallets/{}/tokens?limit=4".format(
                    address
                )
            )

            try:
                response = requests.get(url)
                tokens = json.loads(response.content.decode("utf-8"))
                url = "https://api.coingecko.com/api/v3/simple/price?ids=solana&vs_currencies=usd"
                response = requests.get(url)
                sol_price = json.loads(response.content.decode("utf-8"))["solana"][
                    "usd"
                ]
            except:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Something went wrong in server side",
                )

            response_data = []
            # try:
            for token in tokens:
                url = (
                    "https://api.solscan.io/nft/trade?mint={}&offset=0&limit=1".format(
                        token["mintAddress"]
                    )
                )
                try:
                    response = requests.get(url)
                    trade_data = json.loads(response.content.decode("utf-8"))
                except:
                    continue

                data = {
                    "address": token["mintAddress"],
                    "imageUrl": token["image"],
                    "name": token["name"],
                    "price": 0,
                }

                if len(trade_data["data"]) == 1:
                    data["price"] = (
                        float(trade_data["data"][0]["price"]) / 10**9 * sol_price
                    )

                    response_data.append(data)

            # except:
            #     raise HTTPException(
            #         status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            #         detail="Too many request",
            #     )

            return response_data

        @router.get("/eth/treasury", summary="Return ethereum treasury address")
        async def get_treasury():
            return cfg.ETH_TREASURY_ADDRESS

        @router.get("/sol/treasury", summary="Return solana treasury address")
        async def get_treasury():
            return cfg.SOL_TREASURY_ADDRESS

        # @router.get("/deposit_wallet/sol", summary="Return deposit wallet data")
        # async def deposit_eth_eth(
        #     payload: TokenPayload = Depends(get_current_user_from_oauth),
        #     session: Session = Depends(get_db_session),
        # ) -> float:

        #     wallet: WalletData = get_sol_deposit_wallet()
        #     wallet.user_id = payload.sub
        #     wallet.timestamp = datetime.today().timestamp()
        #     wallet.is_using = True

        #     return wallet.public_key

        # @router.post("/deposit/eth/eth", summary="Deposit eth manually")
        # async def deposit_eth_manually(
        #     tx_hash: str = Query(default=None, regex="0x[a-z0-9]{64}"),
        #     payload: TokenPayload = Depends(get_current_user_from_oauth),
        #     session: Session = Depends(get_db_session),
        # ) -> float:
        #     if tx_hash == None:
        #         raise HTTPException(
        #             status_code=status.HTTP_400_BAD_REQUEST,
        #             detail="You need to set hash",
        #         )

        #     if (
        #         len(list(session.query(DWHistory).filter(DWHistory.tx_hash == tx_hash)))
        #         > 0
        #     ):
        #         raise HTTPException(
        #             status_code=status.HTTP_400_BAD_REQUEST, detail="Already registered"
        #         )

        #     tx_data = get_transaction_eth_value(tx_hash)
        #     if not compare_eth_address(tx_data["to"], cfg.ETH_TREASURY_ADDRESS):
        #         raise HTTPException(
        #             status_code=status.HTTP_400_BAD_REQUEST,
        #             detail="Invalid transfer-didn't send to treasury",
        #         )

        #     fee = get_current_gas_price() * int(cfg.ETH_SWAP_FEE)
        #     tx = self.uniswap.make_trade(
        #         eth, eth_usdt, int(to_wei(tx_data["value"], "wei") - fee)
        #     )
        #     receipt = wait_transaction_receipt(tx)

        #     received = float(int(receipt.logs[2].data, 16)) / 10**6

        #     new_history = DWHistory()
        #     new_history.tx_hash = tx_hash
        #     new_history.user_id = payload.sub
        #     new_history.direct = Direct.Deposit
        #     new_history.deposit_method = DWMethod.Eth
        #     new_history.amount = received

        #     session.add(new_history)

        #     user: User = session.query(User).filter(User.id == payload.sub).first()
        #     user.balance += received

        #     session.commit()
        #     return new_history

        # @router.post("/deposit/eth/stable", summary="Deposit stable coin manually")
        # async def deposit_eth_stable_manually(
        #     tx_hash: str = Query(default=None, regex="0x[a-z0-9]{64}"),
        #     payload: TokenPayload = Depends(get_current_user_from_oauth),
        #     session: Session = Depends(get_db_session),
        # ) -> float:
        #     if tx_hash == None:
        #         raise HTTPException(
        #             status_code=status.HTTP_400_BAD_REQUEST,
        #             detail="You need to set hash",
        #         )

        #     if (
        #         len(list(session.query(DWHistory).filter(DWHistory.tx_hash == tx_hash)))
        #         > 0
        #     ):
        #         raise HTTPException(
        #             status_code=status.HTTP_400_BAD_REQUEST, detail="Already registered"
        #         )

        #     tx_data = get_transaction_token_value(tx_hash)

        #     if not compare_eth_address(
        #         tx_data["contract"], eth_usdt
        #     ) and not compare_eth_address(tx_data["contract"], eth_usdc):
        #         raise HTTPException(
        #             status_code=status.HTTP_400_BAD_REQUEST,
        #             detail="Invalid transfer-not USDT",
        #         )

        #     if not compare_eth_address(tx_data["to"], cfg.ETH_TREASURY_ADDRESS):
        #         raise HTTPException(
        #             status_code=status.HTTP_400_BAD_REQUEST,
        #             detail="Invalid transfer-didn't send to treasury",
        #         )

        #     fee = get_current_gas_price() * int(cfg.ETH_SWAP_FEE)
        #     fee_usdt = (
        #         float(self.uniswap.get_price_output(eth_usdt, eth, fee)) / 10**6
        #     )
        #     received = float(int(tx_data["value"], 16) - fee_usdt) / 10**6

        #     new_history = DWHistory()
        #     new_history.tx_hash = tx_hash
        #     new_history.user_id = payload.sub
        #     new_history.direct = Direct.Deposit

        #     if tx_data["contract"] == cfg.ETH_USDT_ADDRESS:
        #         new_history.deposit_method = DWMethod.Usdt
        #     elif tx_data["contract"] == cfg.ETH_USDC_ADDRESS:
        #         new_history.deposit_method = DWMethod.Usdc

        #     new_history.amount = received

        #     session.add(new_history)

        #     user: User = session.query(User).filter(User.id == payload.sub).first()
        #     user.balance += received

        #     session.commit()
        #     return new_history

        # @router.post("/deposit/eth/nft", summary="Deposit stable coin manually")
        # async def deposit_eth_nft_manually(
        #     tx_hash: str = Query(default=None, regex="0x[a-z0-9]{64}"),
        #     payload: TokenPayload = Depends(get_current_user_from_oauth),
        #     session: Session = Depends(get_db_session),
        # ):
        #     if tx_hash == None:
        #         raise HTTPException(
        #             status_code=status.HTTP_400_BAD_REQUEST,
        #             detail="You need to set hash",
        #         )

        #     if len(list(session.query(NFT).filter(NFT.deposit_tx_hash == tx_hash))) > 0:
        #         raise HTTPException(
        #             status_code=status.HTTP_400_BAD_REQUEST, detail="Already registered"
        #         )

        #     tx_data = get_transaction_nft_data(tx_hash)

        #     deposited = []
        #     for log in tx_data:
        #         # if not compare_eth_address(log.topics[2], cfg.ETH_TREASURY_ADDRESS):
        #         #   continue

        #         if log.data == "0x":
        #             # erc721 nft
        #             new_nft = NFT()
        #             new_nft.user_id = payload.sub
        #             new_nft.deposit_tx_hash = tx_hash
        #             new_nft.token_address = log.address
        #             new_nft.token_id = int(log.topics[3].hex(), 16)
        #             new_nft.price = 0
        #             new_nft.network = Network.Ethereum
        #             new_nft.nft_type = NFTType.ERC721

        #             session.add(new_nft)
        #             session.flush()
        #             session.refresh(new_nft, attribute_names=["id"])

        #             new_history = NFTHistory()
        #             new_history.nft_id = new_nft.id
        #             new_history.after_user_id = payload.sub
        #             new_history.note = NFTNote.Deposit
        #             new_history.price = new_nft.price

        #             session.add(new_history)
        #             session.flush()
        #             deposited.append(new_nft)

        #         elif log.topics[0].hex() == ETH_ERC1155_TRANSFER_TOPIC:
        #             (token_id, amount) = erc1155_data_dispatch(log.data)

        #             for _ in range(amount):
        #                 new_nft = NFT()
        #                 new_nft.user_id = payload.sub
        #                 new_nft.deposit_tx_hash = tx_hash
        #                 new_nft.token_address = log.address
        #                 new_nft.token_id = token_id
        #                 new_nft.price = 0
        #                 new_nft.network = Network.Ethereum
        #                 new_nft.nft_type = NFTType.ERC1155

        #                 session.add(new_nft)
        #                 session.flush()
        #                 session.refresh(new_nft, attribute_names=["id"])

        #                 new_history = NFTHistory()
        #                 new_history.nft_id = new_nft.id
        #                 new_history.after_user_id = payload.sub
        #                 new_history.note = NFTNote.Deposit
        #                 new_history.price = new_nft.price

        #                 session.add(new_history)
        #                 session.flush()
        #                 deposited.append(new_nft)

        #     return deposited

        # @router.post("/withdraw/eth/eth", summary="Withdraw money with ETH")
        # async def withdraw_eth_eth(
        #     amount: float = Query(default=0),
        #     wallet: str = Query(default=None, regex="0x[A-Za-z0-9]{40}"),
        #     payload: TokenPayload = Depends(get_current_user_from_oauth),
        #     session: Session = Depends(get_db_session),
        # ) -> float:
        #     if amount == 0:
        #         raise HTTPException(
        #             status_code=status.HTTP_400_BAD_REQUEST,
        #             detail="You need to set amount more than 0",
        #         )

        #     user: User = session.query(User).filter(User.id == payload.sub).first()

        #     fee = get_current_gas_price() * int(cfg.ETH_SWAP_FEE)
        #     total_eth = (
        #         self.uniswap.get_price_input(eth_usdt, eth, (user.balance) * 10**6)
        #         - fee
        #     )

        #     if amount > total_eth:
        #         raise HTTPException(
        #             status_code=status.HTTP_400_BAD_REQUEST,
        #             detail="Much than real amount",
        #         )

        #     delta_balance = (
        #         float(
        #             self.uniswap.get_price_output(eth_usdt, eth, amount * 10**18)
        #             + fee
        #         )
        #         / 10**6
        #     )
        #     user.balance -= delta_balance
        #     user.withdraw_balance += delta_balance

        #     new_history = DWHistory()
        #     new_history.amount = delta_balance
        #     new_history.direct = Direct.Withdraw
        #     new_history.user_id = payload.sub

        #     session.add(new_history)

        #     tx = self.uniswap.make_trade_output(
        #         eth_usdt, eth, amount * 10**18, wallet
        #     )
        #     receipt = wait_transaction_receipt(tx)

        #     return receipt

        # @router.post("/withdraw/eth/usdt", summary="Withdraw money with USDT")
        # async def withdraw_eth(
        #     amount: float = Query(default=0),
        #     wallet: str = Query(default=None, regex="0x[A-Za-z0-9]{40}"),
        #     payload: TokenPayload = Depends(get_current_user_from_oauth),
        #     session: Session = Depends(get_db_session),
        # ) -> float:
        #     if amount == 0:
        #         raise HTTPException(
        #             status_code=status.HTTP_400_BAD_REQUEST,
        #             detail="You need to set amount more than 0",
        #         )

        #     user: User = session.query(User).filter(User.id == payload.sub).first()

        #     fee = get_current_gas_price() * int(cfg.ETH_SWAP_FEE)
        #     fee_usdt = (
        #         float(self.uniswap.get_price_output(eth_usdt, eth, fee)) / 10**6
        #     )

        #     if amount + fee_usdt > user.balance:
        #         raise HTTPException(
        #             status_code=status.HTTP_400_BAD_REQUEST,
        #             detail="Much than real amount",
        #         )

        #     try:
        #         receipt = send_eth_stable_to(eth_usdt, wallet, amount)
        #     except Exception as ex:
        #         print(ex)
        #         raise HTTPException(
        #             status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        #             detail="Some error occured in server side",
        #         )

        #     delta_balance = amount + fee_usdt
        #     user.balance -= delta_balance
        #     user.withdraw_balance += delta_balance

        #     new_history = DWHistory()
        #     new_history.amount = delta_balance
        #     new_history.direct = Direct.Withdraw
        #     new_history.user_id = payload.sub

        #     session.add(new_history)
        #     return receipt["blockHash"].hex()

        # @router.post("/withdraw/eth/usdc", summary="Withdraw money with USDC")
        # async def withdraw_eth(
        #     amount: float = Query(default=0),
        #     wallet: str = Query(default=None, regex="0x[A-Za-z0-9]{40}"),
        #     payload: TokenPayload = Depends(get_current_user_from_oauth),
        #     session: Session = Depends(get_db_session),
        # ) -> float:
        #     if amount == 0:
        #         raise HTTPException(
        #             status_code=status.HTTP_400_BAD_REQUEST,
        #             detail="You need to set amount more than 0",
        #         )

        #     user: User = session.query(User).filter(User.id == payload.sub).first()

        #     fee = get_current_gas_price() * int(cfg.ETH_SWAP_FEE)
        #     fee_usdt = (
        #         float(self.uniswap.get_price_output(eth_usdc, eth, fee)) / 10**6
        #     )

        #     if amount + fee_usdt > user.balance:
        #         raise HTTPException(
        #             status_code=status.HTTP_400_BAD_REQUEST,
        #             detail="Much than real amount",
        #         )

        #     try:
        #         receipt = send_eth_stable_to(eth_usdc, wallet, amount)
        #     except Exception as ex:
        #         print(ex)
        #         raise HTTPException(
        #             status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        #             detail="Some error occured in server side",
        #         )

        #     delta_balance = amount + fee_usdt
        #     user.balance -= delta_balance
        #     user.withdraw_balance += delta_balance

        #     new_history = DWHistory()
        #     new_history.amount = delta_balance
        #     new_history.direct = Direct.Withdraw
        #     new_history.user_id = payload.sub

        #     session.add(new_history)
        #     return receipt["blockHash"].hex()

        # @router.post("/withdraw/sol/sol", summary="Withdraw money with sol")
        # async def withdraw_sol_sool(
        #     amount: float = Query(default=0),
        #     wallet: str = Query(default=None, regex="[A-Za-z0-9]{42-44}"),
        #     payload: TokenPayload = Depends(get_current_user_from_oauth),
        #     session: Session = Depends(get_db_session),
        # ) -> float:
        #     if amount == 0:
        #         raise HTTPException(
        #             status_code=status.HTTP_400_BAD_REQUEST,
        #             detail="You need to set amount more than 0",
        #         )

        #     user: User = session.query(User).filter(User.id == payload.sub).first()

        #     fee = get_current_gas_price() * int(cfg.ETH_SWAP_FEE)
        #     total_eth = (
        #         self.uniswap.get_price_input(eth_usdt, eth, (user.balance) * 10**6)
        #         - fee
        #     )

        #     if amount > total_eth:
        #         raise HTTPException(
        #             status_code=status.HTTP_400_BAD_REQUEST,
        #             detail="Much than real amount",
        #         )

        #     delta_balance = (
        #         float(
        #             self.uniswap.get_price_output(eth_usdt, eth, amount * 10**18)
        #             + fee
        #         )
        #         / 10**6
        #     )
        #     user.balance -= delta_balance
        #     user.withdraw_balance += delta_balance

        #     new_history = DWHistory()
        #     new_history.amount = delta_balance
        #     new_history.direct = Direct.Withdraw
        #     new_history.user_id = payload.sub

        #     session.add(new_history)

        #     tx = self.uniswap.make_trade_output(
        #         eth_usdt, eth, amount * 10**18, wallet
        #     )
        #     receipt = wait_transaction_receipt(tx)

        #     return receipt

        app.include_router(router)
