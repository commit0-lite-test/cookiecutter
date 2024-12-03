"""Test cookiecutter invocation with nested configuration structure."""

from pathlib import Path

import pytest
from unittest.mock import patch

from cookiecutter import main
from cookiecutter.generate import generate_files


@pytest.mark.parametrize(
    "template_dir,output_dir",
    [
        ["fake-nested-templates", "fake-project"],
        ["fake-nested-templates-old-style", "fake-package"],
    ],
)
@patch('cookiecutter.main.generate_files')
def test_cookiecutter_nested_templates(mock_generate_files, template_dir: str, output_dir: str):
    """Verify cookiecutter nested configuration files mechanism."""
    main_dir = (Path("tests") / template_dir).resolve()
    main.cookiecutter(f"{main_dir}", no_input=True)
    expected = (Path(main_dir) / output_dir).resolve()
    assert mock_generate_files.call_args[1]["repo_dir"] == f"{expected}"
