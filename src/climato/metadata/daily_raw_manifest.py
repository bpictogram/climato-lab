import shutil

import polars as pl

from climato.utils.colors import Color
from climato.utils.datetime import utc_now_iso
from climato.utils.json import DatetimeJSONEncoder, pprint_dict
import climato.config as config
from climato.sources.meteo_france.daily import (
    COLLECTIONS,
    PARAMETER_FAMILIES,
    DEPARTMENTS,
    PERIOD_KEYS,
    build_candidate_resources_list,
)

DATA_DIR = config.get_data_dir()
RAW_DATA_DIR = config.get_raw_data_dir()
METADATA_DIR = DATA_DIR / "metadata"
REPORT_DIR = METADATA_DIR / "downloads" / "daily"

RESOURCE_KEY_FIELDS = (
    "dataset_year",
    "collection",
    "parameter_family",
    "department",
    "period",
)


def read_download_events():
    return (
        pl.read_ndjson(
            list(REPORT_DIR.rglob("*.jsonl")),
            schema_overrides={
                "attempted_at": pl.Datetime(time_zone="UTC"),
                "checked_at": pl.Datetime(time_zone="UTC"),
                "downloaded_at": pl.Datetime(time_zone="UTC"),
                "source_last_modified_at": pl.Datetime(time_zone="UTC"),
            },
        )
    )


def build_latest_event_tables(
        reports: pl.DataFrame,
) -> tuple[pl.DataFrame, pl.DataFrame]:
    latest_events = (
        reports
        .sort("attempted_at", descending=True)
        .unique(
            subset=RESOURCE_KEY_FIELDS,
            keep="first",
            maintain_order=True,
        )
        .select(
            *RESOURCE_KEY_FIELDS,
            pl.col("status").alias("last_attempt_status"),
            pl.col("http_status").alias("last_http_status"),
            pl.col("attempted_at").alias("last_attempted_at"),
            pl.col("checked_at").alias("last_checked_at"),
        )
    )

    latest_successes = (
        reports
        .filter(pl.col("status") == "success")
        .sort("downloaded_at", descending=True)
        .unique(
            subset=RESOURCE_KEY_FIELDS,
            keep="first",
            maintain_order=True,
        )
        .select(
            *RESOURCE_KEY_FIELDS,
            pl.col("size_bytes").alias("download_size_bytes"),
            "downloaded_at",
            "etag",
            "source_last_modified_at",
            "sha256",
        )
    )

    return latest_events, latest_successes


def scan_raw_files() -> pl.DataFrame:
    candidates = build_candidate_resources_list(
        departments=DEPARTMENTS,
        parameter_families=PARAMETER_FAMILIES,
        collections=COLLECTIONS,
        periods=PERIOD_KEYS,
        dataset_year=2026,
    )

    resources_by_path = {
        resource["raw_relative_path"]: {
            **resource,
            "resource_order": resource_order,
        }
        for resource_order, resource in enumerate(candidates)
    }

    raw_rows = []

    for path in RAW_DATA_DIR.rglob("*.csv.gz"):
        relative_path = (
            path
            .relative_to(RAW_DATA_DIR)
            .as_posix()
        )

        resource = resources_by_path.get(relative_path)

        if resource is None:
            raw_rows.append({
                "raw_relative_path": relative_path,
                "local_size_bytes": path.stat().st_size,
                "contract_status": "unrecognized",
                "resource_order": None,
            })
            continue

        raw_rows.append({
            **resource,
            "local_size_bytes": path.stat().st_size,
            "contract_status": "recognized",
        })

    return pl.DataFrame(raw_rows)


