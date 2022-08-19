from __future__ import annotations
from datetime import datetime
from operator import and_
from typing import Callable

from eth_utils import to_wei

from app.__internal import Function
from fastapi import FastAPI, APIRouter, Query, status, HTTPException, Depends
from sqlalchemy.orm import Session
from uniswap import Uniswap
from opensea import OpenseaAPI

from src.dependencies.auth_deps import get_current_user_from_oauth
from src.dependencies.database_deps import get_db_session
from src.models import (
    NFT,
    DWHistory,
    DepositMethod,
    Direct,
    NFTHistory,
    NFTNote,
    NFTType,
    Network,
    User,
)
from src.schemas.auth import TokenPayload

from config import cfg
from src.schemas.user import WalletData
from src.utils.temp_wallets import get_eth_deposit_wallet, get_sol_deposit_wallet
from src.utils.web3 import (
    ETH_ERC1155_TRANSFER_TOPIC,
    compare_eth_address,
    erc1155_data_dispatch,
    get_current_gas_price,
    get_transaction_eth_value,
    get_transaction_nft_data,
    get_transaction_token_value,
    send_eth_stable_to,
    wait_transaction_receipt,
)

eth = "0x0000000000000000000000000000000000000000"
eth_usdt = cfg.ETH_USDT_ADDRESS
eth_usdc = cfg.ETH_USDC_ADDRESS


