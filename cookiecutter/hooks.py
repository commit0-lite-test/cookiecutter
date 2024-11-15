"""Functions for discovering and executing various cookiecutter hooks."""

import logging
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from jinja2.exceptions import UndefinedError
from cookiecutter.exceptions import FailedHookException
from cookiecutter.utils import (
    create_env_with_context,
    create_tmp_repo_dir,
    rmtree,
    work_in,
)

logger = logging.getLogger(__name__)
_HOOKS = ["pre_prompt", "pre_gen_project", "post_gen_project"]
EXIT_SUCCESS = 0


def valid_hook(hook_file, hook_name):
    """Determine if a hook file is valid.

    :param hook_file: The hook file to consider for validity
    :param hook_name: The hook to find
    :return: The hook file validity
    """
    return (
        hook_file.startswith(hook_name)
        and hook_file.endswith((".py", ".sh"))
        and not hook_file.endswith(".pyc")
    )


def find_hook(hook_name, hooks_dir="hooks"):
    """Return a dict of all hook scripts provided.

    Must be called with the project template as the current working directory.
    Dict's key will be the hook/script's name, without extension, while values
    will be the absolute path to the script. Missing scripts will not be
    included in the returned dict.

    :param hook_name: The hook to find
    :param hooks_dir: The hook directory in the template
    :return: The absolute path to the hook script or None
    """
    if not os.path.exists(hooks_dir):
        return None

    for hook_file in os.listdir(hooks_dir):
        if valid_hook(hook_file, hook_name):
            return os.path.abspath(os.path.join(hooks_dir, hook_file))

    return None


def run_script(script_path, cwd="."):
    """Execute a script from a working directory.

    :param script_path: Absolute path to the script to run.
    :param cwd: The directory to run the script from.
    """
    with work_in(cwd):
        if script_path.endswith(".py"):
            subprocess.check_call([sys.executable, script_path], cwd=cwd)
        else:
            subprocess.check_call([script_path], cwd=cwd)


def run_script_with_context(script_path, cwd, context):
    """Execute a script after rendering it with Jinja.

    :param script_path: Absolute path to the script to run.
    :param cwd: The directory to run the script from.
    :param context: Cookiecutter project template context.
    """
    env = create_env_with_context(context)
    with open(script_path, "r") as f:
        script = f.read()
    try:
        rendered_script = env.from_string(script).render(**context)
    except UndefinedError as err:
        raise UndefinedVariableInTemplate(str(err), err, context)

    with tempfile.NamedTemporaryFile(mode="w", delete=False) as temp_script:
        temp_script.write(rendered_script)

    make_executable(temp_script.name)
    run_script(temp_script.name, cwd)
    os.remove(temp_script.name)


def run_hook(hook_name, project_dir, context):
    """Try to find and execute a hook from the specified project directory.

    :param hook_name: The hook to execute.
    :param project_dir: The directory to execute the script from.
    :param context: Cookiecutter project context.
    """
    hook_path = find_hook(hook_name)
    if hook_path:
        logger.debug("Running hook %s", hook_name)
        run_script_with_context(hook_path, project_dir, context)


def run_hook_from_repo_dir(
    repo_dir, hook_name, project_dir, context, delete_project_on_failure
):
    """Run hook from repo directory, clean project directory if hook fails.

    :param repo_dir: Project template input directory.
    :param hook_name: The hook to execute.
    :param project_dir: The directory to execute the script from.
    :param context: Cookiecutter project context.
    :param delete_project_on_failure: Delete the project directory on hook
        failure?
    """
    with work_in(repo_dir):
        try:
            run_hook(hook_name, project_dir, context)
        except FailedHookException:
            if delete_project_on_failure:
                logger.debug("Hook failed, deleting project dir %s", project_dir)
                rmtree(project_dir)
            raise


def run_pre_prompt_hook(repo_dir: "os.PathLike[str]") -> Path:
    """Run pre_prompt hook from repo directory.

    :param repo_dir: Project template input directory.
    """
    temp_dir = create_tmp_repo_dir(repo_dir)
    hook_path = find_hook("pre_prompt", os.path.join(temp_dir, "hooks"))
    if hook_path:
        logger.debug("Running pre_prompt hook")
        run_script(hook_path, cwd=temp_dir)
    return temp_dir
