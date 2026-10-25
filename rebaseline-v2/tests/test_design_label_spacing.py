"""Production ECharts layout uses full measured labels on initial and filtered views."""
import shutil
import subprocess
from pathlib import Path

import pytest


def test_full_design_labels_have_real_row_space_after_filtering():
    node = shutil.which('node')
    if not node:
        pytest.skip('Node unavailable')
    tests = Path(__file__).parent
    source = tests.parent / 'src/ciw2/render/static/portal.js'
    result = subprocess.run([node, str(tests / 'fixtures/design-label-spacing.js'), str(source)],
                            capture_output=True, text=True, check=False)
    assert result.returncode == 0, result.stderr
