"""Functions for finding Cookiecutter templates and other components."""

import logging
import os
from pathlib import Path
from jinja2 import Environment
from cookiecutter.exceptions import NonTemplatedInputDirException

try:
    import jinja2
except ImportError:
    print("jinja2 is not installed. Please install it using 'pip install jinja2'")
    raise

logger = logging.getLogger(__name__)


def find_template(repo_dir: "os.PathLike[str]", env: Environment) -> Path:
    """Determine which child directory of ``repo_dir`` is the project template.

    :param repo_dir: Local directory of newly cloned repo.
    :param env: Jinja2 Environment object for rendering template variables.
    :return: Relative path to project template.
    """
    repo_dir_path = Path(repo_dir)
    logger.debug("Searching %s for the project template.", repo_dir)

    # Check if repo_dir itself is a cookiecutter template
    if _is_cookiecutter_template(repo_dir_path, env):
        return Path(".")

    # Look for 'cookiecutter.json' in subdirectories
    for dir_path in repo_dir_path.iterdir():
        if dir_path.is_dir() and _is_cookiecutter_template(dir_path, env):
            return dir_path.relative_to(repo_dir_path)

    # If we haven't found a template, raise an exception
    raise NonTemplatedInputDirException(
        "The repository {} is not a valid Cookiecutter template. "
        'A valid template must contain a "cookiecutter.json" file '
        'or have a "cookiecutter.json" file in one of its subdirectories.'.format(
            repo_dir
        )
    )


def _is_cookiecutter_template(dir_path: Path, env: Environment) -> bool:
    """Check if the given directory is a valid Cookiecutter template."""
    cookiecutter_json_path = dir_path / "cookiecutter.json"
    if cookiecutter_json_path.is_file():
        try:
            env.get_template(str(cookiecutter_json_path.relative_to(dir_path)))
            return True
        except Exception:
            logger.debug(
                "Unable to load %s as a valid Jinja2 template.",
                cookiecutter_json_path,
                exc_info=True,
            )
    return False
