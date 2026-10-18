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
from climato.utils.colors import Color
from climato.utils.datetime import utc_now_iso
from climato.utils.json import pprint_dict


DATA_DIR = config.get_data_dir()
RAW_DATA_DIR = config.get_raw_data_dir()
MANIFEST_DIR = DATA_DIR / "metadata" / "manifests"
MANIFEST_PATH = MANIFEST_DIR / "daily_files.parquet"
PROCESSED_DIR = DATA_DIR / "processed"
PROCESSED_DAILY_DIR = PROCESSED_DIR / daily.MF_DAILY_RELATIVE_PATH

METADATA_COLS_DTYPES = [
    ("NUM_POSTE", pl.String),
    ("NOM_USUEL", pl.String),
    ("LAT", pl.Float64),
    ("LON", pl.Float64),
    ("ALTI", pl.Int16),
    ("AAAAMMJJ", pl.String),
]

PARAMETER_COLS_DTYPES_RTV_SOURCE = [
    ("RR", pl.Float64),
    ("TN", pl.Float64),
    ("HTN", pl.UInt16),
    ("TX", pl.Float64),
    ("HTX", pl.UInt16),
    ("TM", pl.Float64),
    ("TNTXM", pl.Float64),
    ("TAMPLI", pl.Float64),
    ("TNSOL", pl.Float64),
    ("TN50", pl.Float64),
    ("DG", pl.Int16),  # cases of negative values => UInt16 -> Int16, then replace negative values with null 
    ("FFM", pl.Float64),
    ("FF2M", pl.Float64),
    ("FXY", pl.Float64),
    ("DXY", pl.UInt16),
    ("HXY", pl.UInt16),
    ("FXI", pl.Float64),
    ("DXI", pl.UInt16),
    ("HXI", pl.UInt16),
    ("FXI2", pl.Float64),
    ("DXI2", pl.UInt16),
    ("HXI2", pl.UInt16),
    ("FXI3S", pl.Float64),
    ("DXI3S", pl.UInt16),
    ("HXI3S", pl.UInt16),
    ("DRR", pl.UInt16),
]

PARAMETER_COLS_DTYPES_RTV_TARGET = [
    (col.lower(), dtype) if col != "DG"
    else ("dg", pl.UInt16)
    for col, dtype in PARAMETER_COLS_DTYPES_RTV_SOURCE    
]

OPTIONAL_COLS_DTYPES_RTV = [
    ("STATUS_FXI3S", pl.UInt8),
    ("STATUS_DXI3S", pl.UInt8),
]


# PARAMETER_COLS_RTV: tuple[str] = tuple(
#     param
#     for param, _ in PARAMETER_COLS_DTYPES_RTV
# )

OPTIONAL_COLS_RTV = ("STATUS_DXI3S", "STATUS_FXI3S")

PARAMETER_COLS_DTYPES_AP_SOURCE = [
    ("DHUMEC", pl.UInt16),
    ("PMERM", pl.Float64),
    ("PMERMIN", pl.Float64),
    ("INST", pl.UInt16),
    ("GLOT", pl.Float64),
    ("DIFT", pl.Float64),
    ("DIRT", pl.Float64),
    ("INFRART", pl.Float64),
    ("UV", pl.Float64),
    ("UV_INDICEX", pl.Float64),
    ("SIGMA", pl.Float64),
    ("UN", pl.Float64),
    ("HUN", pl.UInt16),
    ("UX", pl.Float64),
    ("HUX", pl.UInt16),
    ("UM", pl.Float64),
    ("DHUMI40", pl.UInt16),
    ("DHUMI80", pl.UInt16),
    ("TSVM", pl.Float64),
    ("ETPMON", pl.Float64),
    ("ETPGRILLE", pl.Float64),
    ("ECOULEMENTM", pl.Float64),
    ("HNEIGEF", pl.Float64),
    ("NEIGETOTX", pl.Float64),
    ("NEIGETOT06", pl.Float64),
    ("NEIG", pl.UInt8),
    ("BROU", pl.UInt8),
    ("ORAG", pl.UInt8),
    ("GRESIL", pl.UInt8),
    ("GRELE", pl.UInt8),
    ("ROSEE", pl.UInt8),
    ("VERGLAS", pl.UInt8),
    ("SOLNEIGE", pl.UInt8),
    ("GELEE", pl.UInt8),
    ("FUMEE", pl.UInt8),
    ("BRUME", pl.UInt8),
    ("ECLAIR", pl.UInt8),
    ("NB300", pl.UInt8),
    ("BA300", pl.UInt16),
    ("TMERMIN", pl.Float64),
    ("TMERMAX", pl.Float64),
]

