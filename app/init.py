# Don't edit
__author__ = "Joseph Anderson"
__copyright__ = "Copyright 2022, Modern Time Team"
__license__ = "INTERNAL"
__version__ = "0.1.0"
__maintainer__ = __author__
__email__ = "devanderson0412@gmail.com"
__status__ = "alpha"


from fastapi import FastAPI
from app.__internal import bootstrap

app = FastAPI(
    title="Modern Game Backend API",
    description="Gambling site backend API",
    version="-".join([__version__, __status__]),
    # root_path="/api/v1",
)

bootstrap(app)
