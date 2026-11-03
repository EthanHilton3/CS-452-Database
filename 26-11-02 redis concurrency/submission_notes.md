# Redis Concurrency: submission notes

## 1. Redis key structure

**The user's image** is stored in the key `image_queue`.
- Type: **list**. The web server adds to it with `RPUSH`, so it works as a FIFO queue.
- Each element is a **JSON string**: `{"id": "<uuid4>", "image": "<base64>"}`.
- `image` is a preprocessed NumPy array (`float32`, shape `1×224×224×3`), base64-encoded so it fits in JSON. That's 602,112 bytes raw and about 803 KB once encoded, which is why a free 30 MB Redis only holds about 30 queued images.

**The result** is stored in a key named after the request's UUID, e.g. `8e029f38-1583-4901-ba23-9d8d83116222`.
- Type: **string**, holding a JSON list of the top 5 predictions: `[{"label": "church", "probability": 0.4136}, ...]`.

## 2. Web server ↔ model server communication

The two servers never talk to each other directly. Redis sits between them.

From `MONITOR` (web server = port 57602, worker = port 35734):

```
815.056  web     RPUSH image_queue {"id": "8e02…", "image": "…"}   hand off the work
815.066  web     GET 8e02…   → nil                                  start polling
815.085  worker  LRANGE image_queue 0 31                            read up to 32 items
         web     GET 8e02… ×8, every 0.25 s, all nil                still waiting
817.163  worker  SET 8e02… [{"label": "church", …}]                 write the result
817.165  worker  LTRIM image_queue 1 -1                             remove the processed item
817.333  web     GET 8e02… → result                                 found it
817.334  web     DEL 8e02…                                          clean up
```

- **Hand-off:** the web server makes a UUID and pushes `{id, image}` onto `image_queue`.
- **Return path:** the worker writes its result to a key named with that UUID. The UUID is the "return address."
- **Responding to the web request:** the Flask request handler blocks in a `while True` loop, running `GET <uuid>` every 0.25 s (`CLIENT_SLEEP`) until the key exists. Then it deletes the key and returns the predictions as JSON. The HTTP connection stays open the whole time.
- **Both sides poll.** The worker runs `LRANGE` every 0.25 s (`SERVER_SLEEP`) even when idle. That's about 14,400 commands an hour that do nothing. The web server sends 4 `GET`s per second for each waiting request.

## 3. Model output (`castle_image.jpg`)

| # | Label | Probability |
|---|---|---|
| 1 | church | 0.4136 |
| 2 | castle | 0.3930 |
| 3 | monastery | 0.1733 |
| 4 | palace | 0.0041 |
| 5 | vault | 0.0034 |

## 4. Concurrency and scaling

### The bug: two workers, read and remove are not atomic

