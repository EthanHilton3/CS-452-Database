## This script is used to create the tables in the database

import os
from dotenv import load_dotenv
import psycopg2

load_dotenv()

CONNECTION = os.getenv("CONNECTION")

# need to run this to enable vector data type
CREATE_EXTENSION = "CREATE EXTENSION IF NOT EXISTS vector"

# TODO: Add create table statement
CREATE_PODCAST_TABLE = """
CREATE TABLE IF NOT EXISTS podcast (
	id TEXT PRIMARY KEY,
	title TEXT NOT NULL
)
"""
# TODO: Add create table statement
CREATE_SEGMENT_TABLE = """
CREATE TABLE IF NOT EXISTS segment (
	id TEXT PRIMARY KEY,
	start_time FLOAT NOT NULL,
	end_time FLOAT NOT NULL,
	podcast_id TEXT NOT NULL REFERENCES podcast(id),
	content TEXT NOT NULL,
	embedding vector(128) NOT NULL
)
"""

conn = psycopg2.connect(CONNECTION)
# TODO: Create tables with psycopg2 (example: https://www.geeksforgeeks.org/executing-sql-query-with-psycopg2-in-python/)
cursor = conn.cursor()
cursor.execute(CREATE_EXTENSION)
cursor.execute(CREATE_PODCAST_TABLE)
cursor.execute(CREATE_SEGMENT_TABLE)
conn.commit()
conn.close()