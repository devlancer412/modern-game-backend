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
    DB_PASSWORD: str = ""
    DB_HOST: str = "localhost"
    DB_PORT: str = "3306"
    DATABASE: str = "modern_game"

    GOOGLE_CLIENT_ID: str = UNSET
    GOOGLE_CLIENT_SECRET: str = UNSET

    JWT_SECRET_KEY: str = "09d25e094faa6ca2556c818166b7a9563b93f7099f6f0f4caa6cf63b88e8d3e7"
    JWT_REFRESH_SECRET_KEY: str = "09d25e094faa6ca2556c818166b7a9563b93f7099f6f0f4caa6cf63b88e8d3e7"

    # test in ropsten
    ETH_RPC_URL: str = "https://mainnet.infura.io/v3/9aa3d95b3bc440fa88ea12eaa4456161"
    # ETH_RPC_URL: str = "https://rinkeby.infura.io/v3/9aa3d95b3bc440fa88ea12eaa4456161"
    ETH_TREASURY_ADDRESS: str = "0x5C29Ac1d01aE85Bd93D1Cc1C457c0d4aed46C0AF"
    ETH_TREASURY_PRIVATE_KEY: str = "cc2380168b30452e01321b5d8d810714d37e57e2b035b63c8de5d0624ec56def"
    ETH_TEMP_MNEMONIC: str = UNSET
    # UNUSWAP_FACTORY_ADDRESS: str = "0x9c83dCE8CA20E9aAF9D3efc003b2ea62aBC08351"

    ETH_USDT_ADDRESS: str = "0x110a13FC3efE6A245B50102D2d79B3E76125Ae83"
    ETH_USDC_ADDRESS: str = "0x110a13FC3efE6A245B50102D2d79B3E76125Ae83"
    ETH_SWAP_FEE: str = "250000"

    SOL_RPC_URL: str = "https://api.mainnet-beta.solana.com"
    SOL_WSS_URL: str = "wss://api.mainnet-beta.solana.com"
    SOL_TREASURY_ADDRESS: str = "2T6sdfxViTSow8pxeDkVb2C2J6Kj2XtYDWjgbGTgN3Nb"
    SOL_TREASURY_PRIVATE_KEY: str = "2vHbahrxnnisSE7WgFNnG44pGv72oyGaiD2w9gsN9RmEkC2wveCnAGY9mjthMjfxKACBKi6dFfEiaUBwgoEPq9ST"
    SOL_USDT_ADDRESS: str = "Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB"
    SOL_USDC_ADDRESS: str = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"
    SOL_SWAP_FEE: str = "6000000"

    OPENSEA_API: str = ""

# --- Do not edit anything below this line, or do it, I'm not your mom ----
defaults = Configuration(autoload=False)
cfg = Configuration()

