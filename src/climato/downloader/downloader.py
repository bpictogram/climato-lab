import datetime
from pathlib import Path
import requests
import json
import argparse
import hashlib

import climato.config as config
from climato.utils.colors import Color
from climato.utils.datetime import utc_now_micro
from climato.sources.meteo_france.daily import (
    COLLECTIONS,
    DEPARTMENTS,
    PARAMETER_FAMILIES,
    build_candidate_resources_list,
)


run_started_at = datetime.datetime.now(datetime.UTC)
year_str = run_started_at.strftime("%Y")
month_str = run_started_at.strftime("%m")
run_timestamp = run_started_at.strftime("%Y%m%dT%H%M%SZ")

RAW_DATA_DIR = config.get_raw_data_dir()
DATA_DIR = config.get_data_dir()

DOWNLOAD_REPORT_DIR = DATA_DIR / "metadata" / "downloads" / "daily" / year_str / month_str
DOWNLOAD_REPORT_DIR.mkdir(parents=True, exist_ok=True)

DOWNLOAD_REPORT_PATH = DOWNLOAD_REPORT_DIR / f"download_{run_timestamp}.jsonl"

# Pour test sur périmètre restreint
# COLLECTIONS = {k: v for k, v in COLLECTIONS.items() if k == "quot"}
# COLLECTIONS = {k: v for k, v in COLLECTIONS.items()}
# DEPARTMENTS = ["01", "02", "03"]


def build_period_config() -> dict:
    return {
        "before": {
            "valid_args": ("before", "b", "avant"),
        },
        "previous": {
            "valid_args": ("previous", "p"),
        },
        "latest": {
            "valid_args": ("latest", "l"),
        },
    }

PERIOD_CONFIGS = build_period_config()

def build_period_choices():
    choices = []
    for conf in PERIOD_CONFIGS.values():
        choices.extend(conf["valid_args"])

    return choices

PERIOD_CHOICES = build_period_choices()

# PARAMETER_FAMILIES = {k: v for k, v in PARAMETER_FAMILIES.items() if k == "rr_t_vent"}
# PARAMETER_FAMILIES = {k: v for k, v in PARAMETER_FAMILIES.items()}


# def build_url(
#         collection_key: str,
#         department: str,
#         time_period_key: str,
#         family_key: str,
# ) -> str:
#     directory = COLLECTIONS[collection_key]["directory"]
#     prefix = COLLECTIONS[collection_key]["prefix"]
#     family_token = PARAMETER_FAMILIES[family_key]["filename_part"]
#     period_token = PERIOD_TOKENS[time_period_key]

#     return f"{BASE_URL}/{directory}/{prefix}_{department}_{period_token}_{family_token}.csv.gz"


# def build_dest_dir(
#         collection_key: str,
#         family_key: str,
# ):
#     return DAILY_DATA_DIR / collection_key / family_key


# def download_old(url: str, dest_dir: Path) -> dict:
#     filename = url.rsplit("/", 1)[-1]
#     dest_path = dest_dir / filename
#     tmp_path = dest_dir / f"{filename}.part"

#     dest_dir.mkdir(parents=True, exist_ok=True)

#     sha256 = hashlib.sha256()

#     try:
#         with requests.get(
#             url,
#             stream=True,
#             timeout=(5, 60)
#         ) as response:
#             # print(f"{Color.RED}" + "#" * 30 + f"{Color.RESET}")
#             # print(response.headers)
#             # print(f"{Color.RED}" + "#" * 30 + f"{Color.RESET}")

#             if response.status_code == 404:
#                 return {
#                     "status": "not_found",
#                     "http_status": response.status_code,
#                     "size_bytes": None,
#                     "exception": None,
#                 }
            
#             response.raise_for_status()

#             size_bytes = 0

#             with tmp_path.open("wb") as file:            
#                 for chunk in response.iter_content(chunk_size=1024 * 1024):
#                     if not chunk:
#                         continue

#                     file.write(chunk)
#                     size_bytes += len(chunk)
#                     sha256.update(chunk)

#         tmp_path.replace(dest_path)

#         etag = response.headers.get("ETag")
#         last_modified = response.headers.get("Last-Modified")