PARAMETER_COLS_DTYPES_AP_TARGET = [
    (col.lower(), dtype)
    for col, dtype in PARAMETER_COLS_DTYPES_AP_SOURCE    
]



def build_source_schema(
        metadata: Iterable[tuple[str, pl.DataType]],
        parameters: Iterable[tuple[str, pl.DataType]],
        optional: Iterable[tuple[str, pl.DataType]] | None,
):
    fields = list(metadata)

    for param, dtype in parameters:
        fields.append((param, dtype))
        fields.append((f"Q{param}", pl.UInt8))

    if optional:
        fields.extend(optional)

    return dict(fields)


def find_rtv_corrections(
        lf_source: pl.LazyFrame,
) -> pl.DataFrame:
    return (
        lf_source
        .filter(pl.col("DG") < 0)
        .select(
            "NUM_POSTE",
            "NOM_USUEL",
            "AAAAMMJJ",
            "DG",
        )
        .collect()
    )


def apply_rtv_corrections(
        lf_source: pl.LazyFrame,
) -> pl.LazyFrame:
    return (
        lf_source
        .with_columns(
            pl.when(pl.col("DG") < 0)
            .then(None)
            .otherwise(pl.col("DG"))
            .cast(pl.UInt16)
            .alias("DG")
        )
    )


def print_dg_corrections(filename, invalid_rows_df):
    print(f"{Color.BRIGHT_MAGENTA}--> Filename: {filename}{Color.RESET}")
    print(
        f"{Color.RED}Invalid value(s):\n{json.dumps(invalid_rows_df.rows(named=True), indent=4)}\n{Color.RESET}"
        f"""{Color.BRIGHT_RED}{invalid_rows_df.height} invalid DG value(s) """
        f"""for file {filename} (see above){Color.RESET}\n"""
        f"{Color.BRIGHT_GREEN}-> Correction: value(s) replaced by null\n{Color.RESET}"
    )


def find_no_corrections(
        lf_source: pl.LazyFrame,
) -> pl.DataFrame:
    return pl.DataFrame()


def apply_no_corrections(
        lf_source: pl.LazyFrame,
) -> pl.LazyFrame:
    return lf_source


FAMILY_SPECS = {
    "rr_t_vent": {
        "source_schema": build_source_schema(
            METADATA_COLS_DTYPES,
            PARAMETER_COLS_DTYPES_RTV_SOURCE,
            OPTIONAL_COLS_DTYPES_RTV,
        ),
        "parameters_source": PARAMETER_COLS_DTYPES_RTV_SOURCE,
        "parameters_target": PARAMETER_COLS_DTYPES_RTV_TARGET,
        "optional": OPTIONAL_COLS_DTYPES_RTV,
        "optional_cols": OPTIONAL_COLS_RTV,
        "find_corrections": find_rtv_corrections,
        "apply_corrections": apply_rtv_corrections,
    },
    "autres_parametres": {
        "source_schema": build_source_schema(
            METADATA_COLS_DTYPES,
            PARAMETER_COLS_DTYPES_AP_SOURCE,
            None,
        ),
        "parameters_source": PARAMETER_COLS_DTYPES_AP_SOURCE,
        "parameters_target": PARAMETER_COLS_DTYPES_AP_TARGET,
        "optional": (),
        "optional_cols": (),
        "find_corrections": find_no_corrections,
        "apply_corrections": apply_no_corrections,
    },
}


def build_target_schema(
        spec: dict,
):
    schema = {
        "station_id": pl.String,
        "station_name": pl.String,
        "latitude": pl.Float64,
        "longitude": pl.Float64,
        "altitude": pl.Int16,
        "obs_date": pl.Date,
    }

    for parameter, dtype in spec["parameters_target"]:
        schema[parameter.lower()] = dtype
        schema[f"q{parameter.lower()}"] = pl.UInt8

    for column, dtype in spec["optional"]:
        schema[column.lower()] = dtype

    return schema


def build_param_and_quality_columns(params):
    return [
        column
        for param, _ in params
        for column in (param, f"Q{param}")
    ]

for family in daily.PARAMETER_FAMILIES:
    FAMILY_SPECS[family]["target_schema"] = build_target_schema(FAMILY_SPECS[family])
    required = (
        [column for column, _ in METADATA_COLS_DTYPES]
         + build_param_and_quality_columns(FAMILY_SPECS[family]["parameters_source"])
    )
    FAMILY_SPECS[family]["required_cols"] = required
    FAMILY_SPECS[family]["expected_cols"] = (
        required
        + [column for column, _ in FAMILY_SPECS[family]["optional"]]
    )


