from pathlib import Path
from time import perf_counter
import psycopg
import os
import climato.spikes.daily_wide_long as dwl


SCHEMA = "spike"
DUMP_DIR = dwl.get_dump_dir()


def get_table_count(
        conn: psycopg.Connection,
        table: str,
) -> int:
    count_query = psycopg.sql.SQL(
        """
        SELECT COUNT(*) FROM {}
        """
    ).format(
        psycopg.sql.Identifier(SCHEMA, table)
    )

    with conn.cursor() as cur:
        cur.execute(count_query)        
        return int(cur.fetchone()[0])


def print_table_count(
        conn: psycopg.Connection,
        table: str,
):
    print(f"Table {SCHEMA}.{table} contains {get_table_count(conn, table)} rows.")


def copy_csv(
        conn: psycopg.Connection,     
        table: str,
        filepath: Path,
) -> float:
    copy_query = psycopg.sql.SQL(
        """
        COPY {}
        FROM STDIN
        WITH (
            FORMAT CSV,
            DELIMITER ';',
            HEADER TRUE
        )
        """
    ).format(
        psycopg.sql.Identifier(SCHEMA, table)
    )

    start = perf_counter()

    with conn.cursor() as cur:
        with cur.copy(copy_query) as copy:
            with filepath.open("rb") as file:           
                while chunk := file.read(1024 * 1024):
                    copy.write(chunk)

    return perf_counter() - start


def populate_spike_table_print(
        conn: psycopg.Connection,
        table: str,
        filename: str | None = None,
) -> None:
    if filename is None:
        filename = f"{table}.csv"
    filepath = DUMP_DIR / filename
    size_mib = filepath.stat().st_size / 1024**2
    elapsed = copy_csv(conn, table, filepath)
    count = get_table_count(conn, table)
    print(
        f"Loaded {SCHEMA}.{table}: "
        f"{count} rows in {elapsed:.3f} s "
        f"(Input file: {size_mib} MiB -> Rate: {size_mib / elapsed:.1f} MiB/s)"
    )


def main() -> None:
    with psycopg.connect(
        host=os.environ["POSTGRES_HOST"],
        port=os.environ["POSTGRES_PORT"],
        dbname=os.environ["POSTGRES_DB"],
        user=os.environ["POSTGRES_USER"],
        password=os.environ["POSTGRES_PASSWORD"],
    ) as conn:
        table = "stations"
        elapsed = copy_csv(conn, table, DUMP_DIR / "stations.csv")
        count = get_table_count(conn, table)
        print(f"Loaded spike.{table}: "
              f"{count} rows in {elapsed:.3f} s")

        table = "parameters"
        elapsed = copy_csv(conn, table, DUMP_DIR / "parameters.csv")
        count = get_table_count(conn, table)
        print(f"Loaded spike.{table}: "
                f"{count} rows in {elapsed:.3f} s")

        table = "daily_rr_t_vent_wide"
        elapsed = copy_csv(conn, table, DUMP_DIR / "daily_rr_t_vent_wide.csv")
        count = get_table_count(conn, table)
        print(f"Loaded spike.{table}: "
                f"{count} rows in {elapsed:.3f} s")

        table = "daily_autres_parametres_wide"
        elapsed = copy_csv(conn, table, DUMP_DIR / "daily_autres_parametres_wide.csv")
        count = get_table_count(conn, table)
        print(f"Loaded spike.{table}: "
                f"{count} rows in {elapsed:.3f} s")

        table = "daily_long"
        elapsed = copy_csv(conn, table, DUMP_DIR / "daily_long.csv")
        count = get_table_count(conn, table)
        print(f"Loaded spike.{table}: "
                f"{count} rows in {elapsed:.3f} s")

if __name__ == "__main__":
    main()
