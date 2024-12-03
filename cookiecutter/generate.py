"""Functions for generating a project from a project template."""

import fnmatch
import json
import logging
import os
import shutil
from collections import OrderedDict
from pathlib import Path
from typing import Any, Dict, Union

try:
    from binaryornot.check import is_binary
    from jinja2 import Environment
    from jinja2.exceptions import TemplateSyntaxError
except ImportError as e:
    raise ImportError(
        "jinja2 is not installed. Please install it using 'pip install jinja2'."
    ) from e

from cookiecutter.exceptions import ContextDecodingException, FailedHookException
from cookiecutter.utils import (
    create_env_with_context,
    make_sure_path_exists,
    rmtree,
    work_in,
)
from cookiecutter.hooks import run_hook

logger = logging.getLogger(__name__)


def is_copy_only_path(path: str, context: Dict[str, Any]) -> bool:
    """Check whether the given `path` should only be copied and not rendered.

    Returns True if `path` matches a pattern in the given `context` dict,
    otherwise False.

    :param path: A file-system path referring to a file or dir that
        should be rendered or just copied.
    :param context: cookiecutter context.
    """
    copy_only_patterns = context.get("_copy_without_render", [])
    return any(fnmatch.fnmatch(path, pattern) for pattern in copy_only_patterns)


def apply_overwrites_to_context(
    context: Dict[str, Any],
    overwrite_context: Dict[str, Any],
    *,
    in_dictionary_variable: bool = False,
) -> None:
    """Modify the given context in place based on the overwrite_context."""
    for key, value in overwrite_context.items():
        if isinstance(value, dict):
            if key not in context:
                context[key] = {}
            apply_overwrites_to_context(
                context[key], value, in_dictionary_variable=True
            )
        elif isinstance(value, list):
            if key not in context:
                context[key] = []
            context[key].extend(value)
        else:
            if in_dictionary_variable:
                context[key] = value
            else:
                context["cookiecutter"][key] = value


