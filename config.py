import os.path
import pathlib

from app.__internal import ConfigBase, UNSET


class Configuration(ConfigBase):
    # DB_USER: str = "admin"
    # DB_PASSWORD: str = "Wxmzxa;518"
    # DB_HOST: str = "modern-game-db.c3d4svrxffbd.us-east-1.rds.amazonaws.com"
    # DB_PORT: str = "3306"
    # DATABASE: str = "modern_game"
    DB_USER: str = "root"
    DB_PASSWORD: str = "Dev1994412$"
    DB_HOST: str = "localhost"
    DB_PORT: str = "3306"
    DATABASE: str = "modern_game"

    GOOGLE_CLIENT_ID: str = UNSET
    GOOGLE_CLIENT_SECRET: str = UNSET

    JWT_SECRET_KEY: str = (
        "09d25e094faa6ca2556c818166b7a9563b93f7099f6f0f4caa6cf63b88e8d3e7"
    )
    JWT_REFRESH_SECRET_KEY: str = (
        "09d25e094faa6ca2556c818166b7a9563b93f7099f6f0f4caa6cf63b88e8d3e7"
    )

    CN_API_KEY: str = "cc77f27ad5e6effbda55f4c50b18947f12b05de70d17f1b07c0b1b01962f55a1"
    # test in ropsten
    ETH_RPC_URL: str = "https://mainnet.infura.io/v3/9aa3d95b3bc440fa88ea12eaa4456161"
    # ETH_RPC_URL: str = "https://rinkeby.infura.io/v3/9aa3d95b3bc440fa88ea12eaa4456161"
    ETH_TREASURY_ADDRESS: str = "0x5C29Ac1d01aE85Bd93D1Cc1C457c0d4aed46C0AF"
    ETH_TREASURY_PRIVATE_KEY: str = (
        "cc2380168b30452e01321b5d8d810714d37e57e2b035b63c8de5d0624ec56def"
    )
    ETH_MAX_FEE: int = 30000

    SOL_RPC_URL: str = "https://broken-broken-frost.solana-mainnet.quiknode.pro/9e6fcc4860ba30e382a6be3ccbe1455348fc81cb"
    SOL_TREASURY_ADDRESS: str = "4kb8kG8NjqCjgim7DpGC3YWDPY4B5Y4fbFKNeibcPCpo"
    SOL_TREASURY_PRIVATE_KEY: str = "65ozUBVMwsGWLr3K7T8rnHcffvHvb1akYzeQGsMfhTZ1vkArtpsa3qLbTbpA4om1Ar8fPaqPzHW1Sn4oHo4vy6kX"

    ETH_USDT_ADDRESS: str = "0xdAC17F958D2ee523a2206206994597C13D831ec7"

    OPENSEA_API: str = "acc245a0e1724ee1b2aa7849a3da9b63"


# --- Do not edit anything below this line, or do it, I'm not your mom ----
defaults = Configuration(autoload=False)
cfg = Configuration()

# 54cV7FyCa3c59bVcHUciSR2r2XQrz1KvybcZCwDmpdztGBbRKsdFZSjCfsVx8WFzx7rCWHCXUwDmZ6NQVen54o7b
