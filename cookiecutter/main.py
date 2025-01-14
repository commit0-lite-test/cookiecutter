"""Main entry point for the `cookiecutter` command.

The code in this module is also a good example of how to use Cookiecutter as a
library rather than a script.
"""

import logging
import os
import sys
from copy import copy
from pathlib import Path
from cookiecutter.config import get_user_config
from cookiecutter.generate import generate_context, generate_files
from cookiecutter.hooks import run_pre_prompt_hook
from cookiecutter.prompt import prompt_for_config
from cookiecutter.replay import dump, load
from cookiecutter.repository import determine_repo_dir
from cookiecutter.utils import rmtree
from cookiecutter.prompt import prompt_and_delete
from typing import Optional, Dict, Any, Union, Type, List
from types import TracebackType

logger = logging.getLogger(__name__)


def cookiecutter(
    template: str,
    checkout: Optional[str] = None,
    no_input: bool = False,
    extra_context: Optional[Dict[str, Any]] = None,
    replay: Optional[Union[bool, str]] = None,
    overwrite_if_exists: bool = False,
    output_dir: str = ".",
    config_file: Optional[str] = None,
    default_config: bool = False,
    password: Optional[str] = None,
    directory: Optional[str] = None,
    skip_if_file_exists: bool = False,
    accept_hooks: bool = True,
    keep_project_on_failure: bool = False,
    replay_file: Optional[str] = None,
) -> Optional[str]:
    """Run Cookiecutter just as if using it from the command line.

    :param template: A directory containing a project template directory,
        or a URL to a git repository.
    :param checkout: The branch, tag or commit ID to checkout after clone.
    :param no_input: Do not prompt for user input.
        Use default values for template parameters taken from `cookiecutter.json`, user
        config and `extra_dict`. Force a refresh of cached resources.
    :param extra_context: A dictionary of context that overrides default
        and user configuration.
    :param replay: Do not prompt for input, instead read from saved json. If
        ``True`` read from the ``replay_dir``.
        if it exists
    :param overwrite_if_exists: Overwrite the contents of the output directory
        if it exists.
    :param output_dir: Where to output the generated project dir into.
    :param config_file: User configuration file path.
    :param default_config: Use default values rather than a config file.
    :param password: The password to use when extracting the repository.
    :param directory: Relative path to a cookiecutter template in a repository.
    :param skip_if_file_exists: Skip the files in the corresponding directories
        if they already exist.
    :param accept_hooks: Accept pre and post hooks if set to `True`.
    :param keep_project_on_failure: If `True` keep generated project directory even when
        generation fails
    """
    project_dir = None
    try:
        # Get user config
        config_dict = get_user_config(
            config_file=config_file, default_config=default_config
        )

        # Get the repo directory and determine if it should be cleaned up afterwards
        repo_dir, cleanup = determine_repo_dir(
            template=template,
            abbreviations=config_dict["abbreviations"],
            clone_to_dir=config_dict["cookiecutters_dir"],
            checkout=checkout,
            no_input=no_input,
            password=password,
            directory=directory,
        )

        # If it's a repo and the repo hasn't been cleaned up, prompt the user to manually delete it
        if cleanup:
            try:
                prompt_and_delete(repo_dir, no_input=no_input)
            except SystemExit:
                return None

        # Run pre-prompt hook if it exists
        if accept_hooks:
            run_pre_prompt_hook(repo_dir)

        # Determine the context
        context_file = os.path.join(repo_dir, "cookiecutter.json")
        context = generate_context(
            context_file=context_file,
            default_context=config_dict["default_context"],
            extra_context=extra_context,
        )

        # Prompt the user to manually configure at the command line.
        # If no_input is True, proceed with defaults from the JSON file.
        if not replay and not no_input:
            context["cookiecutter"] = prompt_for_config(context)

        # Load context from replay file if it exists
        if replay:
            if replay_file:
                context = load(Path(replay_file).parent, Path(replay_file).name)
            else:
                context = load(config_dict["replay_dir"], template)

        # Include template dir or url in the context dict
        if isinstance(context, dict) and isinstance(context.get("cookiecutter"), dict):
            context["cookiecutter"]["_template"] = template

        # Render the project
        project_dir = generate_files(
            repo_dir=repo_dir,
            context=context,
            overwrite_if_exists=overwrite_if_exists,
            skip_if_file_exists=skip_if_file_exists,
            output_dir=output_dir,
            accept_hooks=accept_hooks,
            keep_project_on_failure=keep_project_on_failure,
        )

        # Cleanup and return
        if cleanup:
            rmtree(repo_dir)

        # Dump context if replay is True
        if replay and isinstance(context, dict):
            dump(config_dict["replay_dir"], template, context)

        return project_dir

    except Exception:
        if not keep_project_on_failure and project_dir:
            rmtree(project_dir)
        raise


class _patch_import_path_for_repo:
    def __init__(self, repo_dir: "os.PathLike[str]"):
        self._repo_dir = f"{repo_dir}" if isinstance(repo_dir, Path) else repo_dir
        self._path = None

    def __enter__(self):
        self._path = copy(sys.path)
        sys.path.append(str(self._repo_dir))

    def __exit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_value: Optional[BaseException],
        traceback: Optional[TracebackType],
    ) -> None:
        sys.path = self._path