def generate_context(
    context_file: str = "cookiecutter.json",
    default_context: Dict[str, Any] | None = None,
    extra_context: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    """Generate the context for a Cookiecutter project template.

    Loads the JSON file as a Python object, with key being the JSON filename.

    :param context_file: JSON file containing key/value pairs for populating
        the cookiecutter's variables.
    :param default_context: Dictionary containing config to take into account.
    :param extra_context: Dictionary containing configuration overrides
    """
    context = {}
    try:
        with open(context_file) as file_handle:
            obj = json.load(file_handle, object_pairs_hook=OrderedDict)
        context = {"cookiecutter": obj}
    except ValueError as e:
        raise ContextDecodingException(
            f"JSON decoding error while loading '{context_file}': {e}"
        )

    # Apply defaults
    if default_context:
        apply_overwrites_to_context(context, default_context)

    # Apply overrides
    if extra_context:
        apply_overwrites_to_context(context, extra_context)

    return context


def generate_file(
    project_dir: Union[str, Path],
    infile: str,
    context: Dict[str, Any],
    env: Environment,
    skip_if_file_exists: bool = False,
) -> bool:
    """Render filename of infile as name of outfile, handle infile correctly.

    Dealing with infile appropriately:

        a. If infile is a binary file, copy it over without rendering.
        b. If infile is a text file, render its contents and write the
           rendered infile to outfile.

    Precondition:

        When calling `generate_file()`, the root template dir must be the
        current working directory. Using `utils.work_in()` is the recommended
        way to perform this directory change.

    :param project_dir: Absolute path to the resulting generated project.
    :param infile: Input file to generate the file from. Relative to the root
        template dir.
    :param context: Dict for populating the cookiecutter's variables.
    :param env: Jinja2 template execution environment.
    """
    logger.debug("Generating file %s", infile)

    # Render the path to the output file (not the contents of the input file)
    outfile_tmpl = env.from_string(infile)
    outfile = os.path.join(project_dir, outfile_tmpl.render(**context))

    logger.debug("Project dir is %s", project_dir)
    logger.debug("Output file is %s", outfile)

    if skip_if_file_exists and os.path.exists(outfile):
        logger.debug("File %s already exists, skipping", outfile)
        return False

    # Ensure paths to rendered files are all created
    make_sure_path_exists(Path(os.path.dirname(outfile)))

    # Just copy over binary files. Don't render.
    if is_binary(infile):
        logger.debug("Copying binary %s to %s without rendering", infile, outfile)
        shutil.copyfile(infile, outfile)
    else:
        # Force fwd slashes on Windows for get_template
        # This is a by-product of the Python templating engine, which always
        # uses Unix-style paths.
        infile_fwd_slashes = infile.replace(os.path.sep, "/")

        # Render the file
        try:
            tmpl = env.get_template(infile_fwd_slashes)
        except TemplateSyntaxError as exception:
            # Disable translated so that printed exception contains verbose
            # information about syntax error location
            exception.translated = False
            raise
        rendered_file = tmpl.render(**context)

        logger.debug("Writing %s", outfile)

        with open(outfile, "w", encoding="utf-8") as fh:
            fh.write(rendered_file)

    return True


def render_and_create_dir(
    dirname: str,
    context: Dict[str, Any],
    output_dir: Union[str, Path],
    environment: Environment,
    overwrite_if_exists: bool = False,
) -> str:
    """Render name of a directory, create the directory, return its path."""
    name_tmpl = environment.from_string(dirname)
    rendered_dirname = name_tmpl.render(**context)
    dir_to_create = os.path.normpath(os.path.join(output_dir, rendered_dirname))

    logger.debug(
        "Rendered dir %s must exist in output_dir %s", dir_to_create, output_dir
    )

    if not overwrite_if_exists and os.path.exists(dir_to_create):
        logger.debug("Dir %s already exists, skipping", dir_to_create)
        return dir_to_create

    make_sure_path_exists(Path(dir_to_create))
    return dir_to_create


def _run_hook_from_repo_dir(
    repo_dir: Union[str, Path],
    hook_name: str,
    project_dir: Union[str, Path],
    context: Dict[str, Any],
    delete_project_on_failure: bool,
) -> None:
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


def generate_files(
    repo_dir: Union[str, Path],
    context: Dict[str, Any] | None = None,
    output_dir: Union[str, Path] = ".",
    overwrite_if_exists: bool = False,
    skip_if_file_exists: bool = False,
    accept_hooks: bool = True,
    keep_project_on_failure: bool = False,
) -> str:
    """Render the templates and saves them to files.

    :param repo_dir: Project template input directory.
    :param context: Dict for populating the template's variables.
    :param output_dir: Where to output the generated project dir into.
    :param overwrite_if_exists: Overwrite the contents of the output directory
        if it exists.
    :param skip_if_file_exists: Skip the files in the corresponding directories
        if they already exist
    :param accept_hooks: Accept pre and post hooks if set to `True`.
    :param keep_project_on_failure: If `True` keep generated project directory even when
        generation fails
    """
    context = context or {}
    env = create_env_with_context(context)

    project_dir = render_and_create_dir(
        context["cookiecutter"]["_template"],
        context,
        output_dir,
        env,
        overwrite_if_exists,
    )

    # We want the Jinja path and the OS paths to match. Consequently, we'll:
    #   1. Join the outdir and the rendered_dirname
    #   2. Then normalize it.
    #      This will eliminate '..', '.' and '/' in the path
    #   3. Then turn it into an absolute path, following symlinks
    project_dir = os.path.abspath(project_dir)

    logger.debug("Project directory is %s", project_dir)

    # if we are overwriting, delete the old project folder
    if overwrite_if_exists and os.path.exists(project_dir):
        rmtree(project_dir)

    if accept_hooks:
        _run_hook_from_repo_dir(
            repo_dir,
            "pre_gen_project",
            project_dir,
            context,
            not keep_project_on_failure,
        )

    with work_in(repo_dir):
        for root, dirs, files in os.walk("."):
            for dirname in dirs:
                render_and_create_dir(
                    dirname,
                    context,
                    os.path.join(project_dir, root),
                    env,
                    overwrite_if_exists,
                )

            for filename in files:
                infile = os.path.join(root, filename)
                if infile.endswith(".swp"):
                    # Ignore vim swap files
                    continue
                if not is_copy_only_path(infile, context):
                    generate_file(
                        project_dir, infile, context, env, skip_if_file_exists
                    )
                else:
                    outfile_tmpl = env.from_string(infile)
                    outfile_rendered = outfile_tmpl.render(**context)
                    outfile = os.path.join(project_dir, outfile_rendered)

                    logger.debug("Copying %s to %s without rendering", infile, outfile)
                    make_sure_path_exists(Path(os.path.dirname(outfile)))
                    shutil.copyfile(infile, outfile)

    if accept_hooks:
        _run_hook_from_repo_dir(
            repo_dir,
            "post_gen_project",
            project_dir,
            context,
            not keep_project_on_failure,
        )

    return project_dir