#         if last_modified:
#             last_modified_iso = (
#                 datetime.datetime.strptime(
#                     last_modified,
#                     "%a, %d %b %Y %H:%M:%S GMT",
#                 )
#                 .strftime("%Y-%m-%dT%H:%M:%SZ")
#             )

#         return {
#             "status": "success",
#             "http_status": response.status_code,
#             "size_bytes": size_bytes,
#             "etag": etag,
#             "last_modified": last_modified_iso if last_modified else None,
#             "sha256": sha256.hexdigest(),
#             "exception": None,
#         }
    
#     except requests.exceptions.RequestException as exception:
#         tmp_path.unlink(missing_ok=True)

#         return {
#             "status": "request_error",
#             "size_bytes": None,
#             "exception": str(exception),
#         }

#     except OSError as exception:
#         tmp_path.unlink(missing_ok=True)

#         return {
#             "status": "filesystem_error",
#             "size_bytes": None,
#             "exception": str(exception),
#         }


def download(resource: dict, report_path: Path) -> dict:
    raw_relative_path_str: str = resource["raw_relative_path"]
    dest_dir_relative_path_str = raw_relative_path_str.rsplit("/", 1)[0]

    dest_dir = RAW_DATA_DIR / dest_dir_relative_path_str

    filename: str = resource["source_filename"]
    dest_path = dest_dir / filename
    tmp_path = dest_dir / f"{filename}.part"

    url: str = resource["source_url"]

    report_line = {
        "collection": resource["collection"],
        "parameter_family": resource["parameter_family"],
        "department": resource["department"],
        "period": resource["period"],
        "dataset_year": resource["dataset_year"],
        "source_url": url,
        "source_filename": filename,
        "raw_relative_path": None,
        "status": None,
        "http_status": None,
        "size_bytes": None,
        "attempted_at": None,
        "checked_at": None,
        "downloaded_at": None,
        "etag": None,
        "source_last_modified_at": None,
        "sha256": None,
        "exception": None,
    }

    sha256 = hashlib.sha256()

    try:
        report_line["attempted_at"] = utc_now_micro()

        with requests.get(
            url,
            stream=True,
            timeout=(5, 60)
        ) as response:
            checked_at = utc_now_micro()
            report_line["checked_at"] = checked_at
            
            if response.status_code == 404:
                report_line.update({
                    "status": "not_found",
                    "http_status": response.status_code,
                })

                with report_path.open("a") as file:
                    file.write(json.dumps(report_line) + "\n")

                return report_line

            report_line["http_status"] = response.status_code
            
            response.raise_for_status()

            size_bytes = 0

            dest_dir.mkdir(parents=True, exist_ok=True)

            with tmp_path.open("wb") as file:            
                for chunk in response.iter_content(chunk_size=1024 * 1024):
                    if not chunk:
                        continue

                    file.write(chunk)
                    size_bytes += len(chunk)
                    sha256.update(chunk)

        # If success
        tmp_path.replace(dest_path)

        downloaded_at = utc_now_micro()
        etag = response.headers.get("ETag")
        last_modified = response.headers.get("Last-Modified")

        if last_modified:
            last_modified_iso = (
                datetime.datetime.strptime(
                    last_modified,
                    "%a, %d %b %Y %H:%M:%S GMT",
                )
                .strftime("%Y-%m-%dT%H:%M:%SZ")
            )

        report_line.update({
            "raw_relative_path": raw_relative_path_str,
            "status": "success",
            "size_bytes": size_bytes,
            "downloaded_at": downloaded_at,
            "etag": etag,
            "source_last_modified_at": last_modified_iso if last_modified else None,
            "sha256": sha256.hexdigest(),
        })
    
    except requests.exceptions.RequestException as exception:
        tmp_path.unlink(missing_ok=True)

        report_line.update({
            "status": "request_error",
            "exception": str(exception),
        })

    except OSError as exception:
        tmp_path.unlink(missing_ok=True)

        report_line.update({
            "status": "filesystem_error",
            "exception": str(exception),
        })

    with report_path.open("a") as file:
        file.write(json.dumps(report_line) + "\n")

    return report_line


def parse_args():
    parser = argparse.ArgumentParser(
        description="Download meteo.data.gouv.fr data",
    )

    parser.add_argument(
        "-p", "--period",
        type=str,
        nargs="+",
        choices=PERIOD_CHOICES,
        default=["latest"],
    )

    return parser.parse_args()


