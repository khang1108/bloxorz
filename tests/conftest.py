"""Use real Ursina entities and a software offscreen renderer in UI tests."""

import pytest
from panda3d.core import loadPrcFileData

loadPrcFileData('', (
    'audio-library-name null\nload-display p3tinydisplay\n'
    'notify-level error\nmodel-cache-dir /tmp/bloxorz-test-cache'
))

from ursina import Ursina, application  # noqa: E402


@pytest.fixture(scope='session')
def engine():
    app = Ursina(window_type='offscreen', size=(1280, 720), development_mode=False)
    # GraphicsBuffer has no OS window properties; keep the real rendering camera.
    application.window_type = 'none'
    return app


@pytest.fixture
def game_app(engine):
    from bloxorz.main import BloxorzApp
    app = BloxorzApp()
    app.sound_mgr.enabled = False
    yield app
    app.stop_solution()
