#!/bin/bash
celery -A src.celery:celery worker -E -Q messaging --loglevel=INFO --autoscale=10,4 --without-heartbeat --without-gossip --without-mingle &
uvicorn app.init:app --reload &
celery -A src.celery:celery flower