def build_column_rename(params, statuses=None, include_metadata=True):
    rename = {
        "NUM_POSTE": "station_id",
        "NOM_USUEL": "station_name",
        "LAT": "latitude",
        "LON": "longitude",
        "ALTI": "altitude",
        "AAAAMMJJ": "obs_date",
    } if include_metadata else {}
    
    for param, _ in params:
        rename[param] = param.lower()
        rename[f"Q{param}"] = f"q{param.lower()}"

    if statuses is None:
        statuses = []
    for status, _ in statuses:
        rename[status] = status.lower()

    return rename


def read_csv_gz_header(
        path: Path,
) -> list[str]:
    with gzip.open(
        path,
        mode="rt",
        encoding="utf-8-sig",
        newline="",
    ) as file:
        return next(csv.reader(file, delimiter=";"))


def validate_header(
        header: list[str],
        spec: dict,
) -> None:

    actual_required = [
        col for col in header
        if col not in spec["optional_cols"]
    ]

    if actual_required != spec["required_cols"]:
        missing = [
            col for col in spec["required_cols"]
            if col not in header
        ]

        raise ValueError(
            f"Header invalid\n"
            + (f"Missing: {missing}" if missing else "")
            + f"Actual: {actual_required}\n"
            f"""Required: {spec["required_cols"]}"""
        )

    unknown = [
        col for col in header
        if col not in spec["expected_cols"]
    ]

    if unknown:
        raise ValueError(
            f"Unknown columns: {unknown}"
        )


def build_processed_path(
        processed_root: Path, 
        resource: dict,
) -> Path:
    return (
        processed_root
        / f"""parameter_family={resource["parameter_family"]}"""
        / f"""dataset_year={resource["dataset_year"]}"""
        / f"""collection={resource["collection"]}"""
        / f"""department={resource["department"]}"""
        / f"""period={resource["period"]}"""
        / "data.parquet"
    )


def scan_daily_file(
        path: Path,
        source_schema: dict[str, pl.DataType],
) -> pl.LazyFrame:
    return (
        pl.scan_csv(
            path,
            separator=";",
            schema=source_schema,
            missing_columns="insert",
            extra_columns="raise",
        )
    )

# """
# Applying corrections to invalid values that appeared during the conversion to Parquet
# """
# def apply_corrections(
#         lf_source: pl.LazyFrame,
#         parameter_family: str,
# ) -> pl.LazyFrame:
#     if parameter_family == "autres_parametres":
#         return lf_source
    
#     return (
#         lf_source
#         .with_columns(
#             pl.when(pl.col("DG") < 0)
#             .then(None)
#             .otherwise(pl.col("DG"))
#             .cast(pl.UInt16)
#             .alias("DG")
#         )
#     )


def build_daily_wide(
        lf_source: pl.LazyFrame,
        spec: dict,
        parameter_family: str,
) -> pl.LazyFrame:
    return (
        lf_source
        .with_columns(pl.col("AAAAMMJJ").str.to_date(format="%Y%m%d"))
        .rename(
            build_column_rename(spec["parameters_source"], spec["optional"]),
        )
    )


