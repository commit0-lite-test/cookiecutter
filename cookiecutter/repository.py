"""Cookiecutter repository functions."""

import os
import re
from os import PathLike
from pathlib import Path
from cookiecutter.exceptions import RepositoryNotFound
from cookiecutter.vcs import clone
from cookiecutter.zipfile import unzip

REPO_REGEX = re.compile(
    "\n# something like git:// ssh:// file:// etc.\n((((git|hg)\\+)?(git|ssh|file|https?):(//)?)\n |                                      # or\n (\\w+@[\\w\\.]+)                          # something like user@...\n)\n",
    re.VERBOSE,
)


def is_repo_url(value: str) -> bool:
    """Return True if value is a repository URL."""
    return bool(REPO_REGEX.match(value))


def is_zip_file(value: str) -> bool:
    """Return True if value is a zip file."""
    return value.lower().endswith(".zip")


def expand_abbreviations(template: str, abbreviations: dict[str, str]) -> str:
    """Expand abbreviations in a template name.

    :param template: The project template name.
    :param abbreviations: A dictionary of abbreviations.
    :return: The expanded template name.
    """
    if template in abbreviations:
        return abbreviations[template]
    for abbreviation, expansion in abbreviations.items():
        if template.startswith(f"{abbreviation}:"):
            suffix = template[len(abbreviation) + 1:]
            try:
                return expansion.format(suffix)
            except IndexError:
                return expansion
    return template


def repository_has_cookiecutter_json(repo_directory: PathLike[str]) -> bool:
    """Determine if `repo_directory` contains a `cookiecutter.json` file.

    :param repo_directory: The candidate repository directory.
    :return: True if the `repo_directory` is valid, else False.
    """
    repo_dir = Path(repo_directory)
    return (repo_dir / "cookiecutter.json").is_file()


def determine_repo_dir(
    template: str,
    abbreviations: dict[str, str],
    clone_to_dir: PathLike[str],
    checkout: str | None,
    no_input: bool,
    password: str | None = None,
    directory: str | None = None,
) -> tuple[PathLike[str], bool]:
    """Locate the repository directory from a template reference.

    :param template: The project template name.
    :param abbreviations: A dictionary of abbreviations.
    :param clone_to_dir: The directory to clone the repository to.
    :param checkout: The branch, tag or commit to checkout after clone.
    :param no_input: Whether to prompt the user for input or not.
    :param password: The password to use for authentication (optional).
    :param directory: The directory to use for the repository (optional).
    :return: The repository directory and a boolean indicating if the repository was cloned.
    :raises: `RepositoryNotFound` if a repository directory could not be found.
    """
    template = expand_abbreviations(template, abbreviations)

    if is_repo_url(template):
        repo_dir = clone(
            template, checkout=checkout, clone_to_dir=clone_to_dir, no_input=no_input
        )
        cleanup = True
    elif is_zip_file(template):
        repo_dir = unzip(
            template,
            is_url=is_repo_url(template),
            clone_to_dir=clone_to_dir,
            no_input=no_input,
            password=password,
        )
        cleanup = True
    else:
        repo_dir = os.path.join(clone_to_dir, template)
        cleanup = False

    if directory:
        repo_dir = os.path.join(repo_dir, directory)

    if not os.path.exists(repo_dir):
        raise RepositoryNotFound(
            f'A valid repository for "{template}" could not be found in the following '
            f'locations:\n{os.path.join(template, directory) if directory else template}\n{repo_dir}'
        )

    if not repository_has_cookiecutter_json(repo_dir):
        raise RepositoryNotFound(
            f'A valid repository for "{template}" could not be found in the following '
            f'location:\n{repo_dir}'
        )

    return repo_dir, cleanup
