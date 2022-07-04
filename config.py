import os.path
import pathlib

from app.__internal import ConfigBase, UNSET


class Configuration(ConfigBase):
    DB_USER: str = "admin"
    DB_PASSWORD: str = "Wxmzxa;518"
    DB_HOST: str = "database-2.c3d4svrxffbd.us-east-1.rds.amazonaws.com"
    DB_PORT: str = "3306"
    DATABASE: str = "modern_game"

    JWT_SECRET_KEY: str = "09d25e094faa6ca2556c818166b7a9563b93f7099f6f0f4caa6cf63b88e8d3e7"
    JWT_REFRESH_SECRET_KEY: str = "09d25e094faa6ca2556c818166b7a9563b93f7099f6f0f4caa6cf63b88e8d3e7"

# --- Do not edit anything below this line, or do it, I'm not your mom ----
defaults = Configuration(autoload=False)
cfg = Configuration()