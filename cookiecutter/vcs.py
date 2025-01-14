"""Helper functions for working with version control systems."""

import logging
import os
import subprocess
import shutil
from typing import Optional, Tuple, Union

from cookiecutter.exceptions import RepositoryCloneFailed, VCSNotInstalled
from cookiecutter.prompt import prompt_and_delete
from cookiecutter.utils import rmtree

logger = logging.getLogger(__name__)
BRANCH_ERRORS = ["error: pathspec", "unknown revision"]


def identify_repo(repo_url: str) -> Optional[Tuple[str, str]]:
    """Determine if `repo_url` should be treated as a URL to a git or hg repo.

    Repos can be identified by prepending "hg+" or "git+" to the repo URL.

    :param repo_url: Repo URL of unknown type.
    :returns: ('git', repo_url), ('hg', repo_url), or None.
    """
    if repo_url.startswith("git+"):
        return ("git", repo_url[4:])
    elif repo_url.startswith("hg+"):
        return ("hg", repo_url[3:])
    return None


def is_vcs_installed(repo_type: str) -> bool:
    """Check if the version control system for a repo type is installed.

    :param repo_type: The type of version control system ('git' or 'hg').
    :return: True if the VCS is installed, False otherwise.
    """
    return shutil.which(repo_type) is not None


def clone(
    repo_url: str,
    checkout: Optional[str] = None,
    clone_to_dir: Union[str, os.PathLike] = ".",
    no_input: bool = False,
) -> str:
    """Clone a repo to the current directory.

    :param repo_url: Repo URL of unknown type.
    :param checkout: The branch, tag or commit ID to checkout after clone.
    :param clone_to_dir: The directory to clone to.
                         Defaults to the current directory.
    :param no_input: Do not prompt for user input and eventually force a refresh of
        cached resources.
    :returns: str with path to the new directory of the repository.
    """
    repo_info = identify_repo(repo_url)
    repo_type, repo_url = repo_info if repo_info else ("git", repo_url)

    if not is_vcs_installed(repo_type):
        raise VCSNotInstalled(f"{repo_type} is not installed.")

    clone_to_dir = os.path.abspath(clone_to_dir)
    repo_dir = os.path.join(
        clone_to_dir, os.path.basename(repo_url).replace(".git", "")
    )

    if os.path.exists(repo_dir):
        if no_input or prompt_and_delete(repo_dir):
            rmtree(repo_dir)
        else:
            return repo_dir

    try:
        if repo_type == "git":
            subprocess.check_output(
                ["git", "clone", repo_url, repo_dir],
                stderr=subprocess.STDOUT,
            )
            if checkout:
                subprocess.check_output(
                    ["git", "checkout", checkout],
                    cwd=repo_dir,
                    stderr=subprocess.STDOUT,
                )
        elif repo_type == "hg":
            subprocess.check_output(["hg", "clone", repo_url, repo_dir])
            if checkout:
                subprocess.check_output(["hg", "update", checkout], cwd=repo_dir)
    except subprocess.CalledProcessError as error:
        rmtree(repo_dir)
        raise RepositoryCloneFailed(error) from error

    return repo_dir
