from pathlib import Path

from test_portal_js import run_portal


def test_common_event_window_is_once_in_definition_not_each_axis_label():
    run_portal((Path(__file__).parent / 'fixtures/result-shared-window.js').read_text())
