# unified logger: every process (web server, workers, clients) pushes its
# entries onto one Redis list, so the whole system reads as one timeline
import datetime
import json
import os
import socket
import sys

import redis

import settings

LOG_KEY = "logs"
MAX_ENTRIES = 1000

db = redis.StrictRedis(host=settings.REDIS_HOST,
	port=settings.REDIS_PORT, password=settings.REDIS_PASSWORD, db=settings.REDIS_DB)

# these never change for the life of the process, so compute them once;
# the PID tells apart two workers running on the same machine
SERVER = f"{socket.gethostname()}:{os.getpid()}"
SCRIPT = os.path.basename(sys.argv[0])

def log(action):
	entry = {
		"time": datetime.datetime.now().isoformat(timespec="milliseconds"),
		"server": SERVER,
		"script": SCRIPT,
		"action": action,
	}

	# one write per entry, so lines from concurrent threads can't interleave
	sys.stdout.write("[{time}] {server} {script}: {action}\n".format(**entry))

	# logging must never take a server down, so swallow Redis errors
	try:
		# pipeline = both commands in one round trip, wrapped in MULTI/EXEC;
		# LTRIM keeps only the newest MAX_ENTRIES so the list can't grow forever
		pipe = db.pipeline()
		pipe.rpush(LOG_KEY, json.dumps(entry))
		pipe.ltrim(LOG_KEY, -MAX_ENTRIES, -1)
		pipe.execute()
	except redis.RedisError as e:
		sys.stdout.write(f"[logger] could not write to Redis: {e}\n")
