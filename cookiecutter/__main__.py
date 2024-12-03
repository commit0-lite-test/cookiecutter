"""Allow cookiecutter to be executable through `python -m cookiecutter`."""

from cookiecutter.cli import main
import click

if __name__ == "__main__":  # pragma: no cover
    main.main(standalone_mode=False)
