import os.path
import pathlib

from app.__internal import ConfigBase, UNSET


class Configuration(ConfigBase):
    RPC_URL: str = "https://rinkeby.infura.io/v3/9aa3d95b3bc440fa88ea12eaa4456161"

# --- Do not edit anything below this line, or do it, I'm not your mom ----
defaults = Configuration(autoload=False)
cfg = Configuration()