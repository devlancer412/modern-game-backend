from multiprocessing import cpu_count

# Socket Path
bind = "unix:/home/modern-game-backend/gunicorn.sock"

# Worker Options
workers = cpu_count() + 1
worker_class = "uvicorn.workers.UvicornWorker"

# Logging Options
loglevel = "debug"
accesslog = "/home/modern-game-backend/access_log"
errorlog = "/home/modern-game-backend/error_log"
