# Learning Log notes: Neo4j Academic Papers

Ethan Hilton · CS 452 · GraphDB (Neo4j): Academic Papers · 10/29/2026

---

## Aha moments (from my own questions)

**1. Arrows in a query are optional. Arrows in the data are not.**
Every relationship is stored with a direction (Person → Movie). My Bacon Path went Bacon → Apollo 13 ← Hanks → You've Got Mail ← Ephron. With `->`, it would need every hop to point the same way and would find nothing. Leaving the arrow out (`-`) traverses in either direction.

**2. Variable-length paths: `-[r*1..4]-`**
`*` repeats the hop, `1..4` sets min and max, and `r` becomes a list of relationships. My cap of 4 was exactly the path length. With `*1..3`, I'd have gotten no results and no error. Use upper bounds only as safety limits.

**3. Why graph traversal is cheap: index-free adjacency.**
Both SQL and graphs grow exponentially with the number of hops. The difference is the cost per hop.
- SQL: each hop is a join with an index lookup into the whole table, so the cost grows with **table size**.
- Neo4j: each node stores pointers to its own relationships, so the cost grows with **neighborhood size**.

**4. Cypher runs inside Python, as a string.**
The notebook is Python, so Cypher goes in `'''...'''` and is sent with `conn.query()`. Pasting raw Cypher into a cell gives a Python syntax error.

**5. Missing properties fail silently.**
`c.name` doesn't exist (it's `c.category`), so it returns `null`, not an error, and my count would quietly have been 0. `STARTS WITH` is case-sensitive: `"CS"` ≠ `"cs."`.

**6. count vs count(DISTINCT): many-to-many double counting.**
- `count(p)` = **7,891** (paper-category pairs)
- `count(DISTINCT p)` = **5,812** (unique CS papers). I chose this one because it's the true number of papers.
- 1,792 papers (31%) are cross-listed in 2+ CS categories. This is the same problem as a SQL JOIN on a many-to-many table.

**7. My co-author query took 45+ seconds.**
No `ORDER BY`/`LIMIT`, so it sent all ~1.57 million pairs to Python. Pairs grow with the **square** of the author count, and one 443-author paper alone creates about 98,000 pairs. Adding `LIMIT 10` returned in seconds. `a1.name < a2.name` removes (A,B)/(B,A) duplicates.

**8. The top "co-authors" were data artifacts.**
"BABAR Collaboration," "D0," and "CDF" are experiments, not people. They were parsed as authors from messy arXiv metadata.

**9. Triangles = communities.**
Mayor–Udry–Queloz (2019 Nobel Prize, exoplanets) and Chen–Wang–Luo all co-authored with each other. In the graph view, 35 of the trio's 55 papers had all 3 authors, and there were 131 relationships vs 55 papers. The layout clusters them together on its own.

**10. LIMIT is not a random sample.**
`RETURN a,p,c LIMIT 300` returned 294 authors and 114 papers, all from **1 category**: it takes the first rows found. Use `ORDER BY rand()` for a real sample. A big graph shown "all at once" is just a blob, so explore from an **anchor node** outward.

**11. Name-as-ID creates fake people.**
The loader made `Author.name` unique, so every "Wei Zhang" in arXiv became one node. My 6-hop path from a robotics researcher to the Nobel team ran through that fake super-person. **A graph is only as true as its identity rules.** Use real IDs (ORCID), not names.

---

## Key concepts

- **Property graph:** nodes (things) with **labels** (`:Paper`), **relationships** (`:AUTHORED`) with a type and direction, and **properties** (key-value pairs) on both.
- **MATCH** describes a pattern as ASCII art: `(a:Author)-[:AUTHORED]->(p:Paper)`.
- **shortestPath** is a breadth-first search that stops at the first match.
- **No GROUP BY:** non-aggregated columns in `RETURN`/`WITH` become the grouping keys automatically. Adding a column changes the groups. To group by something you don't return, aggregate in `WITH` first.
- **MERGE vs CREATE**
  - MERGE = find or create (an upsert), so reloading is safe (idempotent).
  - CREATE = always new. It's faster, and right for events/orders, clean bulk loads, and meaningful duplicate relationships.
  - Trap: MERGE matches the *whole* pattern, so MATCH the nodes first and then MERGE the relationship.
- **Uniqueness constraints** reject duplicates *and* build an index, so MERGE doesn't scan every node. Graphs still use indexes, but only to find **starting points**.
- **UNWIND** turns a list into rows, which is how the notebook batch-loaded 100k papers in about 40 seconds.
- **Degree** = number of relationships on a node.
  - Measures importance (degree centrality).
  - Spots hubs and bad data (443-author paper).
  - Predicts slow queries (supernodes).
  - Neo4j stores degree counts, which is why `apoc.node.degree` is fast. **APOC** is Neo4j's plugin library.
- **Graph vs relational**
  - Graph: connection questions (paths, neighbors, hops, communities, recommendations).
  - Relational: whole-table totals, reporting, strict tabular data.
  - My CS count works fine in SQL. The Bacon Path needs a recursive CTE.

---

## What I'd do differently / still want to try
- Show off multi-hop queries: an academic Bacon Path (Chablat → Mayor in 6 co-author hops), and "co-authors of co-authors" recommendations.
- Fix identity: unique Author IDs instead of names.
- Try the Neo4j Browser Movies guide (`:guide movies`) for CREATE and recommendation patterns.
