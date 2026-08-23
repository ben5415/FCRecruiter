import os

import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

load_dotenv()

DATABASE_URL = os.environ["DATABASE_URL"]
CSV_PATH = "dataset/fc26.csv"

engine = create_engine(DATABASE_URL)

df = pd.read_csv(CSV_PATH)

print(f"CSV rows: {len(df)}")
print(f"CSV columns: {len(df.columns)}")

date_columns = [
    "fifa_update_date",
    "dob",
    "club_joined_date",
]

for col in date_columns:
    if col in df.columns:
        df[col] = pd.to_datetime(df[col], errors="coerce")

df.to_sql(
    "players",
    engine,
    if_exists="replace",
    index=False,
    chunksize=100,
)

print("Import finished.")

with engine.connect() as conn:
    count = conn.execute(
        text("SELECT COUNT(*) FROM players")
    ).scalar()

print(f"Database rows: {count}")