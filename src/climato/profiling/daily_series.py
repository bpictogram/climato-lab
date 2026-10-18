import csv
from datetime import date
import gzip
import json
from pathlib import Path
import sys
import time
from typing import Iterable

import polars as pl

import climato.config as config
from climato.sources.meteo_france import daily


DATA_DIR = config.get_data_dir()
RAW_DATA_DIR = config.get_raw_data_dir()
MANIFEST_DIR = DATA_DIR / "metadata" / "manifests"
MANIFEST_PATH = MANIFEST_DIR / "daily_files.parquet"
PROCESSED_DIR = DATA_DIR / "processed"
PROCESSED_DAILY_DIR = PROCESSED_DIR / daily.MF_DAILY_RELATIVE_PATH


def main():
    # Read processed Parquet
    lf_tntxm = (
        pl.scan_parquet(
            PROCESSED_DAILY_DIR / "parameter_family=rr_t_vent",
            hive_partitioning=True,
            hive_schema={
                "dataset_year": pl.UInt16,
                "department": pl.String,
                "collection": pl.String,
                "period": pl.String,
            },
        )
        .filter(
            pl.col("collection") == "quot",
            pl.col("tntxm").is_not_null(),
            # pl.col("department").str.to_integer().is_between(70, 79),
            # pl.col("period") == "latest",
        )
        .select("station_id", "station_name", "obs_date", "tntxm")
        .group_by("station_id", "station_name")
        .agg(
            n_obs=pl.len(),
            first_obs=pl.col("obs_date").min(),
            last_obs=pl.col("obs_date").max(),
        )
        .with_columns(
            ((pl.col("last_obs") - pl.col("first_obs")).dt.total_days() + 1).alias("span_days"),
            pl.lit("tntxm").alias("parameter"),
        )
        .with_columns(
            (pl.col("n_obs") / pl.col("span_days") * 100).alias("coverage_active_span"),
        )
        .filter(
            pl.col("first_obs").dt.date().le(date(1991, 1, 1)),
            pl.col("last_obs").dt.date().ge(date(2020, 12, 31)),
            pl.col("coverage_active_span") >= 90,
        )
        .sort("station_id")
    )

    print(lf_tntxm)
    print()
    print(lf_tntxm.explain(optimized=True))

    df_tntxm = lf_tntxm.collect(engine="streaming")

    with pl.Config(tbl_rows=500):
        print(df_tntxm)


if __name__ == "__main__":
    main()
