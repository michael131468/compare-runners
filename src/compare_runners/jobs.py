import csv
import datetime
import logging
import re
import shutil
from dataclasses import dataclass
from pathlib import Path

import gitlab

from .config_parser import Runner

logger = logging.getLogger(__name__)


def fetch_jobs_data(
    gitlab_url: str,
    access_token: str,
    project_path: str,
    measure_since: str,
    csv_data_dir: Path = Path("./work"),
) -> Path:
    """
    Fetch GitLab CI jobs that have run since a certain period and store to csv.

    Args:
        gitlab_url (str): GitLab instance URL (e.g., 'https://gitlab.com')
        access_token (str): GitLab personal access token
        project_path (str): Project path
        measure_since (int): Date to measure since

    Returns:
        list: List of jobs that ran within the specified period
    """
    # Ensure we can write to the data dir
    csv_data_dir.mkdir(parents=True, exist_ok=True)
    (csv_data_dir / ".test").touch()
    (csv_data_dir / ".test").unlink()

    # Create GitLab session
    gl = gitlab.Gitlab(gitlab_url, private_token=access_token)
    gl.auth()
    project = gl.projects.get(project_path)

    # Calculate csv data file name
    csv_data_file = csv_data_dir / f"jobs_{project.id}.csv"

    # Load last seen job from csv data
    latest_data_cutoff = None
    if csv_data_file.exists():
        with open(csv_data_file, "r", newline="") as csvfile:
            jobs_csvreader = csv.reader(csvfile, delimiter=",", quotechar="|")
            for row in jobs_csvreader:
                latest_data_cutoff = datetime.datetime.fromisoformat(row[0])
                break

    # Calculate the cutoff date
    cutoff_date = datetime.datetime.fromisoformat(f"{measure_since}T00:00:00.0Z")

    # Fetch jobs with pagination
    tmp_csv_data_file = Path(f"{csv_data_file}.tmp")
    logger.info("Writing to %s", tmp_csv_data_file)
    with open(tmp_csv_data_file, "w", newline="") as csvfile:
        jobs_csvwriter = csv.writer(
            csvfile, delimiter=",", quotechar="|", quoting=csv.QUOTE_MINIMAL
        )
        page = 1
        per_page = 100
        hit_cutoff = False
        while hit_cutoff == False:
            # Get jobs for current page
            job_batch = project.jobs.list(
                page=page,
                per_page=per_page,
                order_by="created_at",
                sort="desc",
                all=False,
                scope=["success"],
            )

            if not job_batch:
                break

            # Stop if we find a job that hits the cutoff date
            # or a job we've already seen in our cached csv data
            for job in job_batch:
                # Parse job creation date
                job_created = datetime.datetime.fromisoformat(job.created_at)

                if job_created < cutoff_date:
                    hit_cutoff = True
                    break

                if latest_data_cutoff and job_created <= latest_data_cutoff:
                    hit_cutoff = True
                    break

                # Update csv data
                logger.info(
                    "Processing job: %s - %s (%s)", job.created_at, job.name, job.status
                )
                try:
                    jobs_csvwriter.writerow(
                        [
                            job.created_at,
                            job.name,
                            job.status,
                            job.duration,
                            job.queued_duration,
                            job.runner.get("description", ""),
                            job.runner.get("ip_address", ""),
                            job.runner.get("runner_type", ""),
                            ",".join(job.tag_list),
                            job.web_url,
                        ]
                    )
                except AttributeError as e:
                    logger.warning("Failed to scrape job runner: %s", e)
                    logger.warning("%s", job)

            page += 1

    # Copy older csv data to newer csv data file before replacing it
    if csv_data_file.exists():
        with open(csv_data_file, "r") as csvfile_prev:
            with open(tmp_csv_data_file, "a+") as csvfile_new:
                csvfile_new.write(csvfile_prev.read())

    logger.info("Updating: %s", csv_data_file)
    shutil.move(tmp_csv_data_file, csv_data_file)

    return csv_data_file


