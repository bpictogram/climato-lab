import polars as pl
import climato.config as config
from climato.sources.meteo_france.daily import (
    COLLECTIONS,
    PARAMETER_FAMILIES,
    DEPARTMENTS,
    PERIODS,
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


def main():
    candidates = build_candidate_resources_list(
        departments=DEPARTMENTS,
        parameter_families=PARAMETER_FAMILIES,
        collections=COLLECTIONS,
        periods=PERIODS,
        dataset_year=2026,
    )

    resources_by_path = {
        resource["raw_relative_path"]: resource
        for resource in candidates
    }

    df_reports = (
        pl.scan_ndjson(
            list(REPORT_DIR.rglob("*.jsonl")),
            schema_overrides={
                "checked_at": pl.Datetime(time_zone="UTC"),
                "downloaded_at": pl.Datetime(time_zone="UTC"),
                "source_last_modified_at": pl.Datetime(time_zone="UTC"),
            },
        )
        .collect()
    )

    for path in RAW_DATA_DIR.rglob("*.csv.gz"):
        relative_path_str = path.relative_to(
            RAW_DATA_DIR
        ).as_posix()

        resource = resources_by_path[relative_path_str]

        resource_events = (
           df_reports
           .filter(
               *(pl.col(key) == resource[key] for key in RESOURCE_KEY_FIELDS),
           )
        )

        latest_event = (
           resource_events
           .filter(
               pl.col("checked_at").is_not_null(),
           )
           .sort("checked_at", descending=True)
           .row(0)
        )

        latest_success = (
           resource_events
           .filter(
               pl.col("status") == "success",
           )
           .sort("downloaded_at", descending=True)
           .row(0)
        )

        


if __name__ == "__main__":
    main()
