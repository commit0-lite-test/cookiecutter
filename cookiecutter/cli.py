"""Main `cookiecutter` CLI."""

import os
import sys
from typing import List, Optional

import click
from cookiecutter import __version__
from cookiecutter.config import get_user_config
from cookiecutter.exceptions import CookiecutterException, RepositoryNotFound
from cookiecutter.log import configure_logger
from cookiecutter.main import cookiecutter


def version_msg() -> str:
    """Return the Cookiecutter version, location and Python powering it."""
    python_version = sys.version
    location = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return f"Cookiecutter {__version__}\nPython {python_version}\nFrom {location}"


def validate_extra_context(
    ctx: click.Context, param: click.Parameter, value: List[str]
) -> List[str]:
    """Validate extra context."""
    for s in value:
        if "=" not in s:
            raise click.BadParameter(
                f'"{s}" is not a valid key/value pair. ' "Use the format key=value."
            )
    return value


def list_installed_templates(
    default_config: bool, passed_config_file: Optional[str]
) -> None:
    """List installed (locally cloned) templates. Use cookiecutter --list-installed."""
    config = get_user_config(passed_config_file, default_config)
    cookiecutters_dir: Optional[str] = config.get("cookiecutters_dir")
    if cookiecutters_dir is None or not os.path.exists(cookiecutters_dir):
        click.echo("No templates found")
        return

    template_names = [
        d
        for d in os.listdir(cookiecutters_dir)
        if os.path.isdir(os.path.join(cookiecutters_dir, d))
    ]

    if not template_names:
        click.echo("No templates found")
    else:
        click.echo("Installed templates:")
        for template_name in template_names:
            click.echo(f"  {template_name}")


import click

@click.command(context_settings=dict(help_option_names=["-h", "--help"]))
@click.version_option(__version__, "-V", "--version", message=version_msg())
@click.argument("template", required=False)
@click.argument("extra_context", nargs=-1, callback=validate_extra_context)
@click.pass_context
@click.option(
    "--no-input",
    is_flag=True,
    help="Do not prompt for parameters and only use cookiecutter.json file content. Defaults to deleting any cached resources and redownloading them. Cannot be combined with the --replay flag.",
)
@click.option(
    "-c", "--checkout", help="branch, tag or commit to checkout after git clone"
)
@click.option(
    "--directory",
    help="Directory within repo that holds cookiecutter.json file for advanced repositories with multi templates in it",
)
@click.option(
    "-v", "--verbose", is_flag=True, help="Print debug information", default=False
)
@click.option(
    "--replay",
    is_flag=True,
    help="Do not prompt for parameters and only use information entered previously. Cannot be combined with the --no-input flag or with extra configuration passed.",
)
@click.option(
    "--replay-file",
    type=click.Path(),
    default=None,
    help="Use this file for replay instead of the default.",
)
@click.option(
    "-f",
    "--overwrite-if-exists",
    is_flag=True,
    help="Overwrite the contents of the output directory if it already exists",
)
@click.option(
    "-s",
    "--skip-if-file-exists",
    is_flag=True,
    help="Skip the files in the corresponding directories if they already exist",
    default=False,
)
@click.option(
    "-o",
    "--output-dir",
    default=".",
    type=click.Path(),
    help="Where to output the generated project dir into",
)
@click.option(
    "--config-file", type=click.Path(), default=None, help="User configuration file"
)
@click.option(
    "--default-config",
    is_flag=True,
    help="Do not load a config file. Use the defaults instead",
)
@click.option(
    "--debug-file",
    type=click.Path(),
    default=None,
    help="File to be used as a stream for DEBUG logging",
)
@click.option(
    "--accept-hooks",
    type=click.Choice(["yes", "ask", "no"]),
    default="yes",
    help="Accept pre/post hooks",
)
@click.option(
    "-l", "--list-installed", is_flag=True, help="List currently installed templates."
)
@click.option(
    "--keep-project-on-failure",
    is_flag=True,
    help="Do not delete project folder on failure",
)
def prompt_accept_hooks(accept_hooks: str) -> bool:
    if accept_hooks == "ask":
        return click.confirm("Do you want to accept hooks?", default=True)
    return accept_hooks == "yes"

def main(
    template: Optional[str] = None,
    extra_context: List[str] = [],
    no_input: bool = False,
    checkout: Optional[str] = None,
    verbose: bool = False,
    replay: bool = False,
    overwrite_if_exists: bool = False,
    output_dir: str = ".",
    config_file: Optional[str] = None,
    default_config: bool = False,
    debug_file: Optional[str] = None,
    directory: Optional[str] = None,
    skip_if_file_exists: bool = False,
    accept_hooks: str = "yes",
    replay_file: Optional[str] = None,
    list_installed: bool = False,
    keep_project_on_failure: bool = False,
) -> None:
    accept_hooks_value = prompt_accept_hooks(accept_hooks)
    """Create a project from a Cookiecutter project template (TEMPLATE).

    Cookiecutter is free and open source software, developed and managed by
    volunteers. If you would like to help out or fund the project, please get
    in touch at https://github.com/cookiecutter/cookiecutter.
    """
    if list_installed:
        list_installed_templates(default_config, config_file)
        return

    configure_logger(
        stream_level="DEBUG" if verbose else "INFO",
        debug_file=debug_file,
    )

    try:
        if replay_file:
            replay = bool(replay_file)

        cookiecutter(
            template,
            checkout=checkout,
            no_input=no_input,
            extra_context=dict(s.split('=', 1) for s in extra_context) if extra_context else None,
            replay=replay,
            overwrite_if_exists=overwrite_if_exists,
            output_dir=output_dir,
            config_file=config_file,
            default_config=default_config,
            password=None,
            directory=directory,
            skip_if_file_exists=skip_if_file_exists,
            accept_hooks=accept_hooks_value,
            keep_project_on_failure=keep_project_on_failure,
            replay_file=replay_file,
        )
    except (CookiecutterException, RepositoryNotFound) as e:
        click.echo(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main(prog_name="cookiecutter")