def validate_period_flag(period_args: list):
    selected_keys = []

    for period_key, period_conf in PERIOD_CONFIGS.items():
        if any(x in period_conf["valid_args"] for x in period_args):
            selected_keys.append(period_key)

    return selected_keys


# def main_old():
#     dt_start = datetime.datetime.now()

#     args = parse_args()

#     period_keys = validate_period_flag(args.period)

#     report = []
#     success_count = 0
#     total_size_bytes = 0

#     for department in DEPARTMENTS:
#         for family_key in PARAMETER_FAMILIES.keys():
#             for collection_key in COLLECTIONS.keys():
#                 for period_key in period_keys:
#                     dt_current = datetime.datetime.now()
#                     td = dt_current - dt_start
#                     td_h, td_m, td_s, td_us = td.seconds // 3600, (td.seconds // 60) % 60, td.seconds % 60, td.microseconds

#                     ts = dt_current.strftime("%Y-%m-%d %H:%M:%S")

#                     url = build_url(collection_key, department, period_key, family_key)
#                     filename = url.split("/")[-1]

#                     print(f"{Color.BRIGHT_CYAN}\n{ts} (processed {total_size_bytes / 1024**2:.2f} MiB in {td_h}h {td_m}m {td_s}s {td_us}us)\n"
#                           f"---> Attempt to download file: {filename}{Color.RESET}")
                    
#                     dest_dir = build_dest_dir(collection_key, family_key)
#                     download_info = download(url, dest_dir)

#                     status = download_info.get("status")
#                     exception = download_info.get("exception")
#                     size_bytes = download_info.get("size_bytes")

#                     if status == "success":
#                         success_count += 1
#                         total_size_bytes += size_bytes

#                     if status == "success":
#                         print(f"{Color.GREEN}Downloaded successfully: {filename} ({size_bytes / 1024**2:.2f} MiB){Color.RESET}")
#                     elif status == "not_found":
#                         print(f"{Color.YELLOW}File not found (404): {filename}{Color.RESET}")
#                     elif status == "request_error":
#                         print(f"{Color.RED}Request error: {filename}\nException: {exception}{Color.RESET}")
#                     elif status == "filesystem_error":
#                         print(f"{Color.RED}Filesystem error: {filename}\nException: {exception}{Color.RESET}")

#                     dt_current_iso = dt_current.astimezone(datetime.UTC).strftime("%Y-%m-%dT%H:%M:%SZ")

#                     report_line = {
#                         "collection": collection_key,
#                         "parameter_family": family_key,
#                         "department": department,
#                         "period": period_key,
#                         "dataset_year": DATASET_YEAR,
#                         "source_url": url,
#                         "source_filename": filename,
#                         "local_path": str(dest_dir / filename) if status == "success" else None,
#                         "status": status,
#                         "http_status": download_info.get("http_status"),
#                         "size_bytes": size_bytes,
#                         "size_mb": (
#                             size_bytes / 1024**2
#                             if size_bytes is not None
#                             else None
#                         ),
#                         "downloaded_at": dt_current_iso,
#                         "etag": download_info.get("etag"),
#                         "last_modified": download_info.get("last_modified"),
#                         "sha256": download_info.get("sha256"),
#                     }

#                     report.append(report_line)

#                     # print(json.dumps(report_line, indent=4))

#                     # return

#     dt_current = datetime.datetime.now()
#     td = dt_current - dt_start
#     td_h, td_m, td_s, td_us = td.seconds // 3600, (td.seconds // 60) % 60, td.seconds % 60, td.microseconds

#     print(
#         f"{Color.GREEN}\nDownloaded successfully {success_count} files "
#         f"({total_size_bytes / 1024**2:.2f} MiB) in {td_h}h {td_m}m {td_s}s {td_us}us{Color.RESET}"
#     )

#     timestamp = today.strftime("%Y%m%d%H%M%S")

#     with open(DAILY_DATA_DIR / f"report_download_daily_{timestamp}.json", "w") as file:
#         json.dump(report, file, indent=4)

