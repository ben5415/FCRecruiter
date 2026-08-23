"""Normalize the FC26 CSV into countries, leagues, clubs, and players.

This is a destructive import: the four destination tables are rebuilt. Run it
from the repository root with:

    python scripts/normalize_players.py --apply

The import is wrapped in one PostgreSQL transaction, so a validation or SQL
error leaves the existing tables unchanged.
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine, text


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CSV_PATH = PROJECT_ROOT / "dataset" / "fc26.csv"

ENTITY_COLUMNS = {
    "countries": ["nationality_id", "nationality_name", "nation_team_id"],
    "leagues": ["league_id", "league_name", "league_level"],
    "clubs": ["club_team_id", "club_name", "league_id"],
}

# These descriptions live in their entity tables. IDs stay on players as FKs.
PLAYER_COLUMNS_TO_REMOVE = {
    "nationality_name",
    "nation_team_id",
    "league_id",
    "league_name",
    "league_level",
    "club_name",
}

INTEGER_COLUMNS = {
    "player_id",
    "nationality_id",
    "nation_team_id",
    "league_id",
    "league_level",
    "club_team_id",
}

# PostgreSQL's extended query protocol supports at most 65,535 bind
# parameters. Keep some headroom for driver-generated parameters.
MAX_BIND_PARAMETERS_PER_BATCH = 60_000
MAX_ROWS_PER_BATCH = 1_000


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Rebuild normalized FC26 tables from dataset/fc26.csv."
    )
    parser.add_argument(
        "--csv",
        type=Path,
        default=DEFAULT_CSV_PATH,
        help=f"CSV source path (default: {DEFAULT_CSV_PATH})",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Confirm that the destination tables may be replaced.",
    )
    return parser.parse_args()


def require_columns(df: pd.DataFrame) -> None:
    required = {"player_id", *PLAYER_COLUMNS_TO_REMOVE, "club_team_id", "nationality_id"}
    missing = sorted(required.difference(df.columns))
    if missing:
        raise ValueError(f"CSV is missing required columns: {', '.join(missing)}")


def normalize_integer_columns(df: pd.DataFrame) -> None:
    for column in INTEGER_COLUMNS.intersection(df.columns):
        df[column] = pd.to_numeric(df[column], errors="raise").astype("Int64")


def assert_unique_mapping(
    df: pd.DataFrame,
    *,
    entity: str,
    id_column: str,
    value_columns: list[str],
) -> None:
    """Reject one source ID mapping to conflicting entity descriptions."""
    populated = df.dropna(subset=[id_column])
    for column in value_columns:
        conflicts = populated.groupby(id_column, dropna=False)[column].nunique(dropna=True)
        conflicting_ids = conflicts[conflicts > 1].index.tolist()
        if conflicting_ids:
            sample = ", ".join(str(value) for value in conflicting_ids[:5])
            raise ValueError(
                f"Conflicting {entity}.{column} values for {id_column}: {sample}"
            )


def build_tables(source: pd.DataFrame) -> dict[str, pd.DataFrame]:
    require_columns(source)
    normalize_integer_columns(source)

    if source["player_id"].isna().any():
        raise ValueError("player_id cannot be null")
    if source["player_id"].duplicated().any():
        duplicates = source.loc[source["player_id"].duplicated(), "player_id"].head()
        raise ValueError(f"Duplicate player_id values: {duplicates.tolist()}")

    assert_unique_mapping(
        source,
        entity="country",
        id_column="nationality_id",
        value_columns=["nationality_name", "nation_team_id"],
    )
    assert_unique_mapping(
        source,
        entity="league",
        id_column="league_id",
        value_columns=["league_name", "league_level"],
    )
    assert_unique_mapping(
        source,
        entity="club",
        id_column="club_team_id",
        value_columns=["club_name", "league_id"],
    )

    countries = (
        source[ENTITY_COLUMNS["countries"]]
        .dropna(subset=["nationality_id"])
        .drop_duplicates(subset=["nationality_id"])
        .reset_index(drop=True)
    )
    leagues = (
        source[ENTITY_COLUMNS["leagues"]]
        .dropna(subset=["league_id"])
        .drop_duplicates(subset=["league_id"])
        .reset_index(drop=True)
    )
    clubs = (
        source[ENTITY_COLUMNS["clubs"]]
        .dropna(subset=["club_team_id"])
        .drop_duplicates(subset=["club_team_id"])
        .reset_index(drop=True)
    )
    players = source.drop(columns=sorted(PLAYER_COLUMNS_TO_REMOVE)).copy()

    return {
        "countries": countries,
        "leagues": leagues,
        "clubs": clubs,
        "players": players,
    }


def rebuild_tables(database_url: str, tables: dict[str, pd.DataFrame]) -> None:
    engine = create_engine(database_url)

    # Fixed staging names are safe because the entire operation is transactional.
    staging_names = {name: f"_{name}_new" for name in tables}

    with engine.begin() as connection:
        for staging_name in staging_names.values():
            connection.execute(text(f'DROP TABLE IF EXISTS "{staging_name}"'))

        for name in ("countries", "leagues", "clubs", "players"):
            column_count = len(tables[name].columns)
            chunksize = min(
                MAX_ROWS_PER_BATCH,
                max(1, MAX_BIND_PARAMETERS_PER_BATCH // column_count),
            )
            tables[name].to_sql(
                staging_names[name],
                connection,
                if_exists="fail",
                index=False,
                chunksize=chunksize,
                method="multi",
            )

        connection.execute(text("ALTER TABLE _countries_new ADD PRIMARY KEY (nationality_id)"))
        connection.execute(text("ALTER TABLE _leagues_new ADD PRIMARY KEY (league_id)"))
        connection.execute(text("ALTER TABLE _clubs_new ADD PRIMARY KEY (club_team_id)"))
        connection.execute(text("ALTER TABLE _players_new ADD PRIMARY KEY (player_id)"))

        connection.execute(
            text(
                "ALTER TABLE _clubs_new "
                "ADD CONSTRAINT fk_clubs_league "
                "FOREIGN KEY (league_id) REFERENCES _leagues_new (league_id)"
            )
        )
        connection.execute(
            text(
                "ALTER TABLE _players_new "
                "ADD CONSTRAINT fk_players_club "
                "FOREIGN KEY (club_team_id) REFERENCES _clubs_new (club_team_id)"
            )
        )
        connection.execute(
            text(
                "ALTER TABLE _players_new "
                "ADD CONSTRAINT fk_players_country "
                "FOREIGN KEY (nationality_id) REFERENCES _countries_new (nationality_id)"
            )
        )

        # No CASCADE: existing dependent application tables make the import fail
        # instead of being deleted unexpectedly.
        for table_name in ("players", "clubs", "leagues", "countries"):
            connection.execute(text(f'DROP TABLE IF EXISTS "{table_name}"'))

        for name in ("countries", "leagues", "clubs", "players"):
            connection.execute(
                text(f'ALTER TABLE "{staging_names[name]}" RENAME TO "{name}"')
            )

        connection.execute(text("CREATE INDEX idx_clubs_league_id ON clubs (league_id)"))
        connection.execute(text("CREATE INDEX idx_players_club_id ON players (club_team_id)"))
        connection.execute(
            text("CREATE INDEX idx_players_country_id ON players (nationality_id)")
        )
        connection.execute(text("CREATE INDEX idx_players_overall ON players (overall)"))
        connection.execute(text("CREATE INDEX idx_players_value_eur ON players (value_eur)"))


def main() -> None:
    args = parse_args()
    if not args.apply:
        raise SystemExit(
            "Refusing to replace database tables without confirmation. "
            "Run again with --apply."
        )

    load_dotenv(PROJECT_ROOT / ".env")
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        raise SystemExit("DATABASE_URL is not set")

    csv_path = args.csv.resolve()
    if not csv_path.is_file():
        raise SystemExit(f"CSV file not found: {csv_path}")

    source = pd.read_csv(csv_path, low_memory=False)
    tables = build_tables(source)

    print(f"Source:    {len(source):,} rows")
    for name in ("countries", "leagues", "clubs", "players"):
        print(f"{name.title():<11}{len(tables[name]):,} rows")

    rebuild_tables(database_url, tables)
    print("Import finished. The four normalized tables were replaced successfully.")


if __name__ == "__main__":
    main()
