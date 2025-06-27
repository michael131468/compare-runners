import argparse
import datetime
import json
import logging
import os
import sys
from pathlib import Path


from .config_parser import Repo, Config, load_config
from .jobs import JobDurationStats, fetch_jobs_data, get_job_stats, get_measured_jobs
from .reports import make_html_table

logger = logging.getLogger(__name__)


def create_parser():
    """Create and configure argument parser with config file support."""
    parser = argparse.ArgumentParser(
        description="Gather runtime statistics for GitLab CI Jobs",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --config /path/to/config.yaml
  %(prog)s -c ./settings.json
  %(prog)s  # Uses default config file
        """,
    )

    parser.add_argument(
        "-c",
        "--config",
        type=Path,
        default="config.toml",
        help="Path to configuration file (default: %(default)s)",
    )
    parser.add_argument(
        "--no-fetch",
        dest="no_fetch",
        action="store_true",
        help="Toggle to skip fetching new jobs data",
    )

    # Optional: Add other common arguments
    parser.add_argument(
        "-v", "--verbose", action="store_true", help="Enable verbose logging output"
    )

    return parser


def main():
    logging.basicConfig(level=logging.INFO)
    logger.info("Hello from compare-runners!")
    parser = create_parser()
    args = parser.parse_args()

    # Load config
    if not args.config.exists():
        logger.error("Configuration File Missing! (%s)", args.config)
        sys.exit(1)

    config = load_config(args.config)

    # Get jobs data
    print(args.no_fetch)
    if args.no_fetch:
        logger.info("Skipping fetching of new data")
    else:
        logger.info("Measuring jobs since: %s", config.measure_since)
        csv_data_files = {}
        for repo in config.repos:
            logger.info("Processing jobs for: %s", repo.path)
            access_token = os.environ.get(repo.auth_token_env_var)
            csv_data_files[repo.path] = fetch_jobs_data(
                repo.gitlab_instance, access_token, repo.path, config.measure_since
            )

    logger.info("Crunching the numbers...")
    # TODO: Rework this into dataclasses and avoid dicts and ensure ordering
    runner_stats = {}
    for repo in config.repos:
        runner_stats[str(repo.path)] = {}
        logger.info("Processing repo: %s", repo.path)
        csv_data_file = csv_data_files[repo.path]
        project_jobs = get_measured_jobs(repo.path, csv_data_file)
        for job_name in project_jobs:
            runner_stats[str(repo.path)][job_name] = {}
            logger.info("  - Job: %s", job_name)
            for runner in config.runners:
                logger.info("    - Runner: %s", runner.name)
                job_stats = get_job_stats(repo.path, job_name, runner, csv_data_file)
                runner_stats[str(repo.path)][job_name][runner.name] = {
                    "no_of_jobs": job_stats.no_of_jobs,
                    "runtime_duration_avg": round(job_stats.runtime_duration_avg, 2),
                    "runtime_duration_min": round(job_stats.runtime_duration_min, 2),
                    "runtime_duration_max": round(job_stats.runtime_duration_max, 2),
                    "queue_duration_avg": round(job_stats.queue_duration_avg, 2),
                    "queue_duration_min": round(job_stats.queue_duration_min, 2),
                    "queue_duration_max": round(job_stats.queue_duration_max, 2),
                    "total_duration_avg": round(job_stats.total_duration_avg, 2),
                    "total_duration_min": round(job_stats.total_duration_min, 2),
                    "total_duration_max": round(job_stats.total_duration_max, 2),
                }
                logger.info("      - no_of_jobs: %d", job_stats.no_of_jobs)

    # Create json data report
    with open("runner_statistics.json", "w") as f:
        json.dump(runner_stats, f)
    logger.info("Raw statistics outputted to runner_statistics.json")

    # Create tabulated report
    html_stats_file = make_html_table(runner_stats)
    logger.info(f"Tabulated data outputted to {html_stats_file}")


if __name__ == "__main__":
    main()