#     # with open(DAILY_DATA_DIR / f"report_download_daily_{timestamp}.csv", "w") as file:
#     #     writer = csv.DictWriter(
#     #         file,
#     #         fieldnames=["collection", "department", "period", "family", "url", "local_path", "status", "size_bytes", "size_mb"],
#     #         delimiter=";",
#     #     )
#     #     writer.writeheader()
#     #     writer.writerows(report)


def main():
    dt_run_start = datetime.datetime.now()

    args = parse_args()
    
    period_keys = validate_period_flag(args.period)

    run_started_at = dt_run_start.astimezone(datetime.UTC)

    ts_log = dt_run_start.strftime("%Y-%m-%d %H:%M:%S")
    
    print(
        f"{Color.BRIGHT_MAGENTA}\n{ts_log} | Download run starting{Color.RESET}"
    )

    year_str = run_started_at.strftime("%Y")
    month_str = run_started_at.strftime("%m")
    run_timestamp = run_started_at.strftime("%Y%m%dT%H%M%SZ")

    DATA_DIR = config.get_data_dir()

    report_dir = DATA_DIR / "metadata" / "downloads" / "daily" / year_str / month_str
    report_dir.mkdir(parents=True, exist_ok=True)

    report_path = DOWNLOAD_REPORT_DIR / f"download_{run_timestamp}.jsonl"

    success_count = 0
    total_size_bytes = 0

    resources = build_candidate_resources_list(
        DEPARTMENTS,
        PARAMETER_FAMILIES,
        COLLECTIONS,
        period_keys,
    )

    ts_log = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    n_resources = len(resources)
    
    print(
        f"{Color.BRIGHT_MAGENTA}{ts_log} | {n_resources} candidate resources{Color.RESET}"
    )

    for resource in resources:
        dt_resource_start = datetime.datetime.now()

        filename = resource["source_filename"]
        
        td = dt_resource_start - dt_run_start
        td_h, td_m, td_s, td_us = td.seconds // 3600, (td.seconds // 60) % 60, td.seconds % 60, td.microseconds
        ts_log = dt_resource_start.strftime("%Y-%m-%d %H:%M:%S")

        print(
            f"{Color.BRIGHT_CYAN}\n{ts_log} | Attempt to download resource: {filename}{Color.RESET}"
        )

        report_line = download(resource, report_path)

        dt_resource_end = datetime.datetime.now()
        td = dt_resource_end - dt_run_start
        td_h, td_m, td_s, td_us = td.seconds // 3600, (td.seconds // 60) % 60, td.seconds % 60, td.microseconds
        ts_log = dt_resource_start.strftime("%Y-%m-%d %H:%M:%S")

        status = report_line["status"]
        exception = report_line["exception"]
        size_bytes = report_line["size_bytes"]

        if status == "success":
            success_count += 1
            total_size_bytes += size_bytes

        if status == "success":
            print(f"{Color.GREEN}{ts_log} | Downloaded successfully: {filename} ({size_bytes / 1024**2:.2f} MiB){Color.RESET}")
        elif status == "not_found":
            print(f"{Color.YELLOW}{ts_log} | File not found (404): {filename}{Color.RESET}")
        elif status == "request_error":
            print(f"{Color.RED}{ts_log} | Request error: {filename}\nException: {exception}{Color.RESET}")
        elif status == "filesystem_error":
            print(f"{Color.RED}{ts_log} | Filesystem error: {filename}\nException: {exception}{Color.RESET}")
        
        print(
            f"{Color.WHITE}{ts_log} | Downloaded successfully {success_count} files ({total_size_bytes / 1024**2:.2f} MiB) "
            f"in {td_h}h {td_m}m {td_s}s {td_us}us{Color.RESET}"
        )    

    dt_run_end = datetime.datetime.now()
    td = dt_run_end - dt_run_start
    td_h, td_m, td_s, td_us = td.seconds // 3600, (td.seconds // 60) % 60, td.seconds % 60, td.microseconds
    ts_log = dt_run_end.strftime("%Y-%m-%d %H:%M:%S")

    print(
        f"{Color.GREEN}\n{ts_log} | Run ended: downloaded successfully {success_count} files "
        f"({total_size_bytes / 1024**2:.2f} MiB) in {td_h}h {td_m}m {td_s}s {td_us}us{Color.RESET}\n"
        f"Report generated: {report_path}"
    )


if __name__ == "__main__":
    main()
