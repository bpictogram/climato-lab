import datetime
from pathlib import Path
import requests
import json
import csv
import sys

import climato.config as config
from climato.utils.colors import Color


today = datetime.datetime.now()

DAILY_DATA_DIR = config.get_daily_data_dir()


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
COLLECTIONS = {k: v for k, v in COLLECTIONS.items() if k == "quot"}


DEPARTMENTS = [str(i).zfill(2) for i in range(1, 96)]
DEPARTMENTS = ["03"]


year = today.year

DATASET_YEAR = 2026

def build_time_periods(dataset_year: int) -> tuple[str, ...]:
    return (
        "avant-1949",
        f"previous-1950-{dataset_year - 2}",
        f"latest-{dataset_year - 1}-{dataset_year}",
    )

TIME_PERIODS = [
    "avant-1949",
    f"previous-1950-{year - 2}",
    f"latest-{year - 1}-{year}",
]
TIME_PERIODS = build_time_periods(DATASET_YEAR)


FAMILIES = {
    "rr_t_vent": {
        "filename_part": "RR-T-Vent",
    },
    "autres_parametres": {
        "filename_part": "autres-parametres",
    },
}
FAMILIES = {k: v for k, v in FAMILIES.items() if k == "rr_t_vent"}


BASE_URL = "https://meteofrance.s3.sbg.io.cloud.ovh.net/data/synchro_ftp/BASE"


def build_url(
        collection_key: str,
        department: str,
        time_period: str,
        family_key: str,
) -> str:
    directory = COLLECTIONS[collection_key]["directory"]
    prefix = COLLECTIONS[collection_key]["prefix"]
    family_str = FAMILIES[family_key]["filename_part"]

    return f"{BASE_URL}/{directory}/{prefix}_{department}_{time_period}_{family_str}.csv.gz"


def build_dest_dir(
        collection_key: str,
        family_key: str,
):
    return DAILY_DATA_DIR / collection_key / family_key


def download(url: str, dest_dir: Path) -> dict:
    filename = url.rsplit("/", 1)[-1]
    dest_path = dest_dir / filename
    tmp_path = dest_dir / f"{filename}.part"

    dest_dir.mkdir(parents=True, exist_ok=True)

    if dest_path.exists():
        return {
            "status": "skipped",
            "size_bytes": dest_path.stat().st_size,
            "exception": None,
        }

    try:
        with requests.get(
            url,
            stream=True,
            timeout=(5, 60)
        ) as response:
            # if response is not None and response.status_code == 404:
            if response.status_code == 404:
                return {
                    "status": "not_found",
                    "size_bytes": None,
                    "exception": None,
                }
            
            response.raise_for_status()

            size_bytes = 0

            with tmp_path.open("wb") as file:            
                for chunk in response.iter_content(chunk_size=1024 * 1024):
                    if chunk:
                        file.write(chunk)
                        size_bytes += len(chunk)

        tmp_path.replace(dest_path)

        return {
            "status": "success",
            "size_bytes": size_bytes,
            "exception": None,
        }

    # except requests.exceptions.HTTPError as exception:
    #     return {
    #         "status": "HTTPError",
    #         "size_bytes": None,
    #         "exception": str(exception),
    #     }
    
    except requests.exceptions.RequestException as exception:
        tmp_path.unlink(missing_ok=True)

        return {
            "status": "request_error",
            "size_bytes": None,
            "exception": str(exception),
        }

    except OSError as exception:
        tmp_path.unlink(missing_ok=True)

        return {
            "status": "filesystem_error",
            "size_bytes": None,
            "exception": str(exception),
        }


def main():
    report = []
    success_count = 0
    total_size_bytes = 0

    for collection_key in COLLECTIONS.keys():
        for department in DEPARTMENTS:
            for family_key in FAMILIES.keys():
                for period in TIME_PERIODS:
                    url = build_url(collection_key, department, period, family_key)
                    filename = url.split("/")[-1]

                    print(f"\n{Color.BRIGHT_CYAN}---> Downloading file: {filename}{Color.RESET}")     
                    
                    dest_dir = build_dest_dir(collection_key, family_key)
                    download_info = download(url, dest_dir)

                    status = download_info.get("status")
                    exception = download_info.get("exception")
                    size_bytes = download_info.get("size_bytes")

                    if status == "success":
                        success_count += 1
                        total_size_bytes += size_bytes

                    if status == "success":
                        print(f"{Color.GREEN}Downloaded successfully: {filename} ({size_bytes / 1024**2:.2f} MiB){Color.RESET}")
                    elif status == "not_found":
                        print(f"{Color.YELLOW}File not found error (404): {filename}{Color.RESET}")
                    elif status == "request_error":
                        print(f"{Color.RED}Request error: {filename}\nException: {exception}{Color.RESET}")
                    elif status == "filesystem_error":
                        print(f"{Color.RED}Filesystem error: {filename}\nException: {exception}{Color.RESET}")

                    report_line = {
                        "collection": collection_key,
                        "department": department,
                        "period": period,
                        "family": family_key,
                        "url": url,
                        "local_path": str(dest_dir / filename),
                        "status": status,
                        "size_bytes": size_bytes,
                        "size_mb": (
                            size_bytes / 1024**2
                            if size_bytes is not None
                            else None
                        ),
                    }

                    report.append(report_line)

                    print(json.dumps(report_line, indent=4))

                    # return

    print(f"{Color.GREEN}Downloaded successfully {success_count} files ({total_size_bytes / 1024**2:.2f} MiB){Color.RESET}")

    timestamp = today.strftime("%Y%m%d%H%M%S")

    with open(DAILY_DATA_DIR / f"report_download_daily_{timestamp}.json", "w") as file:
        json.dump(report, file, indent=4)

    with open(DAILY_DATA_DIR / f"report_download_daily_{timestamp}.csv", "w") as file:
        writer = csv.DictWriter(
            file,
            fieldnames=["collection", "department", "period", "family", "url", "local_path", "status", "size_bytes", "size_mb"],
            delimiter=";"
        )
        writer.writeheader()
        writer.writerows(report)



if __name__ == "__main__":
    main()
