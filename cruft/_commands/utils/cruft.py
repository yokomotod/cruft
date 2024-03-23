import json
from datetime import date, datetime
from pathlib import Path
from typing import Any, Dict, Optional

from git import Repo
from git.objects import Commit

from cruft.exceptions import CruftAlreadyPresent, NoCruftFound

CruftState = Dict[str, Any]


#######################
# Cruft related utils #
#######################


def get_cruft_file(project_dir_path: Path, exists: bool = True) -> Path:
    cruft_file = project_dir_path / ".cruft.json"
    if not exists and cruft_file.is_file():
        raise CruftAlreadyPresent(cruft_file)
    if exists and not cruft_file.is_file():
        raise NoCruftFound(project_dir_path.resolve())
    return cruft_file


def is_project_updated(
    repo: Repo,
    current_commit_hash: str,
    latest_commit_hash: str,
    strict: bool,
    allowed_delay_days: Optional[int] = None,
) -> bool:
    if (
        # If the latest commit exactly matches the current commit
        latest_commit_hash == current_commit_hash
        # Or if there have been no changes to the cookiecutter
        or not repo.index.diff(current_commit_hash)
    ):
        return True

    latest_commit = repo.commit(latest_commit_hash)
    current_commit = repo.commit(current_commit_hash)

    # Or if the strict flag is off, we allow newer commits to count as up to date
    if not strict and repo.is_ancestor(latest_commit, current_commit):
        return True

    # Or if allowed_delay_days is specified, we allow for not being the latest within that period
    if allowed_delay_days is not None and _is_within_allowed_delay_days(
        repo, current_commit, latest_commit, allowed_delay_days
    ):
        return True

    return False


def _is_within_allowed_delay_days(
    repo: Repo, current_commit: Commit, latest_commit: Commit, allowed_delay_days: int
) -> bool:
    # Compare to the oldest, not imported commit's date in template repo. Why not use ...
    # * latest_commit?  -- If the template repo continues to be updated continuously, we will be allowed to be behind indefinitely.
    # * current_commit? -- If the last commit of the template repo is old, we will be judged as older than allowed_delay_days immediately when next update comes.
    oldest_update_commit = next(
        repo.iter_commits(f"{current_commit}..{latest_commit}", reverse=True),
        None,
    )
    if not oldest_update_commit:
        return False

    oldest_update_date = datetime.fromtimestamp(oldest_update_commit.committed_date).date()

    return (date.today() - oldest_update_date).days <= allowed_delay_days


def json_dumps(cruft_state: Dict[str, Any]) -> str:
    text = json.dumps(cruft_state, ensure_ascii=False, indent=2, separators=(",", ": "))
    return text + "\n"
