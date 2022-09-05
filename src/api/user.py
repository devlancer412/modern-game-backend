from __future__ import annotations
from dataclasses import Field
from itertools import count
from operator import and_, or_
from typing import Callable

from app.__internal import Function
from fastapi import FastAPI, APIRouter, Query, status, HTTPException, Depends
from sqlalchemy.orm import Session
import requests
import json

from src.dependencies.auth_deps import get_current_user_from_oauth
from src.dependencies.database_deps import get_db_session
from src.models import (
    NFT,
    Avatar,
    DWMethod,
    Direct,
    NFTHistory,
    NFTNote,
    NFTType,
    Network,
    Transaction,
    User,
)
from src.schemas.auth import TokenPayload

from config import cfg
from src.schemas.user import UserUpdateData

from src.changenow_api.client import api_wrapper as cnio_api
from opensea import OpenseaAPI
from src.utils.solana_web3 import (
    get_solana_nft_transaction_data,
    is_owner_of_nft,
    transfer_solana_nft,
)

from src.utils.web3 import (
    ETH_ERC1155_TRANSFER_TOPIC,
    compare_eth_address,
    erc1155_data_dispatch,
    get_current_gas_price,
    get_transaction_nft_data,
    send_eth_erc1155_to,
    send_eth_erc721_to,
    send_eth_stable_to,
    wait_transaction_receipt,
)
from src.celery import dispatch_transaction


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

            fee = (
                get_current_gas_price()
                * int(cfg.ETH_MAX_FEE)
                / 10**18
                * (await get_price_eth())
            )

            amount -= fee
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

            fee = (
                get_current_gas_price()
                * int(cfg.ETH_MAX_FEE)
                / 10**18
                * (await get_price_eth())
            )

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
            return data["summary"]["estimatedAmount"] + fee

        @router.get(
            "/price/usdt/sol/input",
            summary="Returns the amount of USDT you get for exact SOL",
        )
        async def get_price_usdt_sol_input(amount: float) -> float:

            fee = (
                get_current_gas_price()
                * int(cfg.ETH_MAX_FEE)
                / 10**18
                * (await get_price_eth())
            )

            amount -= fee
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

            fee = (
                get_current_gas_price()
                * int(cfg.ETH_MAX_FEE)
                / 10**18
                * (await get_price_eth())
            )

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

            return data["summary"]["estimatedAmount"] + fee

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

            dispatch_transaction.delay(int(response["id"], 16))
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

            dispatch_transaction.delay(int(response["id"], 16))
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
            user: User = session.query(User).filter(User.id == payload.sub).one()

            if user.balance < amount:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST, detail="amount exceeded"
                )

            fee = (
                get_current_gas_price()
                * int(cfg.ETH_MAX_FEE)
                / 10**18
                * (await get_price_eth())
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

            user.balance -= amount
            user.withdraw_balance += amount

            return

        @router.get("/history/crypto", summary="Return all records of user")
        async def get_records(
            offset: int = 0,
            count: int = 10,
            payload: TokenPayload = Depends(get_current_user_from_oauth),
            session: Session = Depends(get_db_session),
        ):
            total = (
                session.query(Transaction)
                .filter(Transaction.user_id == payload.sub)
                .count()
            )
            records = list(
                session.query(Transaction)
                .filter(Transaction.user_id == payload.sub)
                .offset(offset)
                .limit(count)
            )
            return {"records": records, "total": total}

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

        @router.get("/eth/treasury", summary="Return ethereum treasury address")
        async def get_treasury():
            return cfg.ETH_TREASURY_ADDRESS

        @router.post("/deposit/nft/eth", summary="Deposit Ethereum NFT")
        async def deposit_eth_nft(
            tx_hash: str = Query(default=None, regex="0x[a-z0-9]{64}"),
            payload: TokenPayload = Depends(get_current_user_from_oauth),
            session: Session = Depends(get_db_session),
        ):
            if tx_hash == None:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="You need to set hash",
                )

            if (
                len(
                    list(
                        session.query(NFTHistory).filter(
                            NFTHistory.transaction_hash == tx_hash
                        )
                    )
                )
                > 0
            ):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST, detail="Already registered"
                )

            wait_transaction_receipt(tx_hash)
            tx_data = get_transaction_nft_data(tx_hash)

            deposited = []
            for log in tx_data:
                if not compare_eth_address(log.topics[2], cfg.ETH_TREASURY_ADDRESS):
                    continue

                if log.data == "0x":
                    # erc721 nft
                    token_address = log.address
                    token_id = int(log.topics[3].hex(), 16)
                    nft_type = NFTType.ERC721
                    amount = 1

                elif log.topics[0].hex() == ETH_ERC1155_TRANSFER_TOPIC:
                    (token_id, amount) = erc1155_data_dispatch(log.data)
                    token_address = log.address
                    nft_type = NFTType.ERC1155
                    response = self.opensea.asset(log.address, token_id)

                else:
                    continue

                price = 0
                if nft_type == NFTType.ERC721:
                    last_nfts: list[NFT] = list(
                        session.query(NFT)
                        .filter(
                            and_(
                                NFT.token_address == token_address,
                                NFT.token_id == token_id,
                            )
                        )
                        .all()
                    )

                    if (
                        len(list(filter(lambda nft: nft.deleted == False, last_nfts)))
                        > 0
                    ):
                        raise HTTPException(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Already registered NFT",
                        )
                    if len(last_nfts) > 0:
                        price = last_nfts[len(last_nfts) - 1].price

                for _ in range(amount):

                    new_nft = NFT()
                    new_nft.user_id = payload.sub
                    new_nft.token_address = token_address
                    new_nft.token_id = token_id
                    new_nft.price = price
                    new_nft.network = Network.Ethereum
                    new_nft.nft_type = nft_type

                    try:
                        response = self.opensea.asset(token_address, token_id)
                        new_nft.image_url = response["image_url"]
                        new_nft.name = response["name"]

                        if response["last_sale"] != None:
                            opensea_price = (
                                float(response["last_sale"]["total_price"])
                                / (
                                    10
                                    ** response["last_sale"]["payment_token"][
                                        "decimals"
                                    ]
                                )
                                * float(
                                    response["last_sale"]["payment_token"]["usd_price"]
                                )
                            )
                            if opensea_price > price:
                                new_nft.price = opensea_price
                    except:
                        raise HTTPException(
                            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail="Something went wrong on server side, Please retry",
                        )

                    session.add(new_nft)
                    session.flush()
                    session.refresh(new_nft, attribute_names=["id"])

                    new_history = NFTHistory()
                    new_history.nft_id = new_nft.id
                    new_history.after_user_id = payload.sub
                    new_history.note = NFTNote.Deposit
                    new_history.price = new_nft.price
                    new_history.transaction_hash = tx_hash

                    session.add(new_history)
                    session.flush()
                    deposited.append(new_nft)

            return deposited

        @router.post("/withdraw/nft/eth", summary="Withdraw Ethereum NFT")
        async def withdraw_nft_eth(
            id: int,
            address: str = Query(regex="0x[a-zA-Z0-9]{40}"),
            payload: TokenPayload = Depends(get_current_user_from_oauth),
            session: Session = Depends(get_db_session),
        ):
            user_id = int(payload.sub)
            nft: NFT = (
                session.query(NFT)
                .filter(and_(NFT.id == id, NFT.deleted == False))
                .one()
            )

            if nft == None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND, detail="Can't find such NFT"
                )

            if nft.user_id != user_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST, detail="Not your NFT"
                )

            if nft.nft_type == NFTType.ERC721:
                tx = send_eth_erc721_to(address, nft.token_address, nft.token_id)
            else:
                tx = send_eth_erc1155_to(address, nft.token_address, nft.token_id)

            nft_history = NFTHistory()
            nft_history.before_user_id = user_id
            nft_history.nft_id = id
            nft_history.price = nft.price
            nft_history.note = NFTNote.Withdraw
            nft_history.transaction_hash = tx["blockHash"]

            session.add(nft_history)

            nft.deleted = True

        @router.get("/list/nft/eth", summary="Get ETH NFT list")
        async def get_eth_nft_list(
            payload: TokenPayload = Depends(get_current_user_from_oauth),
            session: Session = Depends(get_db_session),
        ):
            nfts: list[NFT] = list(
                session.query(NFT)
                .filter(
                    and_(
                        and_(
                            NFT.user_id == payload.sub, NFT.network == Network.Ethereum
                        ),
                        NFT.deleted == False,
                    )
                )
                .all()
            )

            response_data = []
            for nft in nfts:
                data = {
                    "id": nft.id,
                    "imageUrl": nft.image_url,
                    "price": nft.price,
                }
                response_data.append(data)

            return response_data

        @router.get("/history/nft/eth", summary="Get Ethereum NFT history")
        async def get_eth_nft_history(
            offset: int = 0,
            count: int = 10,
            payload: TokenPayload = Depends(get_current_user_from_oauth),
            session: Session = Depends(get_db_session),
        ):
            total = (
                session.query(NFTHistory, NFT)
                .filter(
                    and_(
                        and_(
                            NFT.id == NFTHistory.nft_id, NFT.network == Network.Ethereum
                        ),
                        or_(
                            NFTHistory.before_user_id == payload.sub,
                            NFTHistory.after_user_id == payload.sub,
                        ),
                    )
                )
                .count()
            )
            histories: list[any] = list(
                session.query(NFTHistory, NFT)
                .filter(
                    and_(
                        and_(
                            NFT.id == NFTHistory.nft_id, NFT.network == Network.Ethereum
                        ),
                        or_(
                            NFTHistory.before_user_id == payload.sub,
                            NFTHistory.after_user_id == payload.sub,
                        ),
                    )
                )
                .offset(offset)
                .limit(count)
            )

            response_data = []
            for (history, nft) in histories:
                print(history, nft)
                data = {
                    "imageUrl": nft.image_url,
                    "name": nft.name,
                    "created_at": history.created_at,
                    "transactionHash": history.transaction_hash,
                    "note": history.note,
                    "price": history.price,
                }
                response_data.append(data)

            return {"total": total, "records": response_data}

        @router.post("/deposit/nft/sol", summary="Deposit Solana NFT")
        async def deposit_eth_nft(
            tx_sig: str,
            payload: TokenPayload = Depends(get_current_user_from_oauth),
            session: Session = Depends(get_db_session),
        ):
            # get nft transfer transaction data
            tx_datas = await get_solana_nft_transaction_data(tx_sig)
            # get current solana price
            url = "https://api.coingecko.com/api/v3/simple/price?ids=solana&vs_currencies=usd"
            response = requests.get(url)
            sol_price = json.loads(response.content.decode("utf-8"))["solana"]["usd"]
            # loop nfts
            for tx_data in tx_datas:
                if not await is_owner_of_nft(
                    tx_data["token"], cfg.SOL_TREASURY_ADDRESS, tx_data["to"]
                ):
                    continue

                last_nfts: list[NFT] = list(
                    session.query(NFT)
                    .filter(
                        and_(
                            NFT.token_address == tx_data["token"],
                            NFT.network == Network.Solana,
                        )
                    )
                    .all()
                )

                if len(list(filter(lambda nft: nft.deleted == False, last_nfts))) > 0:
                    continue
                # get nft metadata by magic eden api
                url = "https://api-mainnet.magiceden.dev/v2/tokens/{}".format(
                    tx_data["token"]
                )

                response = requests.get(url)
                nft_data = json.loads(response.content.decode("utf-8"))

                # create new nft
                new_nft = NFT()
                new_nft.name = nft_data["name"]
                new_nft.image_url = nft_data["image"]
                new_nft.token_address = tx_data["token"]
                new_nft.network = Network.Solana
                new_nft.user_id = payload.sub
                new_nft.price = 0
                # get last price
                if len(last_nfts) > 0:
                    new_nft.price = last_nfts[len(last_nfts) - 1].price
                # get trade price
                url = (
                    "https://api.solscan.io/nft/trade?mint={}&offset=0&limit=1".format(
                        tx_data["token"]
                    )
                )
                response = requests.get(url)
                trade_data = json.loads(response.content.decode("utf-8"))

                if len(list(trade_data["data"])) > 0:
                    price = float(trade_data["data"][0]["price"]) / 10**9 * sol_price
                    if price > new_nft.price:
                        new_nft.price = price

                session.add(new_nft)
                session.flush()
                session.refresh(new_nft, attribute_names=["id"])

                new_history = NFTHistory()
                new_history.after_user_id = payload.sub
                new_history.nft_id = new_nft.id
                new_history.note = NFTNote.Deposit
                new_history.transaction_hash = tx_sig
                new_history.price = new_nft.price

                session.add(new_history)

            return tx_datas

        @router.get("/sol/treasury", summary="Return solana treasury address")
        async def get_treasury():
            return cfg.SOL_TREASURY_ADDRESS

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
            try:
                for token in tokens:
                    if token["listStatus"] == "listed":
                        continue

                    url = "https://api.solscan.io/nft/trade?mint={}&offset=0&limit=1".format(
                        token["mintAddress"]
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

            except:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Too many request",
                )

            return response_data

        @router.post("/withdraw/nft/sol", summary="Withdraw Solana NFT")
        async def withdraw_nft_sol(
            id: int,
            address: str,
            payload: TokenPayload = Depends(get_current_user_from_oauth),
            session: Session = Depends(get_db_session),
        ):
            nft: NFT = (
                session.query(NFT)
                .filter(and_(NFT.id == id, NFT.deleted == False))
                .one()
            )

            if nft == None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND, detail="Not found such NFT"
                )

            if nft.user_id != int(payload.sub):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Not owner of that NFT",
                )

            try:
                tx_data = await transfer_solana_nft(nft.token_address, address)
            except:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Something went wrong on server side",
                )

            nft.deleted = True

            nft_history = NFTHistory()
            nft_history.before_user_id = payload.sub
            nft_history.nft_id = nft.id
            nft_history.note = NFTNote.Withdraw
            nft_history.price = nft.price
            nft_history.transaction_hash = tx_data

            session.add(nft_history)

        @router.get("/list/nft/sol", summary="Get Solana NFT list")
        async def get_sol_nft_list(
            payload: TokenPayload = Depends(get_current_user_from_oauth),
            session: Session = Depends(get_db_session),
        ):
            nfts: list[NFT] = list(
                session.query(NFT)
                .filter(
                    and_(
                        and_(NFT.user_id == payload.sub, NFT.network == Network.Solana),
                        NFT.deleted == False,
                    )
                )
                .all()
            )

            response_data = []
            for nft in nfts:
                data = {
                    "id": nft.id,
                    "imageUrl": nft.image_url,
                    "price": nft.price,
                }
                response_data.append(data)

            return response_data

        @router.get("/history/nft/sol", summary="Get Solana NFT history")
        async def get_sol_nft_history(
            offset: int = 0,
            count: int = 10,
            payload: TokenPayload = Depends(get_current_user_from_oauth),
            session: Session = Depends(get_db_session),
        ):
            total = (
                session.query(NFTHistory, NFT)
                .filter(
                    and_(
                        and_(
                            NFT.id == NFTHistory.nft_id, NFT.network == Network.Ethereum
                        ),
                        or_(
                            NFTHistory.before_user_id == payload.sub,
                            NFTHistory.after_user_id == payload.sub,
                        ),
                    )
                )
                .count()
            )
            histories: list[any] = list(
                session.query(NFTHistory, NFT)
                .filter(
                    and_(
                        and_(
                            NFT.id == NFTHistory.nft_id, NFT.network == Network.Solana
                        ),
                        or_(
                            NFTHistory.before_user_id == payload.sub,
                            NFTHistory.after_user_id == payload.sub,
                        ),
                    )
                )
                .offset(offset)
                .limit(count)
            )

            response_data = []
            for (history, nft) in histories:
                print(history, nft)
                data = {
                    "imageUrl": nft.image_url,
                    "name": nft.name,
                    "created_at": history.created_at,
                    "transactionHash": history.transaction_hash,
                    "note": history.note,
                    "price": history.price,
                }
                response_data.append(data)

            return {"total": total, "records": response_data}

        app.include_router(router)
