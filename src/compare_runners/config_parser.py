import datetime
import tomllib
from dataclasses import dataclass
from pathlib import Path


@dataclass
class Runner:
    name: str
    matcher_name: str
    matcher_from: datetime.datetime
    matcher_to: datetime.datetime


@dataclass
class Repo:
    gitlab_instance: str
    auth_token_env_var: str
    path: str


@dataclass
class Config:
    repos: list[Repo]
    measure_since: datetime.date
    runners: list[Runner]


def load_config(config_file: Path) -> Config:
    data = {}
    with open(config_file, "rb") as f:
        data = tomllib.load(f)

    today = datetime.date.today()
    last_month = today.replace(day=1) - datetime.timedelta(days=1)
    measure_since = data.get("since", last_month.strftime("%Y-%m-01"))

    repo_configs = []
    for repo in data.get("repos", []):
        gitlab_instance = repo.get("gitlab_instance", "https://gitlab.com")
        auth_token_env_var = repo.get("auth_token_env_var", "GITLAB_TOKEN")
        repo_path = repo.get("path")
        repo_configs.append(
            Repo(
                gitlab_instance=gitlab_instance,
                auth_token_env_var=auth_token_env_var,
                path=repo_path,
            )
        )

    runners_configs = []
    for runner in data.get("runners", []):
        runner_name = runner.get("name")
        runner_filters = runner.get("filters", [])
        matcher_name = None
        matcher_from = None
        matcher_to = None
        for runner_filter in runner_filters:
            matcher_name = runner_filter.get("name_match_pattern")
            from_timestamp = runner_filter.get("from_datetime")
            to_timestamp = runner_filter.get("to_datetime")
            if from_timestamp:
                matcher_from = datetime.datetime.fromisoformat(from_timestamp)
            if to_timestamp:
                matcher_to = datetime.datetime.fromisoformat(to_timestamp)
            break

        runners_configs.append(
            Runner(
                name=runner_name,
                matcher_name=matcher_name,
                matcher_from=matcher_from,
                matcher_to=matcher_to,
            )
        )

    return Config(
        repos=repo_configs, measure_since=measure_since, runners=runners_configs
    )
