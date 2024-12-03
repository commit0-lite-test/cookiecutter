"""Jinja2 environment and extensions loading."""

from typing import Any, Dict, List

try:
    from jinja2 import Environment, StrictUndefined
except ImportError:
    print(
        "Error: jinja2 is not installed. Please install it using 'pip install jinja2'"
    )
    # You might want to raise an exception here instead of just printing
    # raise ImportError("jinja2 is not installed")

from cookiecutter.exceptions import UnknownExtension


class ExtensionLoaderMixin:
    """Mixin providing sane loading of extensions specified in a given context.

    The context is being extracted from the keyword arguments before calling
    the next parent class in line of the child.
    """

    def __init__(self, **kwargs: Any) -> None:
        """Initialize the Jinja2 Environment object while loading extensions.

        Does the following:

        1. Establishes default_extensions (currently just a Time feature)
        2. Reads extensions set in the cookiecutter.json _extensions key.
        3. Attempts to load the extensions. Provides useful error if fails.
        """
        context = kwargs.pop("context", {})
        default_extensions = [
            "cookiecutter.extensions.JsonifyExtension",
            "cookiecutter.extensions.RandomStringExtension",
            "cookiecutter.extensions.SlugifyExtension",
            "cookiecutter.extensions.TimeExtension",
            "cookiecutter.extensions.UUIDExtension",
        ]
        extensions = default_extensions + self._read_extensions(context)
        kwargs['extensions'] = extensions
        try:
            super().__init__(**kwargs)
            self.extensions = {ext.__name__: ext for ext in self.extensions}
        except ImportError as err:
            raise UnknownExtension(f"Unable to load extension: {err}") from err

    def _read_extensions(self, context: Dict[str, Any]) -> List[str]:
        """Return list of extensions as str to be passed on to the Jinja2 env.

        If context does not contain the relevant info, return an empty
        list instead.
        """
        extensions = context.get("cookiecutter", {}).get("_extensions", [])
        return [str(ext) for ext in extensions]


class StrictEnvironment(ExtensionLoaderMixin, Environment):
    """Create strict Jinja2 environment.

    Jinja2 environment will raise error on undefined variable in template-
    rendering context.
    """

    def __init__(self, **kwargs: Any) -> None:
        """Set the standard Cookiecutter StrictEnvironment.

        Also loading extensions defined in cookiecutter.json's _extensions key.
        """
        super().__init__(undefined=StrictUndefined, **kwargs)
        self.extensions = {}  # Initialize extensions as a dictionary

    def iter_extensions(self):
        """Iterates over the extensions by priority."""
        return iter(sorted(self.extensions.values(), key=lambda x: x.priority))
