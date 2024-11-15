"""Functions for prompting the user for project info."""

import json
import os
import sys
from collections import OrderedDict
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from jinja2.exceptions import UndefinedError
from rich.prompt import Confirm, InvalidResponse, Prompt, PromptBase
from typing import cast
from cookiecutter.exceptions import UndefinedVariableInTemplate
from cookiecutter.utils import create_env_with_context, rmtree


def read_user_variable(
    var_name: str,
    default_value: Any,
    prompts: Optional[Dict[str, str]] = None,
    prefix: str = "",
) -> str:
    """Prompt user for variable and return the entered value or given default.

    :param str var_name: Variable of the context to query the user
    :param default_value: Value that will be returned if no input happens
    """
    prompt_text = f"{prefix}{var_name}"
    if prompts and var_name in prompts:
        prompt_text = prompts[var_name]

    return Prompt.ask(prompt_text, default=str(default_value))


class YesNoPrompt(Confirm):
    """A prompt that returns a boolean for yes/no questions."""

    yes_choices = ["1", "true", "t", "yes", "y", "on"]
    no_choices = ["0", "false", "f", "no", "n", "off"]

    def process_response(self, value: str) -> bool:
        """Convert choices to a bool."""
        value = value.lower()
        if value in self.yes_choices:
            return True
        if value in self.no_choices:
            return False
        raise InvalidResponse(self.validate_error_message)


def read_user_yes_no(
    var_name: str,
    default_value: bool,
    prompts: Optional[Dict[str, str]] = None,
    prefix: str = "",
) -> bool:
    """Prompt the user to reply with 'yes' or 'no' (or equivalent values).

    - These input values will be converted to ``True``:
      "1", "true", "t", "yes", "y", "on"
    - These input values will be converted to ``False``:
      "0", "false", "f", "no", "n", "off"

    Actual parsing done by :func:`prompt`; Check this function codebase change in
    case of unexpected behaviour.

    :param str question: Question to the user
    :param default_value: Value that will be returned if no input happens
    """
    prompt_text = f"{prefix}{var_name}"
    if prompts and var_name in prompts:
        prompt_text = prompts[var_name]

    return YesNoPrompt.ask(prompt_text, default=default_value)


def read_repo_password(question: str) -> str:
    """Prompt the user to enter a password.

    :param str question: Question to the user
    """
    return Prompt.ask(question, password=True)


def read_user_choice(
    var_name: str,
    options: List[str],
    prompts: Optional[Dict[str, str]] = None,
    prefix: str = "",
) -> str:
    """Prompt the user to choose from several options for the given variable.

    The first item will be returned if no input happens.

    :param str var_name: Variable as specified in the context
    :param list options: Sequence of options that are available to select from
    :return: Exactly one item of ``options`` that has been chosen by the user
    """
    prompt_text = f"{prefix}{var_name}"
    if prompts and var_name in prompts:
        prompt_text = prompts[var_name]

    choices = [str(choice) for choice in options]
    return Prompt.ask(prompt_text, choices=choices, default=choices[0])


DEFAULT_DISPLAY = "default"


def process_json(user_value: str, default_value: Any = None) -> Any:
    """Load user-supplied value as a JSON dict.

    :param str user_value: User-supplied value to load as a JSON dict
    """
    try:
        return json.loads(user_value)
    except json.JSONDecodeError:
        return default_value


class JsonPrompt(PromptBase[dict]):
    """A prompt that returns a dict from JSON string."""

    default = None
    response_type = dict
    validate_error_message = "[prompt.invalid]  Please enter a valid JSON string"

    def process_response(self, value: str) -> dict:
        """Convert choices to a dict."""
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            raise InvalidResponse(self.validate_error_message)


def read_user_dict(
    var_name: str,
    default_value: Dict[str, Any],
    prompts: Optional[Dict[str, str]] = None,
    prefix: str = "",
) -> Dict[str, Any]:
    """Prompt the user to provide a dictionary of data.

    :param str var_name: Variable as specified in the context
    :param default_value: Value that will be returned if no input is provided
    :return: A Python dictionary to use in the context.
    """
    prompt_text = f"{prefix}{var_name}"
    if prompts and var_name in prompts:
        prompt_text = prompts[var_name]

    default_json = json.dumps(default_value)
    return JsonPrompt.ask(prompt_text, default=default_json)