The original worker reads the queue with `LRANGE` (which doesn't remove anything), runs ResNet for about 1–2 s, then removes items with `LTRIM image_queue N -1`, meaning "delete the first N items." That's two separate commands with a gap between them, and `LTRIM` deletes by **position**, not by which items this worker actually processed.

```
queue:  [1 2 3]
A: LRANGE → [1 2 3]                    B: LRANGE → [1 2 3]       ← same images read twice
        ...requests 4, 5, 6, 7 arrive while both run ResNet...
queue:  [1 2 3 4 5 6 7]
A: SET 1,2,3   LTRIM 3 -1 → [4 5 6 7]
B: SET 1,2,3 again                                              ← duplicate → orphan keys
B: LTRIM 3 -1 → [7]                                             ← 4,5,6 deleted unprocessed → LOST
```

**Evidence** (2 workers, 20 requests, `SLEEP_COUNT = 0.2`):
- Threads 10, 13, 17 and 19 never returned, and the stress test hung on `join()`.
- The queue was empty, yet `MONITOR` showed the web server polling 4 UUIDs forever (12 `GET`s each in 3 s). Those images had been trimmed away without anyone processing them.
- Redis kept result keys that no one would ever read (6 in an earlier run, 3 in this one; screenshot: `orphan_keys.png`). One worker `SET` a result, the web server read it and `DEL`ed it, then the second worker `SET` the same result again.

This is a **check-then-act** race. Both symptoms, the duplicate work and the lost work, come from the same gap between reading and removing.

### The fix: atomic pop

Redis runs commands one at a time on a single thread, so **each single command is atomic**. `LPOP` with a count reads and removes up to 32 items in one indivisible step, which means two workers can never get the same item, and nothing is removed unless someone took it.

```python
# before
queue = db.lrange(settings.IMAGE_QUEUE, 0, settings.BATCH_SIZE - 1)
...
db.ltrim(settings.IMAGE_QUEUE, len(imageIDs), -1)   # deleted

# after
queue = db.lpop(settings.IMAGE_QUEUE, settings.BATCH_SIZE) or []
```

`lpop` returns `None` on an empty queue. My first version handled that with `if queue is None: continue`, but `continue` skipped the `sleep` at the bottom of the loop. That would have turned the worker into a **busy loop** that sends thousands of `LPOP`s a second. `or []` lets the empty case fall through to the normal sleep.

**Result:** with 2 workers, the stress test finished with 20/20 OK on every run, and `KEYS *` was empty afterward (no orphans).

### Are multiple web servers safe?

**Yes.** A web server only does two things in Redis:
- `RPUSH` onto the shared queue, which is a single atomic command, so concurrent pushes from many servers never conflict.
- `GET` and `DEL` on **its own** UUID key.

Web servers share nothing with each other except Redis, and they never touch each other's keys, so there's no read-then-act gap like the workers had. In practice they'd run on different ports or machines behind a load balancer.

### Will they generate conflicting UUIDs?

Practically never. `uuid4()` has 122 random bits, so 2¹²² ≈ 5.3 × 10³⁶ possible values. By the birthday problem, you'd need about **2.7 × 10¹⁸** IDs for a 50% chance of a single collision. That's about 86 years at a billion requests per second. The real risk would be a weak random source, but `uuid4()` uses the operating system's secure random generator (`os.urandom`).

### Will subscribing to notifications scale or conflict?

**No conflicts.** Each waiting request subscribes to a channel named after its own UUID (`__keyspace@0__:<uuid>`), so one server never receives another server's event.

**Scaling has costs:**
- `notify-keyspace-events KEA` publishes events for *every* change to *every* key, including all the queue traffic.
- `psubscribe` is pattern matching. Redis checks every event against every pattern subscriber, so the cost is O(events × waiting requests). An exact `SUBSCRIBE` is a hash lookup, so its cost stays about the same as subscribers grow.
- There's one pub/sub connection per waiting request. A better design is one subscriber connection per web server that hands each event to whichever request thread is waiting.
- Pub/sub is fire-and-forget. If a subscriber isn't connected when the event fires, the event is lost.

### A worker crashes after claiming an item: a recovery strategy

`LPOP` removes the item *before* the work is done, so a crash loses it (**at-most-once** delivery). The fix is a **reliable queue**:

1. **Claim atomically:** `LMOVE image_queue processing LEFT RIGHT` moves the item to a `processing` list in one command. If "copy, then pop" were two separate steps, it would have the same gap as the original bug.
2. **Acknowledge:** after `SET`-ing the result, `LREM processing 1 <item>`.
3. **Recover:** a monitor process re-queues items that have been in `processing` longer than a timeout. A list doesn't store timestamps, so track claim times in a sorted set (score = claim time).
4. **Production alternative:** Redis Streams with consumer groups have this built in (`XREADGROUP` claims, `XACK` acknowledges, `XAUTOCLAIM` takes over idle messages).

**Trade-off:** a too-short timeout re-queues a job from a slow but still-running worker, so the job runs twice (**at-least-once** delivery). That's safe here because classification is **idempotent**: the same image writes the same result to the same key. Leftover duplicate results can be cleaned up automatically with a TTL (`SET key value EX 60`). The web server should also stop polling after a timeout and return an error instead of hanging forever.

## 5. Reducing polling overhead with keyspace notifications

Enabled with `CONFIG SET notify-keyspace-events KEA`:
- **K** = keyspace events: the channel is named after the key, and the message is the command that changed it.
- **E** = keyevent events: the channel is named after the command, and the message is the key.
- **A** = all command types.

Instead of running `GET <uuid>` every 0.25 s, the web server subscribes to `__keyspace@0__:<uuid>` and waits inside `get_message()` until Redis pushes a `set` event.

```python
# subscribe BEFORE pushing the work, so the notification can't fire before we're listening
p = db.pubsub()
p.subscribe(f"__keyspace@{settings.REDIS_DB}__:{k}")
db.rpush(settings.IMAGE_QUEUE, json.dumps(d))

# block until Redis tells us our key changed; the first message is the subscribe confirmation
while True:
    message = p.get_message(timeout=30.0)
    if message is None or message["type"] == "message":
        break

p.unsubscribe()
p.close()

# the notification carries no data, so fetch the result; this also catches a missed notification
output = db.get(k)
if output is not None:
    data["predictions"] = json.loads(output.decode("utf-8"))
    db.delete(k)
    data["success"] = True
```

- I used `SUBSCRIBE` (exact channel name, a hash lookup) instead of the readme's `PSUBSCRIBE` (pattern), because Redis has to check every event against every pattern subscriber.
- The 30 s timeout means a request whose worker crashed returns `success: false` instead of hanging forever.

### Results: before vs. after

| | Polling | Notifications |
|---|---|---|
| Web server commands per request | `RPUSH`, `GET` × (wait / 0.25 s), `DEL` | `SUBSCRIBE`, `RPUSH`, `UNSUBSCRIBE`, **one** `GET`, `DEL` |
| `simple_request.py` | 9 `GET`s that returned nothing | 0 |
| Stress test, 20 requests | ~240 `GET`s that returned nothing | 0 (one `GET` per request, always a hit) |
| Delay from worker `SET` to the web server noticing | up to 250 ms (170 ms measured) | ~1–2 ms (`SET` 043.0964 → `UNSUBSCRIBE` 043.0980) |
| Idle cost | 0 (waiting threads are blocked in `sleep`) | 0 (waiting threads are blocked in the socket) |

```
043.0964  worker  SET eb7254cd… [church, castle…]
043.0980  web     UNSUBSCRIBE                   ← notified 1.6 ms later
043.1074  web     GET eb7254cd…                 ← one GET, always a hit
043.1089  web     DEL eb7254cd…
```

The waiting thread is blocked inside a socket read, so it uses no CPU and sends no commands. The cost of waiting no longer grows with how long the job takes.

**What's still left (from the trace):**
- **The workers still poll:** 2 workers × 4 `LPOP`s a second, forever. The fix is `BLPOP`, a blocking pop that waits inside Redis until an item arrives.
- **One pub/sub connection per request:** each request's `p.close()` drops a connection, so the next request opens a new one (`HELLO` and `CLIENT SETINFO` every time). At scale, one long-lived subscriber per web server that hands each event to the right waiting thread would avoid this.

### What if the notification is missed, or the worker crashes?

Pub/sub is **fire-and-forget**: Redis doesn't store events, so if nobody is subscribed when one fires, it's gone.
- **Subscribing before the push** removes the main way to miss one.
- **If it's missed anyway** (for example, a dropped connection), the `GET` after the 30 s timeout still finds the result. A missed notification costs latency, not correctness, because the data lives in a key, not in the message.
- **If the worker crashed**, no result ever arrives. The request times out with `success: false` instead of hanging, but the work itself is lost. To make sure no work is lost: use the reliable queue from Deliverable 4 (`LMOVE` to `processing`, acknowledge with `LREM`, re-queue stale items), and have the web server retry or resubmit after a timeout. Because classification is idempotent, running a job twice is safe.

## 6. Stress test fix

**Bug:** each request thread is a **daemon** thread, and Python kills daemon threads as soon as the main thread ends. The original code tried to keep the program alive with `time.sleep(300)`, which is only a guess. When I removed it, the loop started all 20 threads in about 1 s and the program exited before any response came back, so nothing printed. The server still did all 20 classifications and sent them to clients that no longer existed. A fixed sleep wastes time when requests are fast, and kills them anyway when they take longer than 300 s.

**Fix:** keep every thread in a list, then `join()` each one. `join()` blocks the main thread until that thread finishes, so the program waits exactly as long as the slowest request and no longer.

```python
threads = []
for i in range(0, NUM_REQUESTS):
    t = Thread(target=call_predict_endpoint, args=(i,))
    threads.append(t)
    t.daemon = True
    t.start()
    time.sleep(SLEEP_COUNT)

for t in threads:
    t.join()

print("all done")
```

Result: all 20 threads returned OK, and `all done` printed last. Total time was about 3.2 s with one worker, from the first `RPUSH` to the last `DEL` in `MONITOR`.

## 7. Unified logging: a Redis logger

`redis_logger.py` gives every process the same `log(action)` function. Each entry is JSON with the **timestamp, server (hostname:PID), main script name, and action**. It's printed to the process's own terminal and pushed onto one shared Redis list called `logs`, so the web server and every worker write to a single timeline.

```python
SERVER = f"{socket.gethostname()}:{os.getpid()}"
SCRIPT = os.path.basename(sys.argv[0])

def log(action):
	entry = {"time": datetime.datetime.now().isoformat(timespec="milliseconds"),
		"server": SERVER, "script": SCRIPT, "action": action}
	sys.stdout.write("[{time}] {server} {script}: {action}\n".format(**entry))
	try:
		pipe = db.pipeline()
		pipe.rpush(LOG_KEY, json.dumps(entry))
		pipe.ltrim(LOG_KEY, -MAX_ENTRIES, -1)
		pipe.execute()
	except redis.RedisError as e:
		sys.stdout.write(f"[logger] could not write to Redis: {e}\n")
```

**Features:**
- **hostname:PID.** Both workers run on one laptop, so the hostname alone can't tell them apart (`LAPTOP-EQBGA00L:8348` vs `:9456`).
- **One write per entry.** The stress test's `print()` calls produced jumbled output, because each `print` writes the text and the newline separately, and threads take turns in between.
- **Pipeline (`MULTI`/`EXEC`).** `RPUSH` and `LTRIM` go in one round trip and run atomically.
- **Capped list.** `LTRIM logs -1000 -1` keeps only the newest 1000 entries. Unlike the worker bug, trimming by position is *correct* here, because dropping the oldest entries is exactly what we want.
- **Never crashes the caller.** Redis errors are caught, and the entry still prints locally.
- **Tracing.** `python view_logs.py <uuid>` filters the timeline to one request as it crosses processes:

```
21:56:25.942  :4568  run_web_server.py    queued 128b6406…
21:56:26.813  :9456  run_model_server.py  batch of 8
21:56:29.075  :9456  run_model_server.py  set 128b6406…
21:56:29.100  :4568  run_web_server.py    done 128b6406…
```

**What the log showed:**
- **20 queued, 20 done.** Both workers share the load with no losses (since the `LPOP` fix).
- **Batching has a latency cost.** Worker `:9456` grabbed a batch of 8 at 26.813 and didn't finish until 29.06. Meanwhile worker `:8348` finished four batches of 2 in about 0.2 s each. The requests in the big batch waited about 2 s while a worker was free. Also, each worker's *first* batch of a new size took about 1.6–2.2 s and repeat sizes took about 0.2 s, which looks like the model warming up for each new input shape.
- **The log is not perfectly ordered.** `done 128b6406` (29.100) is stored *after* `done 8b5fdae2` (29.112). The timestamp is taken before the `RPUSH`, and another thread's push got there first. So the list is in **arrival order at Redis**, not event order. Across real machines with slightly different clocks this gets worse, which is why distributed systems use synchronized clocks, or sort by timestamp, or use logical clocks.
