from email.policy import default
from sqlalchemy import (
    Column,
    Integer,
    String,
    TIMESTAMP,
    Boolean,
    text,
    ForeignKey,
    Enum as SAEnum,
    Float,
)
from sqlalchemy.orm import relationship
from sqlalchemy.ext.associationproxy import association_proxy
from src.database import Base
from enum import Enum


class RoleEnum(str, Enum):
    Dev = "DEV"
    Admin = "ADMIN"
    User = "USER"


class SignMethod(str, Enum):
    Email = "EMAIL"
    Google = "Google"
    MWallet = "METAMASK_WALLET"
    PWallet = "PHANTOM_WALLET"


class User(Base):
    __tablename__ = "user"
    id = Column(Integer, primary_key=True)
    name = Column(String(512), nullable=False, default="Unnamed")
    address = Column(String(512), nullable=True)
    sign_method = Column(SAEnum(SignMethod), nullable=False, default=SignMethod.Email)
    hashed_password = Column(String(512), nullable=True)
    role = Column(SAEnum(RoleEnum), nullable=False, default=RoleEnum.User)
    avatar_id = Column(Integer, ForeignKey("avatar.id"), nullable=False, default=1)
    balance = Column(Float, nullable=False, default=0)
    rollback = Column(Float, nullable=False, default=0)
    deposit_balance = Column(Float, nullable=False, default=0)
    withdraw_balance = Column(Float, nullable=False, default=0)

    created_at = Column(
        TIMESTAMP, nullable=False, server_default=text("CURRENT_TIMESTAMP")
    )
    updated_at = Column(
        TIMESTAMP,
        nullable=True,
        server_default=text("CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP"),
    )
    deleted = Column(Boolean, default=False)

    # relationship with avatar
    avatar = relationship("AvatarList", foreign_keys="[User.avatar_id]", uselist=False)
    avatar_url = association_proxy("avatar", "url")
    # relationship with access key
    access_key = relationship("UserAccessKey", back_populates="user", uselist=False)
    is_pending = association_proxy("access_key", "is_pending")
    # relationship with history data
    dw_histories = relationship("DWHistory", back_populates="user")
    # relationship with nfts
    nfts = relationship("NFT", back_populates="owner")
    out_nfts = relationship(
        "NFTHistory",
        foreign_keys="[NFTHistory.before_user_id]",
        back_populates="before_user",
    )
    in_nfts = relationship(
        "NFTHistory",
        foreign_keys="[NFTHistory.after_user_id]",
        back_populates="after_user",
    )


class AvatarList(Base):
    __tablename__ = "avatar"
    id = Column(Integer, primary_key=True)
    url = Column(String(1024), nullable=False)
    owner_id = Column(Integer, ForeignKey("user.id"), nullable=True)


class UserAccessKey(Base):
    __tablename__ = "user_access_key"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("user.id"))
    is_pending = Column(Boolean, nullable=False, default=True)
    key = Column(String(6), nullable=False)
    updated_at = Column(
        TIMESTAMP,
        nullable=True,
        server_default=text("CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP"),
    )

    user = relationship("User", back_populates="access_key", uselist=False)


class Direct(str, Enum):
    Deposit = "DEPOSIT"
    Withdraw = "WITHDRAW"


class DepositMethod(str, Enum):
    Eth = "ETH"
    Usdt = "USDT"
    Usdc = "USDC"
    Sol = "SOL"


class DWHistory(Base):
    __tablename__ = "dw_history"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("user.id"))
    direct = Column(SAEnum(Direct), nullable=False, default=Direct.Deposit)
    deposit_method = Column(SAEnum(DepositMethod), nullable=False)
    tx_hash = Column(String(128), nullable=False)
    amount = Column(Float, nullable=False, default=0)
    created_at = Column(
        TIMESTAMP, nullable=False, server_default=text("CURRENT_TIMESTAMP")
    )

    user = relationship("User", back_populates="dw_histories", uselist=False)


class Network(str, Enum):
    Ethereum = "ETHEREUM"
    Solana = "SOLANA"


class NFTType(str, Enum):
    ERC721 = "ERC721"
    ERC1155 = "ERC1155"


class NFT(Base):
    __tablename__ = "nft"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("user.id"))
    network = Column(SAEnum(Network), nullable=False, default=Network.Ethereum)
    token_address = Column(String(66), nullable=False)
    token_id = Column(String(66), nullable=True)
    price = Column(Float, nullable=False, default=0)
    nft_type = Column(SAEnum(NFTType), nullable=False, default=NFTType.ERC721)
    deposit_tx_hash = Column(String(128), nullable=False)
    deleted = Column(Boolean, nullable=False, default=False)

    owner = relationship("User", back_populates="nfts", uselist=False)
    histories = relationship("NFTHistory", back_populates="nft")


class NFTNote(str, Enum):
    Jackpot = "JACKPOT"
    Marketplace = "MARKETPLACE"
    Deposit = "DEPOSIT"
    Withdraw = "WITHDRAW"


class NFTHistory(Base):
    __tablename__ = "nft_history"
    id = Column(Integer, primary_key=True)
    nft_id = Column(Integer, ForeignKey("nft.id"))
    before_user_id = Column(Integer, ForeignKey("user.id"), nullable=True)
    after_user_id = Column(Integer, ForeignKey("user.id"), nullable=True)
    price = Column(Float, nullable=False, default=0)
    note = Column(SAEnum(NFTNote), nullable=False)
    created_at = Column(
        TIMESTAMP, nullable=False, server_default=text("CURRENT_TIMESTAMP")
    )

    nft = relationship("NFT", back_populates="histories", uselist=False)
    before_user = relationship(
        "User", foreign_keys=[before_user_id], back_populates="out_nfts", uselist=False
    )
    after_user = relationship(
        "User", foreign_keys=[after_user_id], back_populates="in_nfts", uselist=False
    )
