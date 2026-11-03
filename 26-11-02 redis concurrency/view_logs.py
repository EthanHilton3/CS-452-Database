# USAGE
# python view_logs.py            (whole timeline)
# python view_logs.py <text>     (only entries containing <text>, e.g. a UUID)

import json
import sys

from redis_logger import db, LOG_KEY

needle = sys.argv[1] if len(sys.argv) > 1 else ""

for raw in db.lrange(LOG_KEY, 0, -1):
	entry = json.loads(raw)
	line = "{time}  {server:<26} {script:<20} {action}".format(**entry)
	if needle in line:
		print(line)
