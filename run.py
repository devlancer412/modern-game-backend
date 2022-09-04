import uvicorn
from app.init import app

original_callback = uvicorn.main.callback


def callback(**kwargs):
    from celery.contrib.testing.worker import start_worker
    from src.celery import celery

    with start_worker(celery, perform_ping_check=False, loglevel="info"):
        original_callback(**kwargs)


uvicorn.main.callback = callback


if __name__ == "__main__":
    uvicorn.run(app, reload=True)