def process_resource(
        resource: dict,
        raw_root: Path,
        processed_root: Path,
) -> None:
    print(f"""Source filename: {resource["source_filename"]}""")

    source_path = raw_root / resource["raw_relative_path"]

    if not source_path.exists():
        raise FileNotFoundError(source_path)

    if source_path.stat().st_size != resource["local_size_bytes"]:
        raise ValueError(
            f"Raw size changed: {source_path}"
        )
    
    parameter_family = resource["parameter_family"]
    spec = FAMILY_SPECS[parameter_family]

    header = read_csv_gz_header(source_path)
    try:
        validate_header(header, spec)
    except ValueError as e:
        raise ValueError(f"Input file: {source_path.name}\n{e}")

    lf_source = scan_daily_file(source_path, spec["source_schema"])

    corrections = spec["find_corrections"](lf_source)
    lf_source = spec["apply_corrections"](lf_source)

    if corrections.height:
        print_dg_corrections(resource["source_filename"], corrections)

    lf_wide = build_daily_wide(lf_source, spec, parameter_family)
    
    parquet_path = build_processed_path(processed_root, resource)

    parquet_path.parent.mkdir(parents=True, exist_ok=True)

    lf_wide.sink_parquet(parquet_path, compression="zstd")

    print(f"Wrote to {parquet_path.relative_to(config.PROJECT_ROOT).as_posix()}")
    # print("OK")

    # TODO Remove test
    lf_anal = pl.scan_parquet(
        parquet_path,
    )

    actual_schema = lf_anal.collect_schema()
    target_schema = spec["target_schema"]

    if actual_schema != target_schema:
        raise ValueError(
            f"Parquet schema does not match target schema.\n"
            f"Actual schema: {actual_schema}\n"
            f"Target schema: {target_schema}\n"
        )
    
    n_rows = (
        lf_anal
        .select(
            pl.len().alias("n_rows"),
        )
        .collect()
    )


    # rows = (
    #     lf_anal
    #     .filter(
    #         pl.col("station_id") == "21527001",
    #         pl.col("obs_date").is_between(date(2015, 2, 25), date(2015, 3, 15)),
    #     )
    #     .select(
    #         "station_id",
    #         "station_name",
    #         "obs_date",
    #         "tn",
    #         "tx",
    #         "dg",
    #     )
    #     # .collect()
    # )

    print(f"{Color.GREEN}OK. {Color.YELLOW}{n_rows.item()} rows written to Parquet file{Color.RESET}")
    # if parameter_family == "rr_t_vent":
    #     if invalid_dg.height:
    #         raise InvalidSourceValueError(
    #             print_message=(
    #                 f"{Color.RED}{json.dumps(invalid_dg.rows(named=True), indent=4)}\n{Color.RESET}"
    #                 f"""{Color.BRIGHT_RED}{invalid_dg.height} invalid DG value(s) """
    #                 f"""for file {resource["source_filename"]} (see above){Color.RESET}"""
    #             ),
    #             message=(
    #                 f"""{invalid_dg.height} invalid DG value(s) """
    #                 f"""for file {resource["source_filename"]}. """
    #                 f"""Row(s) as JSON: {json.dumps(invalid_dg.rows(named=True))}"""
    #             ),
    #         )

    # with pl.Config(tbl_rows=19):
    #     print(rows)
    # print(first_rows)

    return corrections


def main():
    start = time.perf_counter()
    manifest = pl.read_parquet(MANIFEST_PATH).filter(pl.col("integrity_status") == "ok")
    failures = {}
    corrections = {}
    processed_count = 0
    corrected_count = 0

    # for resource in manifest.iter_rows(named=True):
    for i, resource in enumerate(manifest.iter_rows(named=True)):
        # if i != 180 and i != 569:
        #     continue
        
        print(f"{Color.BRIGHT_MAGENTA}\nResource {i+1}/{manifest.height} ({time.perf_counter() - start:.3f} s){Color.RESET}")
        try:
            resource_corrections = process_resource(
                resource,
                raw_root=RAW_DATA_DIR,
                processed_root=PROCESSED_DAILY_DIR,
            )
            processed_count += 1

            if resource_corrections.height:
                corrections[resource["source_filename"]] = (
                    resource_corrections
                )

        # except InvalidSourceValueError as e:
        #     print(f"{e.print_message}")
        #     corrections[resource["source_filename"]] = {
        #         "resource_order": i,
        #         "exception": e,
        #     }
        #     processed_count += 1
        #     corrected_count += 1
        except Exception as e:
            print(f"{Color.RED}{e}{Color.RESET}")
            failures[resource["source_filename"]] = {
                "resource_order": i,
                "exception": str(e),
            }

    end_message = "End of run"
    end_chars = "=" * len(end_message)

    print()
    print(f"{Color.BRIGHT_MAGENTA}{end_chars}{Color.RESET}")
    print(f"{Color.BRIGHT_MAGENTA}{end_message}{Color.RESET}")
    print(f"{Color.BRIGHT_MAGENTA}{end_chars}{Color.RESET}")
    print()

    if corrections:
        print(f"{Color.YELLOW}\nCorrections were applied:\n{Color.RESET}")
        for filename, invalid_rows_df in corrections.items():
            print_dg_corrections(filename, invalid_rows_df)
        print(f"\n{Color.YELLOW}Corrections were applied (see above).{Color.RESET}")

    if failures:
        print("\nFailures occurred:\n")
        pprint_dict(failures)
        print(f"{Color.RED}Exceptions occurred (see above).{Color.RESET}")

    print()
    print(f"{Color.BRIGHT_MAGENTA}Ended in {time.perf_counter() - start:.3f} s{Color.RESET}")
    print(f"\nProcessed: {processed_count} (of which {len(corrections)} corrected files)")
    print(f"Failures: {len(failures)}")


if __name__ == "__main__":
    main()
