#!/bin/bash
source ./environment/bin/activate
gunicorn app.init:app -k uvicorn.workers.UvicornWorker

