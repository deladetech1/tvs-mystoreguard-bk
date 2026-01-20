"""Gunicorn configuration file for production deployment"""
import os

# Server Socket
bind = "0.0.0.0:8000"
backlog = 2048

# Worker Processes
# FIXED: Default to 2 workers for predictable connection usage
# cpu_count() in containers often reports host CPUs, not container limits
# This can lead to unexpectedly high worker counts and DB connection exhaustion
# With DB_POOL_SIZE=2 and workers=2: 2 × 2 = 4 connections (very safe for Azure Basic tier)
# Can be overridden with GUNICORN_WORKERS environment variable
workers = int(os.getenv("GUNICORN_WORKERS", "2"))
worker_class = "uvicorn.workers.UvicornWorker"
worker_connections = 1000
max_requests = 1000
max_requests_jitter = 50
timeout = 120
keepalive = 5

# Logging
accesslog = "-"  # Log to stdout
errorlog = "-"   # Log to stderr
loglevel = os.getenv("LOG_LEVEL", "info")
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s'

# Process Naming
proc_name = "trovesuite-api"

# Server Mechanics
daemon = False
pidfile = None
umask = 0
user = None
group = None
tmp_upload_dir = None

# SSL (if needed in future)
keyfile = None
certfile = None
