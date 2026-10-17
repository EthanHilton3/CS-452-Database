## This script is used to insert data into the database
import os
import json
from dotenv import load_dotenv
import pandas as pd
from utils import fast_pg_insert

load_dotenv()


# TODO: Read the embedding files
EMB_DIR = "data/embedding"
emb_rows = []
for filename in os.listdir(EMB_DIR):          # just the names, e.g. "0lw3....jsonl"
	path = os.path.join(EMB_DIR, filename)    # "data/embedding/0lw3....jsonl"
	with open(path, encoding="utf-8") as f:
		for line in f:
			record = json.loads(line)
			emb_rows.append({
				"id": record["custom_id"],
				"embedding": record["response"]["body"]["data"][0]["embedding"],
			})

emb_df = pd.DataFrame(emb_rows)

# TODO: Read documents files
DOC_DIR = "data/documents"
doc_rows = []
for filename in os.listdir(DOC_DIR):
	path = os.path.join(DOC_DIR, filename)
	with open(path, encoding="utf-8") as f:
		for line in f:
			record = json.loads(line)
			meta = record["body"]["metadata"]
			doc_rows.append({
				"id": record["custom_id"],
				"content": record["body"]["input"],
				"start_time": meta["start_time"],
				"end_time": meta["stop_time"],
				"podcast_id": meta["podcast_id"],
				"title": meta["title"],
			})

doc_df = pd.DataFrame(doc_rows)


# print(len(emb_df), len(doc_df))   # both should be ~832,839
# print(doc_df.head())


# TODO: Insert into postgres
# HINT: use the utils.fast_pg_insert function to insert data into the database
# otherwise inserting the 800k documents will take a very, very long time
merged_df = pd.merge(doc_df, emb_df, on="id", how="inner")
# print(len(merged_df))
# print(merged_df.head())
podcast_df = merged_df[["podcast_id", "title"]].drop_duplicates().rename(columns={"podcast_id": "id"})
podcast_df["title"] = podcast_df["title"].str.removeprefix("Podcast: ")
segment_df = merged_df[["id", "start_time", "end_time", "content", "embedding", "podcast_id"]]
# print(podcast_df.head())
# print(segment_df.head())

CONNECTION = os.getenv("CONNECTION")

fast_pg_insert(podcast_df, CONNECTION, "podcast", ["id", "title"])
fast_pg_insert(segment_df, CONNECTION, "segment", ["id", "start_time", "end_time", "content", "embedding", "podcast_id"])
