"""Jinja2 extensions."""

import json
import string
import uuid
from secrets import choice
from typing import Any

import arrow
from jinja2 import Environment, nodes
from jinja2.ext import Extension
from slugify import slugify as pyslugify


class JsonifyExtension(Extension):
    """Jinja2 extension to convert a Python object to JSON."""

    def __init__(self, environment: Environment) -> None:
        """Initialize the extension with the given environment."""
        super().__init__(environment)

        def jsonify(obj: Any) -> str:
            return json.dumps(obj, sort_keys=True, indent=4)

        environment.filters["jsonify"] = jsonify


class RandomStringExtension(Extension):
    """Jinja2 extension to create a random string."""

    def __init__(self, environment: Environment) -> None:
        """Jinja2 Extension Constructor."""
        super().__init__(environment)

        def random_ascii_string(length: int, punctuation: bool = False) -> str:
            if punctuation:
                corpus = "".join((string.ascii_letters, string.punctuation))
            else:
                corpus = string.ascii_letters
            return "".join((choice(corpus) for _ in range(length)))

        environment.globals.update(random_ascii_string=random_ascii_string)


class SlugifyExtension(Extension):
    """Jinja2 Extension to slugify string."""

    def __init__(self, environment: Environment) -> None:
        """Jinja2 Extension constructor."""
        super().__init__(environment)

        def slugify(value: str, **kwargs: Any) -> str:
            """Slugifies the value."""
            return pyslugify(value, **kwargs)

        environment.filters["slugify"] = slugify


class UUIDExtension(Extension):
    """Jinja2 Extension to generate uuid4 string."""

    def __init__(self, environment: Environment) -> None:
        """Jinja2 Extension constructor."""
        super().__init__(environment)

        def uuid4() -> str:
            """Generate UUID4."""
            return str(uuid.uuid4())

        environment.globals.update(uuid4=uuid4)


class TimeExtension(Extension):
    """Jinja2 Extension for dates and times."""

    tags = {"now"}

    def __init__(self, environment: Environment) -> None:
        """Jinja2 Extension constructor."""
        super().__init__(environment)
        environment.extend(datetime_format="%Y-%m-%d")

    def parse(self, parser: Any) -> nodes.Node:
        """Parse datetime template and add datetime value."""
        lineno = next(parser.stream).lineno
        token = parser.stream.next()
        format_string = self.environment.datetime_format
        if token.type == "string":
            format_string = token.value

        node = nodes.Call(
            self.attr("_render_now"), [nodes.Const(format_string)], [], None, None
        )
        return nodes.Output([node]).set_lineno(lineno)

    def _render_now(self, format_string: str) -> str:
        return arrow.now().format(format_string)