class UserAPI(Function):
    def __init__(self, error: Callable):
        self.log.info("user api initailized")
        self.uniswap = Uniswap(
            address=cfg.ETH_TREASURY_ADDRESS,
            private_key=cfg.ETH_TREASURY_PRIVATE_KEY,
            version=2,
            provider=cfg.ETH_RPC_URL,
        )
        # self.opensea = OpenseaAPI(apikey=cfg.OPENSEA_API)
        # create_transacion_filter()

    def Bootstrap(self, app: FastAPI):
        router = APIRouter(
            prefix="/user",
            tags=["user"],
            responses={404: {"description": "Not found"}},
        )

        @router.get("/", summary="Get user data")
        async def get_user_data(
            payload: TokenPayload = Depends(get_current_user_from_oauth),
            session: Session = Depends(get_db_session),
        ):
            user: User = (
                session.query(User)
                .filter(and_(User.id == payload.sub, User.deleted == False))
                .one()
            )

            return {
                "name": user.name,
                "address": user.address,
                "avatar": user.avatar_url,
                "signMethod": user.sign_method,
                "balance": user.balance,
                "rollback": user.rollback,
                "isPending": user.is_pending,
            }

        @router.get(
            "/price/eth/usdt/input",
            summary="Returns the amount of USDT you get for exact ETH",
        )
        async def get_price_eth_usdt_input(amount: float) -> float:
            fee = get_current_gas_price() * int(cfg.ETH_SWAP_FEE)
            print(fee / 10**18)
            return (
                float(
                    self.uniswap.get_price_input(
                        eth, eth_usdt, int(amount * (10**18)) + fee
                    )
                )
            ) / 10**6

        @router.get(
            "/price/eth/usdt/output",
            summary="Returns the amount of ETH need to deposit for exact USDT",
        )
        async def get_price_eth_usdt_output(amount: float) -> float:
            fee = get_current_gas_price() * int(cfg.ETH_SWAP_FEE)
            return (
                float(
                    self.uniswap.get_price_output(
                        eth, eth_usdt, int(amount * (10**6))
                    )
                )
                + fee
            ) / 10**18

        @router.get(
            "/price/usdt/eth/input",
            summary="Returns the amount of ETH you get for exact USDT",
        )
        async def get_price_usdt_eth_input(amount: float) -> float:
            fee = get_current_gas_price() * int(cfg.ETH_SWAP_FEE)
            print(fee / 10**18)
            return (
                float(
                    self.uniswap.get_price_input(eth_usdt, eth, int(amount * (10**6)))
                )
                + fee
            ) / 10**18

        @router.get(
            "/price/usdt/eth/output",
            summary="Returns the amount of USDT need to deposit for exact ETH",
        )
        async def get_price_usdt_eth_output(amount: float) -> float:
            fee = get_current_gas_price() * int(cfg.ETH_SWAP_FEE)
            return (
                float(
                    self.uniswap.get_price_output(
                        eth_usdt, eth, int(amount * (10**18)) + fee
                    )
                )
            ) / 10**6

        @router.get("/deposit_wallet/eth", summary="Return deposit wallet data")
        async def deposit_eth_eth(
            payload: TokenPayload = Depends(get_current_user_from_oauth),
            session: Session = Depends(get_db_session),
        ) -> float:

            wallet: WalletData = get_eth_deposit_wallet()
            wallet.user_id = payload.sub
            wallet.timestamp = datetime.today().timestamp()
            wallet.is_using = True

            return wallet.public_key

        @router.get("/deposit_wallet/sol", summary="Return deposit wallet data")
        async def deposit_eth_eth(
            payload: TokenPayload = Depends(get_current_user_from_oauth),
            session: Session = Depends(get_db_session),
        ) -> float:

            wallet: WalletData = get_sol_deposit_wallet()
            wallet.user_id = payload.sub
            wallet.timestamp = datetime.today().timestamp()
            wallet.is_using = True

            return wallet.public_key

        @router.post("/deposit/eth/eth", summary="Deposit eth manually")
        async def deposit_eth_manually(
            tx_hash: str = Query(default=None, regex="0x[a-z0-9]{64}"),
            payload: TokenPayload = Depends(get_current_user_from_oauth),
            session: Session = Depends(get_db_session),
        ) -> float:
            if tx_hash == None:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="You need to set hash",
                )

            if (
                len(list(session.query(DWHistory).filter(DWHistory.tx_hash == tx_hash)))
                > 0
            ):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST, detail="Already registered"
                )

            tx_data = get_transaction_eth_value(tx_hash)
            if not compare_eth_address(tx_data["to"], cfg.ETH_TREASURY_ADDRESS):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid transfer-didn't send to treasury",
                )

            fee = get_current_gas_price() * int(cfg.ETH_SWAP_FEE)
            tx = self.uniswap.make_trade(
                eth, eth_usdt, int(to_wei(tx_data["value"], "wei") - fee)
            )
            receipt = wait_transaction_receipt(tx)

            received = float(int(receipt.logs[2].data, 16)) / 10**6

            new_history = DWHistory()
            new_history.tx_hash = tx_hash
            new_history.user_id = payload.sub
            new_history.direct = Direct.Deposit
            new_history.deposit_method = DepositMethod.Eth
            new_history.amount = received

            session.add(new_history)

            user_balance: UserBalance = (
                session.query(UserBalance)
                .filter(UserBalance.user_id == payload.sub)
                .one()
            )
            user_balance.balance += received

            return new_history

        @router.post("/deposit/eth/stable", summary="Deposit stable coin manually")
        async def deposit_eth_stable_manually(
            tx_hash: str = Query(default=None, regex="0x[a-z0-9]{64}"),
            payload: TokenPayload = Depends(get_current_user_from_oauth),
            session: Session = Depends(get_db_session),
        ) -> float:
            if tx_hash == None:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="You need to set hash",
                )

            if (
                len(list(session.query(DWHistory).filter(DWHistory.tx_hash == tx_hash)))
                > 0
            ):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST, detail="Already registered"
                )

            tx_data = get_transaction_token_value(tx_hash)

            if not compare_eth_address(
                tx_data["contract"], eth_usdt
            ) and not compare_eth_address(tx_data["contract"], eth_usdc):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid transfer-not USDT",
                )

            if not compare_eth_address(tx_data["to"], cfg.ETH_TREASURY_ADDRESS):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid transfer-didn't send to treasury",
                )

            fee = get_current_gas_price() * int(cfg.ETH_SWAP_FEE)
            fee_usdt = (
                float(self.uniswap.get_price_output(eth_usdt, eth, fee)) / 10**6
            )
            received = float(int(tx_data["value"], 16) - fee_usdt) / 10**6

            new_history = DWHistory()
            new_history.tx_hash = tx_hash
            new_history.user_id = payload.sub
            new_history.direct = Direct.Deposit

            if tx_data["contract"] == cfg.ETH_USDT_ADDRESS:
                new_history.deposit_method = DepositMethod.Usdt
            elif tx_data["contract"] == cfg.ETH_USDC_ADDRESS:
                new_history.deposit_method = DepositMethod.Usdc

            new_history.amount = received

            session.add(new_history)

            user_balance: UserBalance = (
                session.query(UserBalance)
                .filter(UserBalance.user_id == payload.sub)
                .one()
            )
            user_balance.balance += received

            return new_history

        @router.post("/deposit/eth/nft", summary="Deposit stable coin manually")
        async def deposit_eth_nft_manually(
            tx_hash: str = Query(default=None, regex="0x[a-z0-9]{64}"),
            payload: TokenPayload = Depends(get_current_user_from_oauth),
            session: Session = Depends(get_db_session),
        ):
            if tx_hash == None:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="You need to set hash",
                )

            if len(list(session.query(NFT).filter(NFT.deposit_tx_hash == tx_hash))) > 0:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST, detail="Already registered"
                )

            tx_data = get_transaction_nft_data(tx_hash)

            deposited = []
            for log in tx_data:
                # if not compare_eth_address(log.topics[2], cfg.ETH_TREASURY_ADDRESS):
                #   continue

                if log.data == "0x":
                    # erc721 nft
                    new_nft = NFT()
                    new_nft.user_id = payload.sub
                    new_nft.deposit_tx_hash = tx_hash
                    new_nft.token_address = log.address
                    new_nft.token_id = int(log.topics[3].hex(), 16)
                    new_nft.price = 0
                    new_nft.network = Network.Ethereum
                    new_nft.nft_type = NFTType.ERC721

                    session.add(new_nft)
                    session.flush()
                    session.refresh(new_nft, attribute_names=["id"])

                    new_history = NFTHistory()
                    new_history.nft_id = new_nft.id
                    new_history.after_user_id = payload.sub
                    new_history.note = NFTNote.Deposit
                    new_history.price = new_nft.price

                    session.add(new_history)
                    session.flush()
                    deposited.append(new_nft)

                elif log.topics[0].hex() == ETH_ERC1155_TRANSFER_TOPIC:
                    (token_id, amount) = erc1155_data_dispatch(log.data)

                    for _ in range(amount):
                        new_nft = NFT()
                        new_nft.user_id = payload.sub
                        new_nft.deposit_tx_hash = tx_hash
                        new_nft.token_address = log.address
                        new_nft.token_id = token_id
                        new_nft.price = 0
                        new_nft.network = Network.Ethereum
                        new_nft.nft_type = NFTType.ERC1155

                        session.add(new_nft)
                        session.flush()
                        session.refresh(new_nft, attribute_names=["id"])

                        new_history = NFTHistory()
                        new_history.nft_id = new_nft.id
                        new_history.after_user_id = payload.sub
                        new_history.note = NFTNote.Deposit
                        new_history.price = new_nft.price

                        session.add(new_history)
                        session.flush()
                        deposited.append(new_nft)

            return deposited

        @router.post("/withdraw/eth/eth", summary="Withdraw money with ETH")
        async def withdraw_eth_eth(
            amount: float = Query(default=0),
            wallet: str = Query(default=None, regex="0x[A-Za-z0-9]{40}"),
            payload: TokenPayload = Depends(get_current_user_from_oauth),
            session: Session = Depends(get_db_session),
        ) -> float:
            if amount == 0:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="You need to set amount more than 0",
                )

            user_balance: UserBalance = (
                session.query(UserBalance)
                .filter(UserBalance.user_id == payload.sub)
                .one()
            )

            fee = get_current_gas_price() * int(cfg.ETH_SWAP_FEE)
            total_eth = (
                self.uniswap.get_price_input(
                    eth_usdt, eth, (user_balance.balance) * 10**6
                )
                - fee
            )

            if amount > total_eth:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Much than real amount",
                )

            delta_balance = (
                float(
                    self.uniswap.get_price_output(eth_usdt, eth, amount * 10**18)
                    + fee
                )
                / 10**6
            )
            user_balance -= delta_balance
            user_balance.withdraw_balance += delta_balance

            new_history = DWHistory()
            new_history.amount = delta_balance
            new_history.direct = Direct.Withdraw
            new_history.user_id = payload.sub

            session.add(new_history)

            tx = self.uniswap.make_trade_output(
                eth_usdt, eth, amount * 10**18, wallet
            )
            receipt = wait_transaction_receipt(tx)

            return receipt

        @router.post("/withdraw/eth/usdt", summary="Withdraw money with USDT")
        async def withdraw_eth(
            amount: float = Query(default=0),
            wallet: str = Query(default=None, regex="0x[A-Za-z0-9]{40}"),
            payload: TokenPayload = Depends(get_current_user_from_oauth),
            session: Session = Depends(get_db_session),
        ) -> float:
            if amount == 0:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="You need to set amount more than 0",
                )

            user_balance: UserBalance = (
                session.query(UserBalance)
                .filter(UserBalance.user_id == payload.sub)
                .one()
            )

            fee = get_current_gas_price() * int(cfg.ETH_SWAP_FEE)
            fee_usdt = (
                float(self.uniswap.get_price_output(eth_usdt, eth, fee)) / 10**6
            )

            if amount + fee_usdt > user_balance.balance:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Much than real amount",
                )

            try:
                receipt = send_eth_stable_to(eth_usdt, wallet, amount)
            except Exception as ex:
                print(ex)
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Some error occured in server side",
                )

            delta_balance = amount + fee_usdt
            user_balance.balance -= delta_balance
            user_balance.withdraw_balance += delta_balance

            new_history = DWHistory()
            new_history.amount = delta_balance
            new_history.direct = Direct.Withdraw
            new_history.user_id = payload.sub

            session.add(new_history)
            return receipt["blockHash"].hex()

        @router.post("/withdraw/eth/usdc", summary="Withdraw money with USDC")
        async def withdraw_eth(
            amount: float = Query(default=0),
            wallet: str = Query(default=None, regex="0x[A-Za-z0-9]{40}"),
            payload: TokenPayload = Depends(get_current_user_from_oauth),
            session: Session = Depends(get_db_session),
        ) -> float:
            if amount == 0:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="You need to set amount more than 0",
                )

            user_balance: UserBalance = (
                session.query(UserBalance)
                .filter(UserBalance.user_id == payload.sub)
                .one()
            )

            fee = get_current_gas_price() * int(cfg.ETH_SWAP_FEE)
            fee_usdt = (
                float(self.uniswap.get_price_output(eth_usdc, eth, fee)) / 10**6
            )

            if amount + fee_usdt > user_balance.balance:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Much than real amount",
                )

            try:
                receipt = send_eth_stable_to(eth_usdc, wallet, amount)
            except Exception as ex:
                print(ex)
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Some error occured in server side",
                )

            delta_balance = amount + fee_usdt
            user_balance.balance -= delta_balance
            user_balance.withdraw_balance += delta_balance

            new_history = DWHistory()
            new_history.amount = delta_balance
            new_history.direct = Direct.Withdraw
            new_history.user_id = payload.sub

            session.add(new_history)
            return receipt["blockHash"].hex()

        @router.post("/withdraw/sol/sol", summary="Withdraw money with sol")
        async def withdraw_sol_sool(
            amount: float = Query(default=0),
            wallet: str = Query(default=None, regex="[A-Za-z0-9]{42-44}"),
            payload: TokenPayload = Depends(get_current_user_from_oauth),
            session: Session = Depends(get_db_session),
        ) -> float:
            if amount == 0:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="You need to set amount more than 0",
                )

            user_balance: UserBalance = (
                session.query(UserBalance)
                .filter(UserBalance.user_id == payload.sub)
                .one()
            )

            fee = get_current_gas_price() * int(cfg.ETH_SWAP_FEE)
            total_eth = (
                self.uniswap.get_price_input(
                    eth_usdt, eth, (user_balance.balance) * 10**6
                )
                - fee
            )

            if amount > total_eth:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Much than real amount",
                )

            delta_balance = (
                float(
                    self.uniswap.get_price_output(eth_usdt, eth, amount * 10**18)
                    + fee
                )
                / 10**6
            )
            user_balance -= delta_balance
            user_balance.withdraw_balance += delta_balance

            new_history = DWHistory()
            new_history.amount = delta_balance
            new_history.direct = Direct.Withdraw
            new_history.user_id = payload.sub

            session.add(new_history)

            tx = self.uniswap.make_trade_output(
                eth_usdt, eth, amount * 10**18, wallet
            )
            receipt = wait_transaction_receipt(tx)

            return receipt

        app.include_router(router)