def get_measured_jobs(project_path: str, csv_data_file: Path) -> list[str]:
    job_names = set()
    with open(csv_data_file, "r", newline="") as csvfile:
        jobs_csvreader = csv.reader(csvfile, delimiter=",", quotechar="|")
        for row in jobs_csvreader:
            job_name = row[1]
            job_names.add(job_name)

    return sorted(job_names)


@dataclass
class JobDurationStats:
    runtime_duration_avg: float
    runtime_duration_min: float
    runtime_duration_max: float
    queue_duration_avg: float
    queue_duration_min: float
    queue_duration_max: float
    total_duration_avg: float
    total_duration_min: float
    total_duration_max: float
    no_of_jobs: int


def match_runner(
    job_created_at: str, job_runner_description: str, runner: Runner
) -> bool:
    # Try to match a runner to this job runner and update stats it if it matches
    # Only return True if all filters set match
    # Apply name matchers if set
    if runner.matcher_name and not re.fullmatch(
        runner.matcher_name, job_runner_description
    ):
        return False

    # Apply datetime matchers if set
    created_at = datetime.datetime.fromisoformat(job_created_at)
    if runner.matcher_from and created_at < runner.matcher_from:
        return False
    if runner.matcher_to and created_at > runner.matcher_to:
        return False

    return True


def get_job_stats(
    project_path: str, job_name: str, runner: Runner, csv_data_file: Path
) -> JobDurationStats:
    total_runtime_duration = 0.0
    total_queue_duration = 0.0
    total_job_duration = 0.0
    runtime_duration_avg = 0.0
    runtime_duration_min = 10000000.0
    runtime_duration_max = 0.0
    queue_duration_avg = 0.0
    queue_duration_min = 10000000.0
    queue_duration_max = 0.0
    total_duration_avg = 0.0
    total_duration_min = 10000000.0
    total_duration_max = 0.0
    no_of_jobs = 0

    if not csv_data_file.exists():
        raise RuntimeError("CSV Data file missing!")

    with open(csv_data_file, "r", newline="") as csvfile:
        jobs_csvreader = csv.reader(csvfile, delimiter=",", quotechar="|")
        for row in jobs_csvreader:
            job_created_at = row[0]
            csv_job_name = row[1]
            job_status = row[2]
            job_duration = float(row[3])
            job_queued_duration = float(row[4])
            job_runner_description = row[5]
            job_runner_ip_address = row[6]
            job_runner_runner_type = row[7]

            if csv_job_name != job_name:
                continue

            if match_runner(job_created_at, job_runner_description, runner):
                no_of_jobs += 1

                total_runtime_duration += job_duration
                if job_duration < runtime_duration_min:
                    runtime_duration_min = job_duration
                if job_duration > runtime_duration_max:
                    runtime_duration_max = job_duration

                total_queue_duration += job_queued_duration
                if job_queued_duration < queue_duration_min:
                    queue_duration_min = job_queued_duration
                if job_queued_duration > queue_duration_max:
                    queue_duration_max = job_queued_duration

                total_duration = job_duration + job_queued_duration
                total_job_duration += total_duration
                if total_duration < total_duration_min:
                    total_duration_min = total_duration
                if total_duration > total_duration_max:
                    total_duration_max = total_duration

    if no_of_jobs <= 0:
        runtime_duration_min = 0.0
        queue_duration_min = 0.0
        total_duration_min = 0.0
        runtime_duration_avg = 0.0
        queue_duration_avg = 0.0
        total_duration_avg = 0.0
    else:
        runtime_duration_avg = total_runtime_duration / float(no_of_jobs)
        queue_duration_avg = total_queue_duration / float(no_of_jobs)
        total_duration_avg = total_job_duration / float(no_of_jobs)

    return JobDurationStats(
        runtime_duration_avg,
        runtime_duration_min,
        runtime_duration_max,
        queue_duration_avg,
        queue_duration_min,
        queue_duration_max,
        total_duration_avg,
        total_duration_min,
        total_duration_max,
        no_of_jobs,
    )
