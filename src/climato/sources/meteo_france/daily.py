from typing import Iterable


MF_DAILY_RELATIVE_PATH = "meteo_france/daily"

BASE_URL = "https://meteofrance.s3.sbg.io.cloud.ovh.net/data/synchro_ftp/BASE"

COLLECTIONS = {
    "quot": {
        "directory": "QUOT",
        "prefix": "Q",
    },
    "quot_comp": {
        "directory": "QUOT_COMP",
        "prefix": "Q-COMP",
    },
}

DEPARTMENTS = [str(i).zfill(2) for i in range(1, 96)]

PERIODS = ("before", "previous", "latest")

DATASET_YEAR = 2026

def build_period_tokens(dataset_year: int) -> dict:
    return {
        "before": "avant-1949",
        "previous": f"previous-1950-{dataset_year - 2}",
        "latest": f"latest-{dataset_year - 1}-{dataset_year}",
    }

PERIOD_TOKENS = build_period_tokens(DATASET_YEAR)

PARAMETER_FAMILIES = {
    "rr_t_vent": {
        "filename_part": "RR-T-Vent",
    },
    "autres_parametres": {
        "filename_part": "autres-parametres",
    },
}


def build_url(
        collection_key: str,
        department: str,
        time_period_key: str,
        parameter_family_key: str,
        dataset_year: int,
) -> str:
    directory = COLLECTIONS[collection_key]["directory"]
    prefix = COLLECTIONS[collection_key]["prefix"]
    family_token = PARAMETER_FAMILIES[parameter_family_key]["filename_part"]
    period_tokens = build_period_tokens(dataset_year)
    period_token = period_tokens[time_period_key]

    return f"{BASE_URL}/{directory}/{prefix}_{department}_{period_token}_{family_token}.csv.gz"


def build_resource_identity(
        collection_key: str,
        parameter_family_key: str,
        department: str,
        time_period_key: str,
        dataset_year: int,
) -> dict:
    url = build_url(collection_key, department, time_period_key, parameter_family_key, dataset_year)
    filename = url.rsplit("/", 1)[-1]
    
    return {
        "collection": collection_key,
        "parameter_family": parameter_family_key,
        "department": department,
        "period": time_period_key,
        "dataset_year": dataset_year,
        "source_url": url,
        "source_filename": filename,
        "raw_relative_path": f"{MF_DAILY_RELATIVE_PATH}/{dataset_year}/{collection_key}/{parameter_family_key}/{filename}",
    }


def build_candidate_resources_list(
        departments: Iterable[str],
        parameter_families: Iterable[str],
        collections: Iterable[str],
        periods: Iterable[str],
        dataset_year: int = DATASET_YEAR,
) -> list[dict]:
    return [
        build_resource_identity(
            collection,
            parameter_family,
            department,
            period,
            dataset_year,
        )
        for department in departments
        for parameter_family in parameter_families
        for collection in collections
        for period in periods
    ]