def build_raw_manifest(
        raw_files: pl.DataFrame,
        latest_events: pl.DataFrame,
        latest_successes: pl.DataFrame,
) -> pl.DataFrame:
    df_unrecognized = raw_files.filter(
        pl.col("contract_status") == "unrecognized",
    )

    if df_unrecognized.height:
        print(df_unrecognized)

    
    df_manifest = (
        raw_files
        .filter(pl.col("contract_status") == "recognized")
        .join(
            latest_successes,
            on=RESOURCE_KEY_FIELDS,
            how="left",
        )
        .join(
            latest_events,
            on=RESOURCE_KEY_FIELDS,
            how="left",
        )
    )

    df_manifest = df_manifest.with_columns(
        pl.when(pl.col("downloaded_at").is_null())
        .then(pl.lit("untracked"))

        .when(pl.col("local_size_bytes") != pl.col("download_size_bytes"))
        .then(pl.lit("size_mismatch"))

        .otherwise(pl.lit("ok"))

        .alias("integrity_status")
    )

    return (
        df_manifest
        .sort("resource_order")
        .drop("resource_order")
    )


def main():
    df_reports = read_download_events()

    latest_events, latest_successes = build_latest_event_tables(df_reports)

    df_raw_files = scan_raw_files()

    df_manifest = build_raw_manifest(df_raw_files, latest_events, latest_successes)

    print(df_manifest)

    manifest_dir = METADATA_DIR / "manifests"
    manifest_dir.mkdir(parents=True, exist_ok=True)
    ts = utc_now_iso()
    manifest_filename = "daily_files"
    manifest_filename_ts = f"{manifest_filename}_{ts}"
    csv_path_ts = manifest_dir / f"{manifest_filename_ts}.csv"
    parquet_path_ts = manifest_dir / f"{manifest_filename_ts}.parquet"
    csv_path = manifest_dir / f"{manifest_filename}.csv"
    parquet_path = manifest_dir / f"{manifest_filename}.parquet"
    df_manifest.write_csv(csv_path_ts, separator=";")
    shutil.copy(csv_path_ts, csv_path)
    df_manifest.write_parquet(manifest_dir / f"{manifest_filename_ts}.parquet")
    shutil.copy(parquet_path_ts, parquet_path)

        # resource_events = (
        #    df_reports
        #    .filter(
        #        *(pl.col(key) == resource[key] for key in RESOURCE_KEY_FIELDS),
        #    )
        # )

        # latest_event = (
        #    resource_events
        #    .filter(
        #        pl.col("checked_at").is_not_null(),
        #    )
        #    .sort("checked_at", descending=True)
        #    .row(0, named=True)
        # )

        # latest_success = (
        #    resource_events
        #    .filter(
        #        pl.col("status") == "success",
        #    )
        #    .sort("downloaded_at", descending=True)
        #    .row(0, named=True)
        # )

        # pprint_dict(latest_event)
        # pprint_dict(latest_success)
        # print(f"latest_event == latest_success: {latest_event == latest_success}")
        # print(f"path.stat().st_size: {path.stat().st_size}")
        # print(f"""latest_success["size_bytes"]: {latest_success["size_bytes"]}""")

        # manifest_line = {
        #     "collection": resource["collection"],
        #     "parameter_family": resource["parameter_family"],
        #     "department": resource["department"],
        #     "period": resource["period"],
        #     "dataset_year": resource["dataset_year"],
        #     "source_url": latest_success["source_url"],
        #     "source_filename": latest_success["source_filename"],
        #     "last_check_status": latest_event["status"],
        #     "last_http_status": latest_event["http_status"],
        #     "size_bytes": latest_success["size_bytes"],
        #     "last_checked_at": latest_event["checked_at"],
        #     "downloaded_at": latest_success["downloaded_at"],
        #     "etag": latest_success["etag"],
        #     "source_last_modified_at": latest_success["source_last_modified_at"],
        #     "sha256": latest_success["sha256"],
        # }

        # print(f"{Color.YELLOW}")
        # pprint_dict(manifest_line)
        # print(f"{Color.RESET}")

        # return 


if __name__ == "__main__":
    main()
