"""cookiecutter.replay.

-------------------
"""

import json
import os
from cookiecutter.utils import make_sure_path_exists


def get_file_name(replay_dir: "os.PathLike[str]", template_name: str) -> str:
    """Get the name of file."""
    file_name = f"{template_name}.json"
    return os.path.join(replay_dir, file_name)


def dump(replay_dir: "os.PathLike[str]", template_name: str, context: dict) -> None:
    """Write json data to file."""
    make_sure_path_exists(replay_dir)
    file_path = get_file_name(replay_dir, template_name)
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(context, f, indent=2)


def load(replay_dir: "os.PathLike[str]", template_name: str) -> dict | None:
    """Read json data from file."""
    file_path = get_file_name(replay_dir, template_name)
    if not os.path.exists(file_path):
        return None
    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)
