"""Utility functions for handling and fetching repo archives in zip format."""

import os
import tempfile
import shutil
from pathlib import Path
from typing import Optional
from zipfile import BadZipFile, ZipFile
import requests
from cookiecutter.exceptions import InvalidZipRepository


def unzip(
    zip_uri: str,
    is_url: bool,
    clone_to_dir: "os.PathLike[str]" = ".",
    no_input: bool = False,
    password: Optional[str] = None,
):
    """Download and unpack a zipfile at a given URI.

    This will download the zipfile to the cookiecutter repository,
    and unpack into a temporary directory.

    :param zip_uri: The URI for the zipfile.
    :param is_url: Is the zip URI a URL or a file?
    :param clone_to_dir: The cookiecutter repository directory
        to put the archive into.
    :param no_input: Do not prompt for user input and eventually force a refresh of
        cached resources.
    :param password: The password to use when unpacking the repository.
    """
    clone_to_dir = Path(clone_to_dir)
    if is_url:
        # Download the file
        response = requests.get(zip_uri)
        response.raise_for_status()
        zip_file = clone_to_dir / "template.zip"
        zip_file.write_bytes(response.content)
    else:
        zip_file = Path(zip_uri)

    # Create a temporary directory to extract the contents
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_dir_path = Path(temp_dir)

        try:
            with ZipFile(zip_file) as zf:
                if password:
                    zf.setpassword(password.encode())
                zf.extractall(temp_dir_path)
        except BadZipFile:
            raise InvalidZipRepository(f"The file {zip_file} is not a valid zip file.")

        # If the zip file contains a single directory, use that as the root
        contents = list(temp_dir_path.iterdir())
        if len(contents) == 1 and contents[0].is_dir():
            extracted_dir = contents[0]
        else:
            extracted_dir = temp_dir_path

        # Move the extracted contents to the clone_to_dir
        for item in extracted_dir.iterdir():
            shutil.move(str(item), str(clone_to_dir))

    # Clean up the downloaded zip file if it was from a URL
    if is_url:
        zip_file.unlink()

    return clone_to_dir