def render_variable(env: Any, raw: str, cookiecutter_dict: Dict[str, Any]) -> str:
    """Render the next variable to be displayed in the user prompt.

    Inside the prompting taken from the cookiecutter.json file, this renders
    the next variable. For example, if a project_name is "Peanut Butter
    Cookie", the repo_name could be be rendered with:

        `{{ cookiecutter.project_name.replace(" ", "_") }}`.

    This is then presented to the user as the default.

    :param Environment env: A Jinja2 Environment object.
    :param raw: The next value to be prompted for by the user.
    :param dict cookiecutter_dict: The current context as it's gradually
        being populated with variables.
    :return: The rendered value for the default variable.
    """
    try:
        template = env.from_string(raw)
        return template.render(**cookiecutter_dict)
    except UndefinedError as err:
        raise UndefinedVariableInTemplate(str(err), err, cookiecutter_dict)


def _prompts_from_options(options: dict) -> dict:
    """Process template options and return friendly prompt information."""
    prompts = {}
    for key, value in options.items():
        if isinstance(value, dict):
            prompts[key] = value.get("_prompt", key)
        else:
            prompts[key] = key
    return prompts


def prompt_choice_for_template(
    key: str, options: Dict[str, Any], no_input: bool
) -> str:
    """Prompt user with a set of options to choose from.

    :param no_input: Do not prompt for user input and return the first available option.
    """
    if no_input:
        return next(iter(options.keys()))

    prompts = _prompts_from_options(options)
    choices = list(options.keys())
    return read_user_choice(key, choices, prompts=prompts)


def prompt_choice_for_config(
    cookiecutter_dict: Dict[str, Any],
    env: Any,
    key: str,
    options: List[str],
    no_input: bool,
    prompts: Optional[Dict[str, str]] = None,
    prefix: str = "",
) -> str:
    """Prompt user with a set of options to choose from.

    :param no_input: Do not prompt for user input and return the first available option.
    """
    if no_input:
        return options[0]

    rendered_options = [
        render_variable(env, option, cookiecutter_dict) for option in options
    ]
    return read_user_choice(key, rendered_options, prompts=prompts, prefix=prefix)


def prompt_for_config(
    context: Dict[str, Any], no_input: bool = False
) -> Dict[str, Any]:
    """Prompt user to enter a new config.

    :param dict context: Source for field names and sample values.
    :param no_input: Do not prompt for user input and use only values from context.
    """
    cookiecutter_dict = OrderedDict([])
    env = create_env_with_context(context)

    for key, raw in context["cookiecutter"].items():
        if key.startswith("_"):
            cookiecutter_dict[key] = raw
            continue

        if isinstance(raw, list):
            val = prompt_choice_for_config(
                cookiecutter_dict,
                env,
                key,
                raw,
                no_input,
                prompts=context.get("prompts", {}),
                prefix=context.get("prefix", ""),
            )
        elif isinstance(raw, dict):
            val = prompt_choice_for_template(key, raw, no_input)
        else:
            val = render_variable(env, raw, cookiecutter_dict)

        if not no_input:
            if isinstance(raw, bool):
                val = read_user_yes_no(key, bool(val))
            elif isinstance(raw, dict):
                val = read_user_dict(key, val if isinstance(val, dict) else {})
            else:
                val = read_user_variable(key, val)

        cookiecutter_dict[key] = val

    return cookiecutter_dict


def choose_nested_template(context: dict, repo_dir: str, no_input: bool = False) -> str:
    """Prompt user to select the nested template to use.

    :param context: Source for field names and sample values.
    :param repo_dir: Repository directory.
    :param no_input: Do not prompt for user input and use only values from context.
    :returns: Path to the selected template.
    """
    template_options = context["cookiecutter"].get("_templates", {})
    if not template_options:
        return cast(str, repo_dir)

    if no_input:
        return os.path.join(repo_dir, next(iter(template_options.values())))

    choice = prompt_choice_for_template("_templates", template_options, no_input)
    return os.path.join(repo_dir, template_options[choice])


def prompt_and_delete(path: Union[str, Path], no_input: bool = False) -> bool:
    """Ask user if it's okay to delete the previously-downloaded file/directory.

    If yes, delete it. If no, checks to see if the old version should be
    reused. If yes, it's reused; otherwise, Cookiecutter exits.

    :param path: Previously downloaded zipfile.
    :param no_input: Suppress prompt to delete repo and just delete it.
    :return: True if the content was deleted
    """
    if no_input:
        rmtree(path)
        return True

    delete = read_user_yes_no(
        f"You've downloaded {path} before. Is it okay to delete and re-download it?",
        True,
    )

    if delete:
        rmtree(path)
        return True

    reuse = read_user_yes_no("Do you want to re-use the existing version?", True)

    if reuse:
        return False

    sys.exit()
