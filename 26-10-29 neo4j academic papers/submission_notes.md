# Neo4j Academic Papers: submission notes

## 1. Bacon Path for Nora Ephron
Screenshot: `bacon_path.png`

```cypher
MATCH p = shortestPath(
  (bacon:Person {name: "Kevin Bacon"})-[r*1..4]-(nora:Person {name: "Nora Ephron"})
)
RETURN p
```
4 hops: Kevin Bacon → Apollo 13 ← Tom Hanks → You've Got Mail ← Nora Ephron (directed)

## 2. inDegree vs Category chart
Screenshot: `category_chart.png` (from the notebook)

## 3. Total papers in CS categories: **5,812**

```cypher
MATCH (p:Paper)-[:IN_CATEGORY]->(c:Category)
WHERE c.category STARTS WITH "cs."
RETURN count(DISTINCT p) AS total
```

## 4. Unique papers vs. per-category count
I counted **unique papers** (5,812). That's the true number of CS papers in the dataset. Counting a paper once for every CS category it's listed in inflates the number for no reason.

The other way, `count(p)` without DISTINCT, gives **7,891**. The difference of 2,079 comes from cross-listed papers. 1,792 papers (about 31% of CS papers) are in two or more CS categories, and the non-distinct count includes each one once per CS category.

## 5. My own query: which pairs of authors co-wrote the most papers?

```cypher
MATCH (a1:Author)-[:AUTHORED]->(p:Paper)<-[:AUTHORED]-(a2:Author)
WHERE a1.name < a2.name
RETURN a1.name, a2.name, count(p) AS collaboration_count
ORDER BY collaboration_count DESC
LIMIT 10
```

| a1.name | a2.name | collaboration_count |
|---|---|---|
| The BABAR Collaboration | B. Aubert | 115 |
| Damien Chablat | Philippe Wenger | 70 |
| D0 Collaboration | V. Abazov | 50 |
| CDF Collaboration | T. Aaltonen | 44 |
| G. F. Chen | N. L. Wang | 42 |
| M. Mayor | S. Udry | 39 |
| J. L. Luo | N. L. Wang | 39 |
| G. F. Chen | J. L. Luo | 38 |
| D. Queloz | S. Udry | 37 |
| D. Queloz | M. Mayor | 35 |

What I learned:

- `a1.name < a2.name` keeps one copy of each pair. Without it, every pair appears twice (A,B and B,A).
- My first version had no `ORDER BY`/`LIMIT` and took 45+ seconds, because it returned all ~1.57 million pair rows to Python. Pairs grow with the square of the author count. One paper has 443 authors, which alone creates about 98,000 pairs.
- Three of the top pairs are data artifacts. Physics collaborations (BABAR, D0, CDF) were parsed as "authors" and paired with the alphabetically first real author.
- Chen–Wang–Luo and Mayor–Udry–Queloz each form a **triangle**: every pair in the group co-authored. Triangles reveal research communities (the Mayor/Queloz team won the 2019 Nobel Prize in Physics for exoplanets).
