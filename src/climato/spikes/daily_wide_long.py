import csv
from pathlib import Path
import sys
import os

import polars as pl

import climato.config as config
from climato.config import get_daily_data_dir


DATA_DIR = get_daily_data_dir()
RR_T_VENT_PATTERN = "Q_79_*_RR-T-Vent.csv"
AUTRES_PARAMETRES_PATTERN = "Q_79_*_autres-parametres.csv"


RR_T_VENT_CORE_PARAMS = ("RR", "TN", "TX", "TM", "TNTXM")


METADATA_COL_FDTYPES = [
    ("NUM_POSTE", pl.String),
    ("NOM_USUEL", pl.String),
    ("LAT", pl.Float64),
    ("LON", pl.Float64),
    ("ALTI", pl.Int16),
    ("AAAAMMJJ", pl.String),
]

RR_T_VENT_COL_FDTYPES = [
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
    ("DG", pl.UInt16),
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


RR_T_VENT_COL_FDTYPES_OPTIONAL = [
    ("STATUS_FXI3S", pl.UInt8),
    ("STATUS_DXI3S", pl.UInt8),
]


RR_T_VENT_ALL_PARAMS: tuple[str] = tuple(
    param
    for param, _ in RR_T_VENT_COL_FDTYPES    # des places fraîches pour ceux qui prévoient longtemps à l'avance 
)

OPTIONAL_KNOWN_COLUMNS_RR_T_VENT = ("STATUS_DXI3S", "STATUS_FXI3S")

AUTRES_PARAMETRES_COL_FDTYPES = [
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

AUTRES_PARAMETRES_ALL_PARAMS = tuple(
    param
    for param, _ in AUTRES_PARAMETRES_COL_FDTYPES
)

METADATA_COLUMNS_AFTER_SCAN = ("NUM_POSTE", "NOM_USUEL", "obs_date", "source_file")  # "source" après le scan rename AAAAMMJJ -> obs_date et ajout source_file
DAILY_PARAMS = tuple(dict.fromkeys(
    (*RR_T_VENT_ALL_PARAMS, *AUTRES_PARAMETRES_ALL_PARAMS)
))

PARAM_IDS = {
    param.lower(): param_id
    for param_id, param in enumerate(DAILY_PARAMS)
}

"""
RR, QRR, TN, QTN...
"""
def param_and_quality_columns(params):
    return [
        column
        for param in params
        for column in (param, f"Q{param}")
    ]


def build_rr_t_vent_schema() -> dict[str, pl.DataType]:
    fields = list(METADATA_COL_FDTYPES)

    for param, dtype in RR_T_VENT_COL_FDTYPES:
        fields.append((param, dtype))
        fields.append((f"Q{param}", pl.UInt8))

    fields.extend(RR_T_VENT_COL_FDTYPES_OPTIONAL)

    return dict(fields)


def build_autres_parametres_schema() -> dict[str, pl.DataType]:
    fields = list(METADATA_COL_FDTYPES)

    for param, dtype in AUTRES_PARAMETRES_COL_FDTYPES:
        fields.append((param, dtype))
        fields.append((f"Q{param}", pl.UInt8))

    return dict(fields)


def build_column_rename(params, statuses=None, include_metadata=True):
    rename = {
        "NUM_POSTE": "station_id",
        "NOM_USUEL": "station_name",
    } if include_metadata else {}
    
    for param in params:
        rename[param] = param.lower()
        rename[f"Q{param}"] = f"q{param.lower()}"

    if statuses is None:
        statuses = []
    for status in statuses:
        rename[status] = status.lower()

    return rename


RR_T_VENT_SCHEMA = build_rr_t_vent_schema()

EXPECTED_COLUMNS_RR_T_VENT = set(RR_T_VENT_SCHEMA)
REQUIRED_COLUMNS_RR_T_VENT = EXPECTED_COLUMNS_RR_T_VENT - set(OPTIONAL_KNOWN_COLUMNS_RR_T_VENT)

PARAM_AND_QUALITY_COLUMNS_RR_T_VENT_CORE = param_and_quality_columns(RR_T_VENT_CORE_PARAMS)
PARAM_AND_QUALITY_COLUMNS_RR_T_VENT_ALL = param_and_quality_columns(RR_T_VENT_ALL_PARAMS)
PARAM_AND_QUALITY_COLUMNS_AUTRES_PARAMETRES = param_and_quality_columns(AUTRES_PARAMETRES_ALL_PARAMS)

AUTRES_PARAMETRES_SCHEMA = build_autres_parametres_schema()

EXPECTED_COLUMNS_AUTRES_PARAMETRES = set(AUTRES_PARAMETRES_SCHEMA)
REQUIRED_COLUMNS_AUTRES_PARAMETRES = EXPECTED_COLUMNS_AUTRES_PARAMETRES


RENAME_COLUMNS_RR_T_VENT_CORE = build_column_rename(RR_T_VENT_CORE_PARAMS)
RENAME_COLUMNS_RR_T_VENT = build_column_rename(RR_T_VENT_ALL_PARAMS, OPTIONAL_KNOWN_COLUMNS_RR_T_VENT)
RENAME_COLUMNS_AUTRES_PARAMETRES = build_column_rename(AUTRES_PARAMETRES_ALL_PARAMS)

RR_T_VENT_ALL_PARAMS_LOWER = tuple(param.lower() for param in RR_T_VENT_ALL_PARAMS)
AUTRES_PARAMETRES_ALL_PARAMS_LOWER = tuple(param.lower() for param in AUTRES_PARAMETRES_ALL_PARAMS)


def read_header(path: Path) -> set[str]:
    with path.open(encoding="utf-8", newline="") as file:
        reader = csv.reader(file, delimiter=";")
        return set(next(reader))


def validate_headers(paths: list[Path], required: set[str], expected: set[str]) -> None:
    for path in paths:
        actual = read_header(path)

        missing_required = required - actual
        unknown = actual - expected

        if missing_required:
            raise ValueError(
                f"Input file: {path.name}\n"
                f"Missing required columns: {sorted(missing_required)}"
            )

        if unknown:
            raise ValueError(
                f"Input file: {path.name}\n"
                f"Unknown columns: {sorted(unknown)}"
            )


def scan_daily_rr_t_vent() -> pl.LazyFrame:
    paths = list(DATA_DIR.glob(RR_T_VENT_PATTERN))

    if not paths:
        raise FileNotFoundError(
            f"No RR-T-Vent source files found in {DATA_DIR.resolve()} with pattern {RR_T_VENT_PATTERN}"
        )
    
    validate_headers(paths, REQUIRED_COLUMNS_RR_T_VENT, EXPECTED_COLUMNS_RR_T_VENT)

    return (
        pl.scan_csv(
            str(DATA_DIR / RR_T_VENT_PATTERN),
            separator=";",
            schema=RR_T_VENT_SCHEMA,
            include_file_paths="source_file",
            missing_columns="insert",
        )
        .with_columns(
            pl.col("AAAAMMJJ").str.to_date(format="%Y%m%d").alias("obs_date"),
            pl.col("source_file").str.extract(r"([^/\\]+)$", 1).alias("source_file")
        )
    )


def scan_daily_autres_parametres() -> pl.LazyFrame:
    validate_headers(DATA_DIR.glob(AUTRES_PARAMETRES_PATTERN), REQUIRED_COLUMNS_AUTRES_PARAMETRES, EXPECTED_COLUMNS_AUTRES_PARAMETRES)

    return (
        pl.scan_csv(
            str(DATA_DIR / AUTRES_PARAMETRES_PATTERN),
            separator=";",
            schema=AUTRES_PARAMETRES_SCHEMA,
            include_file_paths="source_file",
            missing_columns="insert",
        )
        .with_columns(
            pl.col("AAAAMMJJ").str.to_date(format="%Y%m%d").alias("obs_date"),
            pl.col("source_file").str.extract(r"([^/\\]+)$", 1).alias("source_file")
        )
    )


def build_lf_rtv_wide_core(
        lf: pl.LazyFrame,
) -> pl.LazyFrame:
    return (
        lf
        .select(
            *METADATA_COLUMNS_AFTER_SCAN,
            *PARAM_AND_QUALITY_COLUMNS_RR_T_VENT_CORE,
        )
        .rename(RENAME_COLUMNS_RR_T_VENT_CORE)
    )


def build_lf_rtv_wide_all(
        lf: pl.LazyFrame
) -> pl.LazyFrame:
    return (
        lf
        .select(
            *METADATA_COLUMNS_AFTER_SCAN,
            *PARAM_AND_QUALITY_COLUMNS_RR_T_VENT_ALL,
            *OPTIONAL_KNOWN_COLUMNS_RR_T_VENT,
        )
        .rename(RENAME_COLUMNS_RR_T_VENT)
    )


def build_lf_ap_wide(
        lf: pl.LazyFrame
) -> pl.LazyFrame:
    return (
        lf
        .select(
            *METADATA_COLUMNS_AFTER_SCAN,
            *PARAM_AND_QUALITY_COLUMNS_AUTRES_PARAMETRES,
        )
        .rename(RENAME_COLUMNS_AUTRES_PARAMETRES)
    )


def custom_describe(
        lf: pl.LazyFrame
) -> pl.DataFrame:
    n_rows = lf.select(pl.len()).collect().item()
    describe = lf.describe()
    describe_tr = (
        describe
        .transpose(include_header=True, column_names=describe.select("statistic").to_series(), header_name="column")
        .remove(column="statistic")
        .with_columns(
            count=pl.col("count").cast(pl.Float64).cast(pl.UInt32),
            null_count=pl.col("null_count").cast(pl.Float64).cast(pl.UInt32),
        )
        .with_columns(
            count_pct=(pl.col("count") / n_rows * 100).round(2),
            null_count_pct=(pl.col("null_count") / n_rows * 100).round(2),
        )
        .select("column", "count", "null_count", "count_pct", "null_count_pct")
    )

    return describe_tr


def add_measure_count_lf(
        lf: pl.LazyFrame,
        params: tuple[str],
        column_name: str,
) -> pl.LazyFrame:
    return lf.with_columns(
        pl.sum_horizontal(
            [
                pl.col(param.lower())
                .is_not_null()
                for param in params
            ]
        ).alias(column_name)
    )


def add_measure_count(
        df: pl.DataFrame,
        params: tuple[str],
        column_name: str,
) -> pl.DataFrame:
    return df.with_columns(
        pl.sum_horizontal(
            [
                pl.col(param.lower())
                .is_not_null()
                # .cast(pl.UInt8)
                for param in params
            ]
        ).alias(column_name)
    )



FIELDS_TO_AUDIT = (
    "hneigef",
    "neigetotx",
    "neigetot06",
    "uv_indicex",
    "sigma",
    "un",
    "ux",
    "um",
)


def audit_numeric_types_lf(
    lf: pl.LazyFrame,
    columns: tuple[str, ...],
) -> pl.DataFrame:
    expressions = []
    for col in columns:
        c = pl.col(col)
        expressions.extend([
            c.min().alias(f"{col}__min"),
            c.max().alias(f"{col}__max"),
            c.drop_nulls().n_unique().alias(f"{col}__n_unique"),
            (
                c.is_not_null()
                & (c.floor() != c)
            ).sum().alias(f"{col}__fractional_count"),
        ])

    summary = lf.select(expressions).collect()
    values = summary.row(0, named=True)    

    return pl.DataFrame({
        "column": list(columns),
        "min": [
            values[f"{col}__min"]
            for col in columns
        ],
        "max": [
            values[f"{col}__max"]
            for col in columns
        ],
        "n_unique": [
            values[f"{col}__n_unique"]
            for col in columns
        ],
        "fractional_count": [
            values[f"{col}__fractional_count"]
            for col in columns
        ],
    })


def audit_numeric_types(
    df: pl.DataFrame,
    columns: tuple[str, ...],
) -> pl.DataFrame:
    return pl.DataFrame({
        "column": list(columns),
        "min": [
            df[col].min()
            for col in columns
        ],
        "max": [
            df[col].max()
            for col in columns
        ],
        "n_unique": [
            df[col].n_unique()
            for col in columns
        ],
        "fractional_count": [
            df.select(
                (
                    pl.col(col).is_not_null()
                    & (pl.col(col) != pl.col(col).floor())
                ).sum()
            ).item()
            for col in columns
        ],
    })


def quality_pair_audit_lf(
    lf: pl.LazyFrame,
    params: tuple[str, ...],
) -> pl.DataFrame:
    expressions = []

    for param in params:
        value = pl.col(param.lower())
        quality = pl.col(f"q{param.lower()}")

        expressions.extend([
            (
                value.is_not_null()
                & quality.is_null()
            )
            .sum()
            .alias(f"{param}_value_without_quality"),

            (
                value.is_null()
                & quality.is_not_null()
            )
            .sum()
            .alias(f"{param}_quality_without_value"),
        ])

    return (
        lf
        .select(expressions)
        .collect()
        .transpose(include_header=True, header_name="line_type", column_names=["count"])
    )


def quality_pair_audit_lf_2(
    lf: pl.LazyFrame,
    params: tuple[str, ...],
) -> pl.DataFrame:
    def aux(metadata: list, exprs: list[pl.Expr], not_null_col: pl.Expr, null_col: pl.Expr, not_null_str: str, null_str: str, param):
        metric_id = f"metric_{len(metadata)}"
        exprs.append(
            (
                not_null_col.is_not_null()
                & null_col.is_null()
            )
            .sum()
            .alias(metric_id)
        )
        metadata.append({
            "metric_id": metric_id,
            "pair_type": f"{not_null_str}_without_{null_str}",
            "param": param,
        })

        return metadata, exprs


    audit_expressions = []
    audit_metadata = []

    for param in params:
        value = pl.col(param.lower())
        quality = pl.col(f"q{param.lower()}")

        not_null_col = value
        null_col = quality
        not_null_str = "value"
        null_str = "quality"

        audit_metadata, audit_expressions = aux(audit_metadata, audit_expressions, not_null_col, null_col, not_null_str, null_str, param)
        not_null_col, null_col = null_col, not_null_col
        not_null_str, null_str = null_str, not_null_str
        audit_metadata, audit_expressions = aux(audit_metadata, audit_expressions, not_null_col, null_col, not_null_str, null_str, param)
        

        # for not_null, null in ((value, quality), (quality, value)):
        #     audit_metadata, audit_expressions = aux(audit_metadata, audit_expressions, not_null, null, param)

        # audit_metadata, expressions = aux(audit_metadata, expressions, "value", "quality", param)
        # audit_metadata, expressions = aux(audit_metadata, expressions, "quality", "value", param)

        # metric_id = f"metric_{len(audit_metadata)}"
        # expressions.append(
        #     (
        #         value.is_not_null()
        #         & quality.is_null()
        #     )
        #     .sum()
        #     .alias(metric_id)
        # )

        # audit_metadata.append({
        #     "metric_id": metric_id,
        #     "param": param,
        #     "pair_type": "value_without_quality",
        # })
        # metric_id = f"metric_{len(audit_metadata)}"
        # expressions.append(
        #     (
        #         value.is_null()
        #         & quality.is_not_null()
        #     )
        #     .sum()
        #     .alias(metric_id)
        # )

        # audit_metadata.append({
        #     "metric_id": metric_id,
        #     "param": param,
        #     "pair_type": "value_without_quality",
        # })

    return audit_metadata, audit_expressions


def quality_pair_audit(
    df: pl.DataFrame,
    params: tuple[str, ...],
) -> pl.DataFrame:
    expressions = []

    for param in params:
        value = pl.col(param.lower())
        quality = pl.col(f"q{param.lower()}")

        expressions.extend([
            (
                value.is_not_null()
                & quality.is_null()
            )
            .sum()
            .alias(f"{param}_value_without_quality"),

            (
                value.is_null()
                & quality.is_not_null()
            )
            .sum()
            .alias(f"{param}_quality_without_value"),
        ])

    return df.select(expressions)


def measure_signature_expr(
    params: tuple[str, ...],
) -> pl.Expr:
    return pl.concat_str(
        [
            pl.when(
                pl.col(param.lower()).is_not_null()
            )
            .then(pl.lit(param))
            .otherwise(pl.lit(None, dtype=pl.String))
            for param in params
        ],
        separator=",",
        ignore_nulls=True,
    )


def drill_down_orphan_quality_pairs(lf: pl.LazyFrame, param: str, quality_code_value: int):
    value_col = param.lower()
    quality_col = f"q{value_col}"

    return (
        lf
        .filter(
            pl.col(value_col).is_null()
            & (pl.col(quality_col) == quality_code_value)
        )
        .select(
            "station_id",
            "station_name",
            "obs_date"
        )
        .group_by(
            "station_id",
            "station_name",
        )
        .agg(
            count=pl.len(),
            min_date=pl.col("obs_date").min(),
            max_date=pl.col("obs_date").max(),
        )
        .sort("station_id")
        .collect()
    )


def replace_param_code_with_param_id(df: pl.DataFrame):
    return (
        df
        .with_columns(
            param_id=(
                pl.col("param_code")
                .replace_strict(
                    PARAM_IDS,
                    return_dtype=pl.UInt16,
                )
            ),
        )
        .drop("param_code")
    )


def get_dump_dir() -> Path:
    configured_path = os.getenv("CLIMATO_DUMP_DIR")

    if configured_path:
        return Path(configured_path).expanduser().resolve()

    return config.PROJECT_ROOT / "dump"


DUMP_DIR = get_dump_dir()



def main():
    lf_rtv_source = scan_daily_rr_t_vent()
    lf_rtv_core = build_lf_rtv_wide_core(lf_rtv_source)
    lf_rtv_all = build_lf_rtv_wide_all(lf_rtv_source)

    lf_autres_source = scan_daily_autres_parametres()
    lf_autres_all = build_lf_ap_wide(lf_autres_source)

    df_rtv_core = lf_rtv_core.collect()
    df_rtv_all = lf_rtv_all.collect()
    df_autres_all = lf_autres_all.collect()

    print(df_rtv_all)
    sys.exit(1)

    print(df_rtv_all.group_by("status_fxi3s", "source_file").agg(
        n_rows=pl.len(),
        pct=pl.len() / df_rtv_all.height * 100,
    ))

    # for col in df_rtv_all.columns:
    #     col_count_str = f"{col}_count"
    #     col_ncount_str = f"{col}_null_count"
    #     df_rtv_all.with_columns(pl.col(col).is_not_null().alias(col_count_str)).select(pl.col(col_count_str).sum()).item()
    #     # df_rtv_all.group_by(col).agg(
    #     #     null_count=
    #     # )

    describe_rtv = df_rtv_all.describe()
    print(describe_rtv.columns)
    describe_rtv_tr = (
        describe_rtv
        .transpose(include_header=True, column_names=describe_rtv.select("statistic").to_series(), header_name="column")
        .remove(column="statistic")
    )
    print(describe_rtv)
    # print(describe_rtv_tr)
    
    describe_rtv_tr = describe_rtv_tr.with_columns(
        count_pct=pl.col("count").cast(pl.Float64) / df_rtv_all.height * 100,
        null_count_pct=pl.col("null_count").cast(pl.Float64) / df_rtv_all.height * 100,
    )
    with pl.Config(tbl_cols=20, tbl_rows=-1):
        print(describe_rtv_tr)


    describe_ap = df_autres_all.describe()
    print(describe_ap.columns)
    describe_ap_tr = (
        describe_ap
        .transpose(include_header=True, column_names=describe_ap.select("statistic").to_series(), header_name="column")
        .remove(column="statistic")
    )
    print(describe_ap)
    # print(describe_ap_tr)
    
    describe_ap_tr = describe_ap_tr.with_columns(
        count_pct=pl.col("count").cast(pl.Float64) / df_autres_all.height * 100,
        null_count_pct=pl.col("null_count").cast(pl.Float64) / df_autres_all.height * 100,
    )
    with pl.Config(tbl_cols=20, tbl_rows=-1):
        print(describe_ap_tr)
    

    # with pl.Config(tbl_cols=20, tbl_rows=-1, tbl_width_chars=-1, fmt_str_lengths=200):
    # with pl.Config(tbl_cols=20, tbl_rows=-1):
    #     print(describe.transpose(header_name="statistic").with_columns(
    #         count_pct=pl.col("co")
    #     ))

    print("*********************************************")
    print("**************** df_rtv_core ****************")
    print("*********************************************")
    # with pl.Config(tbl_cols=20, tbl_width_chars=-1, fmt_str_lengths=200):
    #     print(lf_autres_all)


    df_rtv_core = add_measure_count(df_rtv_core, RR_T_VENT_CORE_PARAMS, "core_measure_count")
    expected_long_core_rows = (
        df_rtv_core
        .select(pl.col("core_measure_count").sum())
        .item()
    )
    mean_measures_per_wide_row = (
        expected_long_core_rows / df_rtv_core.height
    )
    measure_density = (
        expected_long_core_rows
        / (df_rtv_core.height * len(RR_T_VENT_CORE_PARAMS))
    )

    with pl.Config(tbl_cols=20, tbl_rows=100):
        print(f"height: {df_rtv_core.height}")
        print(f"expected_long_core_rows: {expected_long_core_rows}")
        print(f"mean_measures_per_wide_row: {mean_measures_per_wide_row}")
        print(f"measure_density: {measure_density}")
        print(
            df_rtv_core
            .group_by("core_measure_count")
            .agg(
                count=pl.len(),
                pct=pl.len() / df_rtv_core.height * 100
            )
            .sort("core_measure_count")
        )

        df_rtv_core = df_rtv_core.with_columns(
            measure_signature_expr(RR_T_VENT_CORE_PARAMS)
            .alias("measure_signature")
        )

        df_rtv_core_niort = df_rtv_core.filter(pl.col("station_id") == "79191005")

        # TODO ... TODO

        patterns_core = (
            df_rtv_core
            .group_by(
                "core_measure_count",
                "measure_signature",
            )
            .agg(
                count=pl.len(),
            )
            .with_columns(
                pct=pl.col("count") / df_rtv_core.height * 100
            )
            .sort("count", descending=True)
        )
        
        patterns_core_niort = (
            df_rtv_core_niort
            .group_by(
                "core_measure_count",
                "measure_signature",
            )
            .agg(
                count=pl.len(),
            )
            .with_columns(
                pct_all=pl.col("count") / df_rtv_core.height * 100,
                pct_niort=pl.col("count") / df_rtv_core_niort.height * 100
            )
            .sort("count", descending=True)
        )
        
    with pl.Config(tbl_cols=20, tbl_rows=100, fmt_str_lengths=300):   
        print(patterns_core.head(30))
        print(patterns_core_niort.head(30))

        core_quality_audit = quality_pair_audit(df_rtv_core, RR_T_VENT_CORE_PARAMS).transpose(include_header=True)
        print(core_quality_audit)

    print("********************************************")
    print("**************** df_rtv_all ****************")
    print("********************************************")

    df_quality = 1

    df_rtv_all = add_measure_count(df_rtv_all, RR_T_VENT_ALL_PARAMS, "all_measure_count")

    # df_long = (
    #     df_rtv_all
    #     .unpivot(
    #         on=QUALITY_COLUMNS,
    #         index=AUTRES_PARAMETRES_COL_FDTYPES,
    #         variable_name="quality_param_code",
    #         value_name="quality_param_code",
    #     )
    # )

    expected_long_rtv_all_rows = (
        df_rtv_all
        .select(pl.col("all_measure_count").sum())
        .item()
    )
    mean_measures_rtv_all_per_wide_row = (
        expected_long_rtv_all_rows / df_rtv_all.height
    )
    measure_density_rtv_all = (
        expected_long_rtv_all_rows
        / (df_rtv_all.height * len(RR_T_VENT_COL_FDTYPES))
    )

    print(
        f"expected_long_rtv_all_rows = "
        f"mean_measures_rtv_all_per_wide_row = "
        f"measure_density_rtv_all = "
    )
    
    with pl.Config(tbl_cols=20, tbl_rows=100):
        print(f"height: {df_rtv_all.height}")
        print(f"expected_long_all_rows: {expected_long_rtv_all_rows}")
        print(f"mean_measures_all_per_wide_row: {mean_measures_rtv_all_per_wide_row}")
        print(f"measure_density_all: {measure_density_rtv_all}")
        sum_measure_count = df_rtv_all.select("all_measure_count").sum().item()
        print(sum_measure_count)
        print(sum_measure_count / df_rtv_all.height)
        print(
            df_rtv_all
            .group_by("all_measure_count")
            .agg(
                count=pl.len(),
                pct=pl.len() / df_rtv_all.height * 100
            )
            .sort("all_measure_count")
        )
        print(
            df_rtv_all
            .group_by("all_measure_count")
            .agg(
                count=pl.len(),
                pct=pl.len() / df_rtv_all.height * 100
            )
            .sort("pct", descending=True)
        )

    df_rtv_all = df_rtv_all.with_columns(
        measure_signature_expr(RR_T_VENT_ALL_PARAMS)
        .alias("measure_signature")
    )
    df_rtv_all_niort = df_rtv_all.filter(pl.col("station_id") == "79191005")
    df_rtv_all_sig_9 = (
        df_rtv_all
        .filter(pl.col("measure_signature") == "RR,TN,HTN,TX,HTX,TM,TNTXM,TAMPLI,DG")
        .select(["station_id", "station_name", "obs_date", "measure_signature"])
    )

    patterns_rtv = (
        df_rtv_all
        .group_by(
            "all_measure_count",
            "measure_signature",
        )
        .agg(
            count=pl.len(),
        )
        .with_columns(
            pct=pl.col("count") / df_rtv_all.height * 100
        )
        .sort("count", descending=True)
    )

    patterns_rtv_niort = (
        df_rtv_all_niort
        .group_by(
            "all_measure_count",
            "measure_signature",
        )
        .agg(
            count=pl.len(),
        )
        .with_columns(
            pct_all=pl.col("count") / df_rtv_all.height * 100,
            pct_niort=pl.col("count") / df_rtv_all_niort.height * 100
        )
        .sort("count", descending=True)
    )

    with pl.Config(tbl_cols=20, tbl_rows=100, fmt_str_lengths=300):   
        print(patterns_rtv.head(30))
        print(patterns_rtv_niort.head(30))
        print(df_rtv_all_sig_9)
        print(df_rtv_all_sig_9.group_by(["station_id", "station_name"]).agg(
            pl.len().alias("count"),
        ))
        # rtv_all_quality_audit = quality_pair_audit(df_rtv_all, RR_T_VENT_COL_FDTYPES).transpose(include_header=True)
        rtv_all_quality_audit = quality_pair_audit(df_rtv_all, RR_T_VENT_ALL_PARAMS).transpose(include_header=True)
        print(rtv_all_quality_audit)

        # for param in RR_T_VENT_COL_FDTYPES:
        for param in RR_T_VENT_ALL_PARAMS:
            value_col = param.lower()
            quality_col = f"q{value_col}"

            audit_orph_q_rtv = (
                df_rtv_all
                .filter(
                    pl.col(value_col).is_null()
                    & pl.col(quality_col).is_not_null()
                )
                .group_by(quality_col)
                .len()
                .sort(quality_col)
            )

            if audit_orph_q_rtv.height > 0:
                pass
                # print(param)
                # print(audit_orph_q_rtv)

    # sys.exit()

    # with pl.Config(tbl_cols=20):
    #     print((
    #         df_rtv_core
    #         .filter(pl.col("tn").is_not_null())
    #     ))

    # print(df_rtv_core["core_measure_count"].mean())


    # with pl.Config(tbl_cols=20):
    #     print(df_rtv_core.null_count())

    # with pl.Config(tbl_cols=20, tbl_rows=200):
    #     print((
    #         df_rtv_core
    #         .group_by("station_id")
    #         .agg(
    #             station_name=pl.col("station_name").first(),
    #             n_rows=pl.len(),
    #             tn_null_count=pl.col("tn").null_count(),
    #             rr_null_count=pl.col("rr").null_count(),
    #         )
    #         .with_columns(                
    #             tn_nonnull_rate=pl.lit(1) - pl.col("tn_null_count") / pl.col("n_rows"),
    #             rr_nonnull_rate=pl.lit(1) - pl.col("rr_null_count") / pl.col("n_rows"),
    #         )
    #         .sort(by="station_id")
    #     ))

    # with pl.Config(tbl_cols=20, tbl_rows=100):
    #     print((
    #         df_rtv_core
    #         .group_by("source_file")
    #         .agg(
    #             n_rows=pl.len(),
    #             min_date=pl.col("obs_date").min(),
    #             max_date=pl.col("obs_date").max(),
    #             tn_null_count=pl.col("tn").null_count(),
    #             rr_null_count=pl.col("rr").null_count(),
    #         )
    #         .with_columns(                
    #             tn_nonnull_rate=pl.lit(1) - pl.col("tn_null_count") / pl.col("n_rows"),
    #             rr_nonnull_rate=pl.lit(1) - pl.col("rr_null_count") / pl.col("n_rows"),
    #         )
    #     ))

    print("***********************************************")
    print("**************** df_autres_all ****************")
    print("***********************************************")

    df_autres_all = add_measure_count(df_autres_all, AUTRES_PARAMETRES_ALL_PARAMS, "all_measure_count")

    expected_long_autres_all_rows = (
        df_autres_all
        .select(pl.col("all_measure_count").sum())
        .item()
    )
    mean_measures_autres_all_per_wide_row = (
        expected_long_autres_all_rows / df_autres_all.height
    )
    measure_density_autres_all = (
        expected_long_autres_all_rows
        / (df_autres_all.height * len(AUTRES_PARAMETRES_ALL_PARAMS))
    )
    
    with pl.Config(tbl_cols=20, tbl_rows=100):
        print(f"height: {df_autres_all.height}")
        print(f"expected_long_all_rows: {expected_long_autres_all_rows}")
        print(f"mean_measures_all_per_wide_row: {mean_measures_autres_all_per_wide_row}")
        print(f"measure_density_all: {measure_density_autres_all}")
        print(
            df_autres_all
            .group_by("all_measure_count")
            .agg(
                count=pl.len(),
                pct=pl.len() / df_autres_all.height * 100
            )
            .sort("all_measure_count")
        )
        print(
            df_autres_all
            .group_by("all_measure_count")
            .agg(
                count=pl.len(),
                pct=pl.len() / df_autres_all.height * 100
            )
            .sort("pct", descending=True)
        )

    df_autres_all = df_autres_all.with_columns(
        measure_signature_expr(AUTRES_PARAMETRES_ALL_PARAMS)
        .alias("measure_signature")
    )
    df_autres_all_niort = df_autres_all.filter(pl.col("station_id") == "79191005")

    patterns_autres = (
        df_autres_all
        .group_by(
            "all_measure_count",
            "measure_signature",
        )
        .agg(
            count=pl.len(),
        )
        .with_columns(
            pct=pl.col("count") / df_autres_all.height * 100
        )
        .sort("count", descending=True)
    )

    patterns_autres_niort = (
        df_autres_all_niort
        .group_by(
            "all_measure_count",
            "measure_signature",
        )
        .agg(
            count=pl.len(),
        )
        .with_columns(
            pct_all=pl.col("count") / df_autres_all.height * 100,
            pct_niort=pl.col("count") / df_autres_all_niort.height * 100
        )
        .sort("count", descending=True)
    )

    with pl.Config(tbl_cols=20, tbl_rows=100, fmt_str_lengths=300):   
        print(patterns_autres.head(80))
        print(patterns_autres_niort.head(80))
        autres_all_quality_audit = quality_pair_audit(df_autres_all, AUTRES_PARAMETRES_ALL_PARAMS).transpose(include_header=True)
        print(autres_all_quality_audit)

        for param in AUTRES_PARAMETRES_ALL_PARAMS:
            value_col = param.lower()
            quality_col = f"q{value_col}"

            audit_orph_q_autres = (
                df_autres_all
                .filter(
                    pl.col(value_col).is_null()
                    & pl.col(quality_col).is_not_null()
                )
                .group_by(quality_col)
                .len()
                .sort(quality_col)
            )

            if audit_orph_q_autres.height > 0:
                pass
                # print(param)
                # print(audit_orph_q_autres)

        print()
        print()
        print()
        print("*** Audit des lignes sans mesures + audit types incertains autres + drill-down ETPMON/NEIGETOTX ***")
        print("*** Audit des lignes sans mesures + audit types incertains autres + drill-down ETPMON/NEIGETOTX ***")
        print()
        print()
        print()

        print()
        print("Audit des lignes sans mesures")
        print()
        zero_measure_rows_rtv = df_rtv_all.filter(pl.col("all_measure_count") == 0)
        zero_measure_rows_autres = df_autres_all.filter(pl.col("all_measure_count") == 0)

        print("Lignes sans mesures RR-T-Vent")
        print(zero_measure_rows_rtv.select(["station_id", "station_name", "obs_date"]))
        print(
            zero_measure_rows_rtv
            .group_by("station_id", "station_name")
            .agg(
                count=pl.len(),
                min_date=pl.col("obs_date").min(),
                max_date=pl.col("obs_date").max(),
            )
            .sort("count", descending=True)
        )
        print("Lignes sans mesures autres-parametres")
        print(zero_measure_rows_autres.select(["station_id", "station_name", "obs_date"]))
        print(
            zero_measure_rows_autres
            .group_by("station_id", "station_name")
            .agg(
                count=pl.len(),
                min_date=pl.col("obs_date").min(),
                max_date=pl.col("obs_date").max(),
            )
            .sort("count", descending=True)
        )

        print()
        print("audit_numeric_types")
        print()

        print(audit_numeric_types(df_autres_all, FIELDS_TO_AUDIT))

        print()
        print("drill-down ETPMON/NEIGETOTX")
        print()

        

        for param in ("ETPMON", "NEIGETOTX"):
            value_col = param.lower()
            quality_col = f"q{value_col}"

            print(f"drill-down {param}")
            drill_down_etp_neigetotx = (
                df_autres_all
                .filter(
                    pl.col(value_col).is_null()
                    & (pl.col(quality_col) == 1)
                )
            )

            print(drill_down_etp_neigetotx.select(["station_id", "station_name", "obs_date"]))

            print(
                drill_down_etp_neigetotx
                .group_by(["station_id", "station_name"])
                .agg(
                    n_rows=pl.len(),
                    min_date=pl.col("obs_date").min(),
                    max_date=pl.col("obs_date").max(),
                )
            )

        print("""print(lf_rtv_all.group_by("source_file", "station_id", "obs_date").len())""")
        print(
            lf_rtv_all
            .group_by("source_file", "station_id", "obs_date")
            .len()
        )
        print(lf_rtv_all.group_by(["source_file", "station_id", "obs_date"]).len())
        # print(lf_rtv_all.group_by("source_file", "station_id", "obs_date").len().filter(pl.col("len")))

        # # lf_long = lf_autres_long.filter(
        # lf_long = lf_rtv_all.filter(
        #     pl.col("quality_code").is_null()
        # )

        # print(lf_long)

        # lf_rtv_all.group_by("source_file", "station_id", "obs_date").len().filter(pl.col("len"))

        value_columns_rtv = [
            param.lower()
            for param in RR_T_VENT_ALL_PARAMS
        ]

        quality_columns_rtv = [
            f"q{param.lower()}"
            for param in RR_T_VENT_ALL_PARAMS
        ]

        df_long_rtv_all_values = (
            df_rtv_all
            .unpivot(
                on=value_columns_rtv,
                index=["station_id", "obs_date", "source_file"],
                variable_name="param_code",
                value_name="value",
            )
            .filter(pl.col("value").is_not_null())
        )

        print(df_long_rtv_all_values.height)
        print(df_long_rtv_all_values)

        df_long_rtv_all_quality = (
            df_rtv_all
            .unpivot(
                on=quality_columns_rtv,
                index=["station_id", "obs_date", "source_file"],
                variable_name="quality_param_code",
                value_name="quality_code",
            )
            .filter(pl.col("quality_code").is_not_null())
            .with_columns(
                pl.col("quality_param_code")
                .str.slice(1)
                .alias("param_code")
            )
            .drop("quality_param_code")
        )

        print(df_long_rtv_all_quality.height)
        print(df_long_rtv_all_quality.shape)

        join_keys = ["source_file", "station_id", "obs_date", "param_code"]

        df_long_rtv_all = (
            df_long_rtv_all_values
            .join(
                df_long_rtv_all_quality,
                on=join_keys,
                how="left",
                validate="1:1",
            )
        )

        df_rtv_status = (
            df_rtv_all
            .select(
                "station_id",
                "obs_date",
                "status_fxi3s",
                "status_dxi3s",
                "source_file",
            )
        )

        df_long_rtv_all = (
            df_long_rtv_all
            .join(
                df_rtv_status,
                on=["source_file", "station_id", "obs_date"],
                how="left",
                validate="m:1",
            )
            .with_columns(
                pl.when(pl.col("param_code") == "fxi3s")
                .then(pl.col("status_fxi3s"))
                .when(pl.col("param_code") == "dxi3s")
                .then(pl.col("status_dxi3s"))
                .otherwise(None)
                .cast(pl.UInt8)
                .alias("status_code")
            )
            .drop(
                "status_fxi3s",
                "status_dxi3s",
            )
        )

        print("""df_long_rtv_all.filter((pl.col("status_code").is_not_null()) & (pl.col("value").is_null()))""")
        print(df_long_rtv_all.filter((pl.col("status_code").is_not_null()) & (pl.col("value").is_null())))
        print("""df_long_rtv_all.filter((pl.col("status_code").is_null()) & (pl.col("value").is_not_null()))""")
        print(df_long_rtv_all.filter((pl.col("status_code").is_null()) & (pl.col("value").is_not_null())))
        print("""df_long_rtv_all.filter((pl.col("status_code").is_not_null()) & ~((pl.col("param_code") == "fxi3s") | (pl.col("param_code") == "dxi3s")))""")
        print(df_long_rtv_all.filter((pl.col("status_code").is_not_null()) & ~((pl.col("param_code") == "fxi3s") | (pl.col("param_code") == "dxi3s"))))
        print("""df_long_rtv_all.filter((pl.col("status_code").is_not_null()))""")
        print(df_long_rtv_all.filter((pl.col("status_code").is_not_null())))


        print("df_long_rtv_all")
        print(df_long_rtv_all)

        print("""df_rtv_all.estimated_size("mb")""")
        print(df_rtv_all.estimated_size("mb"))
        print("""df_long_rtv_all.estimated_size("mb")""")
        print(df_long_rtv_all.estimated_size("mb"))


        value_columns_ap = [
            param.lower()
            for param in AUTRES_PARAMETRES_ALL_PARAMS
        ]

        quality_columns_ap = [
            f"q{param.lower()}"
            for param in AUTRES_PARAMETRES_ALL_PARAMS
        ]

        df_long_ap_all_values = (
            df_autres_all
            .unpivot(
                on=value_columns_ap,
                index=["station_id", "obs_date", "source_file"],
                variable_name="param_code",
                value_name="value",
            )
            .filter(pl.col("value").is_not_null())
        )

        print(df_long_ap_all_values.height)
        print(df_long_ap_all_values)

        df_long_ap_all_quality = (
            df_autres_all
            .unpivot(
                on=quality_columns_ap,
                index=["station_id", "obs_date", "source_file"],
                variable_name="quality_param_code",
                value_name="quality_code",
            )
            .filter(pl.col("quality_code").is_not_null())
            .with_columns(
                pl.col("quality_param_code")
                .str.slice(1)
                .alias("param_code")
            )
            .drop("quality_param_code")
        )

        print(df_long_ap_all_quality.height)
        print(df_long_ap_all_quality.shape)

        join_keys = ["source_file", "station_id", "obs_date", "param_code"]

        df_long_ap_all = (
            df_long_ap_all_values
            .join(
                df_long_ap_all_quality,
                on=join_keys,
                how="left",
                validate="1:1",
            )
            .with_columns(
                status_code=pl.lit(None, dtype=pl.UInt8),
            )
        )

        print("df_long_ap_all")
        print(df_long_ap_all)

        print("""df_autres_all.estimated_size("mb")""")
        print(df_autres_all.estimated_size("mb"))
        print("""df_long_ap_all.estimated_size("mb")""")
        print(df_long_ap_all.estimated_size("mb"))

        DAILY_LONG_PARAMS = list()
        DAILY_LONG_PARAMS.extend(RR_T_VENT_ALL_PARAMS)
        DAILY_LONG_PARAMS.extend([p for p in AUTRES_PARAMETRES_ALL_PARAMS if p not in RR_T_VENT_ALL_PARAMS])

        print("DAILY_LONG_PARAMS")
        print(DAILY_LONG_PARAMS)
        print("RR_T_VENT_ALL_PARAMS")
        print(RR_T_VENT_ALL_PARAMS)
        print("AUTRES_PARAMETRES_ALL_PARAMS")
        print(AUTRES_PARAMETRES_ALL_PARAMS)

        PARAM_INDEXES = dict((k.lower(), v) for v, k in enumerate(DAILY_LONG_PARAMS))

        print("PARAM_INDEXES")
        print(PARAM_INDEXES)

        def repl_pcode_with_pid(df: pl.DataFrame):
            return (
                df
                .with_columns(
                    param_id=pl.Series(PARAM_INDEXES.get(p) for p in df.select("param_code").to_series()).cast(pl.UInt16),
                )
                .drop("param_code")
            )

        df_long_rtv_pnorm = repl_pcode_with_pid(df_long_rtv_all)
        df_long_ap_pnorm = repl_pcode_with_pid(df_long_ap_all)  

        print("df_long_rtv_pnorm")
        print(df_long_rtv_pnorm)
        print("df_long_ap_pnorm")
        print(df_long_ap_pnorm)

        print("""df_autres_all.estimated_size("mb")""")
        print(df_autres_all.estimated_size("mb"))
        print("""df_long_ap_all.estimated_size("mb")""")
        print(df_long_ap_all.estimated_size("mb"))
        print("""df_long_ap_pnorm.estimated_size("mb")""")
        print(df_long_ap_pnorm.estimated_size("mb"))
        print("""df_long_ap_pnorm_without_source_file.estimated_size("mb")""")
        print(df_long_ap_pnorm.select(
            "station_id",
            "obs_date",
            "value",
            "quality_code",
            "status_code",
            "param_id"
        ).estimated_size("mb"))
        print()
        print("""df_rtv_all.estimated_size("mb")""")
        print(df_rtv_all.estimated_size("mb"))
        print("""df_long_rtv_all.estimated_size("mb")""")
        print(df_long_rtv_all.estimated_size("mb"))
        print("""df_long_rtv_pnorm_without_source_file.estimated_size("mb")""")
        print(df_long_rtv_pnorm.select(
            "station_id",
            "obs_date",
            "value",
            "quality_code",
            "status_code",
            "param_id"
        ).estimated_size("mb"))









if __name__ == "__main__":
    main()
