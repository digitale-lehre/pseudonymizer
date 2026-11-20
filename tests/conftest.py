import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))


@pytest.fixture(autouse=True)
def _cleanup_zip_temp_dirs():
    """Aus ZIP-Eingaben entpackte Klartextdateien nach jedem Test loeschen."""
    yield
    import pseudonym
    cleanup = getattr(pseudonym, "cleanup_temp_dirs", None)
    if cleanup:
        cleanup()
