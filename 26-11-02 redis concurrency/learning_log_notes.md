# Learning Log notes: Redis Concurrency

Ethan Hilton · CS 452 · Redis Project (Concurrency) · 11/2/2026

---

## Aha moments

**1. Redis is a shared dictionary that lives on a server.**
Keys map to values (strings, lists, …), and any program connected to Redis can read and change them. The web server and the worker never talk to each other directly. They only communicate through Redis.
*Summary: Redis is the middleman that lets separate programs share data.*

**2. A list can be a line of jobs.**
`RPUSH` adds a job to the back of the line, and `LPOP` takes one from the front: first in, first out. Watch out for the names: the L in `LPOP` means "left," but the L in `LRANGE` and `LTRIM` just means "List."
*Summary: Push on the right and pop on the left, and a list becomes a work queue.*

**3. The UUID is a return address.**
The web server makes up a random ID, puts it on the job, and waits. The worker saves its answer under a key with that exact name, so the web server knows where to look.
*Summary: A random ID lets two programs match up a request with its answer.*

**4. Polling is wasteful.**
`MONITOR` showed the web server asking "is it ready yet?" 9 times for one request, and the workers checking the empty queue 4 times a second forever. The stress test produced about 240 useless checks.
*Summary: Constantly asking "is it done?" costs work even when nothing is happening.*

**5. Daemon threads die when the program ends.**
Without `sleep(300)`, the stress test printed nothing, because Python kills daemon threads as soon as the main program finishes. The server still did all the work, but nobody was left to receive it.
*Summary: Background threads get killed at exit unless you wait for them.*

**6. `join()` means "wait for this thread to finish."**
Start all the threads first, then `join()` each one. They still run at the same time, and the program waits exactly as long as the slowest one. `sleep(300)` was just a guess.
*Summary: `join()` waits exactly as long as needed, no more and no less.*

**7. The race condition: reading and removing were two separate steps.**
The worker read jobs with `LRANGE`, spent about 2 seconds on them, then deleted "the first N" with `LTRIM`. With two workers, both read the same jobs, and then their deletes removed new jobs nobody had done. Those requests hung forever (threads 10, 13, 17, 19). The jobs both workers did left extra result keys that nobody would ever read ("orphans").
*Summary: When there's a gap between reading something and acting on it, another worker can change things in that gap.*

**8. Race conditions don't happen every time.**
My first two-worker test passed. The bug only showed up when new jobs arrived while the workers were busy, so I had to spread out the requests to catch it.
*Summary: A passing test doesn't prove there's no race; it might just be lucky timing.*

**9. One Redis command can't be interrupted (it's atomic).**
Redis runs one command at a time, so nothing can happen in the middle of a single command. `LPOP` takes *and* removes a job in one step, so two workers can never get the same job.
*Summary: Fix a race by turning "read, then remove" into one atomic command.*

**10. My fix almost created a busy loop.**
`if queue is None: continue` skipped the sleep at the bottom of the loop, so an idle worker would have hammered Redis thousands of times a second. Changing it to `... or []` fixed that.
*Summary: Every path through a waiting loop needs a pause.*

**11. Losing work vs. doing it twice (the kitchen analogy).**
`LPOP` is a cook putting the order ticket in his pocket. If he faints, the order is gone. The fix is a "cooking now" board: move the ticket there in **one motion** (`LMOVE`), throw it away when the food is done, and have a manager put back any ticket that's been sitting there too long. Now nothing is lost, but a slow cook's order might get made twice.
*Summary: You can trade "might lose work" for "might do work twice."*

**12. Idempotent = doing it twice has the same effect as doing it once.**
Pressing an elevator button twice still takes you to the same floor. Saving the same classification result twice writes the same answer to the same key. So running a job twice is harmless here. Charging a credit card twice would not be.
*Summary: Retrying is safe only when the job is idempotent.*

**13. Push notifications instead of polling.**
After `CONFIG SET notify-keyspace-events KEA`, Redis announces whenever a key changes. The web server subscribes to its own result key and waits, sending no commands until Redis tells it the answer is ready. Empty checks went from 9 to 0, and response time went from about 170 ms to about 1.6 ms. Rules: subscribe **before** sending the job, and do one final `GET` in case the announcement was missed.
*Summary: Being told when something's ready beats asking over and over.*

**14. "No conflicts" is not the same as "scales well."**
Multiple web servers are safe, because each one only touches its own keys. UUIDs won't collide: you'd need about 2.7 × 10¹⁸ of them for a 50% chance of a single collision. But notifications still cost more with every request that's waiting.
*Summary: Something can be correct and still get more expensive as it grows.*

**15. One shared log for all the programs.**
Every program writes to one Redis list, so I can read a single timeline and follow one request across programs. I needed the PID to tell my two workers apart, since they run on the same laptop. Log entries are stored in the order they *arrived*, not the order they *happened*.
*Summary: A shared log shows the whole system, but its order isn't perfectly reliable.*

**16. Check which Python you're running.**
`No module named redis` happened because my terminal was using the neo4j project's `.venv`. Both folders are named `.venv`, so they look the same. `which python` shows the real one.
*Summary: When an import fails, check which environment is active first.*

---

## The big lesson
The same bug kept coming back: **a gap between two steps** where someone else can change something. (`LRANGE` then `LTRIM`. "Copy then pop." `print` text, then the newline.) The fix is always to **make it one step that can't be interrupted.**
