import os
import pathlib
from typing import Optional


def get_chromium_executable() -> str:
    """Return the path to the Playwright Chromium executable.

    The function first checks the ``PLAYWRIGHT_EXECUTABLE_PATH`` environment
    variable. If that points to an existing file it is returned. Otherwise the
    default Playwright install location under ``%LOCALAPPDATA%\ms-playwright``
    is inspected and the first ``chromium-`` folder that contains
    ``chrome-win64\chrome.exe`` is used.

    Raises:
        FileNotFoundError: If no executable can be found. The caller should
            surface a clear error message (e.g. instruct the user to run
            ``playwright install chromium``).
    """
    env_path = os.getenv("PLAYWRIGHT_EXECUTABLE_PATH")
    if env_path and os.path.isfile(env_path):
        return env_path

    # Default Playwright install location on Windows
    local_app_data = os.getenv("LOCALAPPDATA", "")
    base_path = pathlib.Path(local_app_data) / "ms-playwright"
    if not base_path.is_dir():
        raise FileNotFoundError(
            "Playwright install directory not found. Run `playwright install chromium` or set PLAYWRIGHT_EXECUTABLE_PATH."
        )

    for child in base_path.iterdir():
        if child.is_dir() and child.name.startswith("chromium-"):
            exe = child / "chrome-win64" / "chrome.exe"
            if exe.is_file():
                return str(exe)

    raise FileNotFoundError(
        "Chromium executable not found in Playwright installation. Install via `playwright install chromium` or set PLAYWRIGHT_EXECUTABLE_PATH."
    )
