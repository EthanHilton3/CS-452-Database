## This script is used to query the database
import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

CONNECTION = os.getenv("CONNECTION")


def run_query(cursor, label, query, params=None):
	cursor.execute(query, params)
	print(f"\n=== {label} ===")
	print([col[0] for col in cursor.description])
	for row in cursor.fetchall():
		print(row)


# Q1-Q4 use L2 distance (<->) from the query segment to every other segment.
# %(seg_id)s is filled in by psycopg2, so the same query serves Q1, Q3 and Q4.
SIMILAR_SEGMENTS = """
	SELECT p.title,
		s.id,
		s.content,
		s.start_time,
		s.end_time,
		s.embedding <-> (SELECT embedding FROM segment WHERE id = %(seg_id)s) AS distance
	FROM segment s
	JOIN podcast p ON s.podcast_id = p.id
	WHERE s.id != %(seg_id)s
	ORDER BY distance
	LIMIT 5;
"""

# DESC is a keyword, not a value, so it can't be a parameter: Q2 needs its own query.
DISSIMILAR_SEGMENTS = """
	SELECT p.title,
		s.id,
		s.content,
		s.start_time,
		s.end_time,
		s.embedding <-> (SELECT embedding FROM segment WHERE id = %(seg_id)s) AS distance
	FROM segment s
	JOIN podcast p ON s.podcast_id = p.id
	WHERE s.id != %(seg_id)s
	ORDER BY distance DESC
	LIMIT 5;
"""

# Q5: five most similar episodes to a segment (average each episode's embeddings)
SIMILAR_EPISODES_TO_SEGMENT = """
	SELECT p.title,
		AVG(s.embedding) <-> (SELECT embedding FROM segment WHERE id = %(seg_id)s) AS distance
	FROM segment s
	JOIN podcast p ON s.podcast_id = p.id
	WHERE s.podcast_id != (SELECT podcast_id FROM segment WHERE id = %(seg_id)s)
	GROUP BY p.id, p.title
	ORDER BY distance
	LIMIT 5;
"""

# Q6: five most similar episodes to an episode (average embeddings on both sides)
SIMILAR_EPISODES_TO_EPISODE = """
	SELECT p.title,
		AVG(s.embedding) <-> (SELECT AVG(embedding) FROM segment WHERE podcast_id = %(podcast_id)s) AS distance
	FROM segment s
	JOIN podcast p ON s.podcast_id = p.id
	WHERE s.podcast_id != %(podcast_id)s
	GROUP BY p.id, p.title
	ORDER BY distance
	LIMIT 5;
"""


conn = psycopg2.connect(CONNECTION)
cursor = conn.cursor()

# Q1) Input: "that if we were to meet alien life at some point"
run_query(cursor, 'Q1: five most similar segments to "267:476"', SIMILAR_SEGMENTS, {"seg_id": "267:476"})

# Q2) Input: "that if we were to meet alien life at some point"
run_query(cursor, 'Q2: five most dissimilar segments to "267:476"', DISSIMILAR_SEGMENTS, {"seg_id": "267:476"})

# Q3) Input: "Is it is there something especially interesting and profound to you in terms of our current
# deep learning neural network, artificial neural network approaches and the whatever we do understand
# about the biological neural network."
run_query(cursor, 'Q3: five most similar segments to "48:511"', SIMILAR_SEGMENTS, {"seg_id": "48:511"})

# Q4) Input: "But what about like the fundamental physics of dark energy? Is there any understanding of what the heck it is?"
run_query(cursor, 'Q4: five most similar segments to "51:56"', SIMILAR_SEGMENTS, {"seg_id": "51:56"})

# Q5) For each segment, the five most similar podcast episodes (return title and distance)
for seg_id in ["267:476", "48:511", "51:56"]:
	run_query(cursor, f'Q5: five most similar episodes to "{seg_id}"', SIMILAR_EPISODES_TO_SEGMENT, {"seg_id": seg_id})

# Q6) Input episode: "Balaji Srinivasan: How to Fix Government, Twitter, Science, and the FDA | Lex Fridman Podcast #331"
run_query(cursor, 'Q6: five most similar episodes to "VeH7qKZr0WI"', SIMILAR_EPISODES_TO_EPISODE, {"podcast_id": "VeH7qKZr0WI"})

cursor.close()
conn.close()
