"""Official unchanged assets must work through normal and self-contained rendering."""
import base64
import hashlib
import json
from pathlib import Path

from ciw2.render.portal import render_report
from ciw2.service import Service

STATIC = Path(__file__).resolve().parents[1] / 'src/ciw2/render/static'


def test_shipped_brand_assets_match_the_registered_skill_input():
    manifest = json.loads((STATIC / 'kangzhe-assets.json').read_text())
    assert manifest['version'] == '7.1.1'
    assert manifest['files']['logo_bot.svg'] == '8d16d3ae8353dd31f46a50d401e66f9e62af40be6cc42cdf5050866a4e6e1cae'
    for file, digest in manifest['files'].items():
        assert hashlib.sha256((STATIC / file).read_bytes()).hexdigest() == digest


def test_ordinary_and_inline_reports_have_one_brand_field_and_one_motion_owner(settings):
    svc = Service(settings)
    pid = svc.create_project('品牌集成核验', list('ABC'))
    for inline in (False, True):
        html = render_report(svc.db, pid, 'C', inline=inline)
        assert html.count('class="kz-optical-field"') == 1
        assert html.count('alt="康哲药业"') == 1
        if inline:
            assert 'src="/static/' not in html and 'href="/static/' not in html
            assert 'KZMotion.mountField' in html and 'KZMotion.mountTilt' in html
            payload = html.split('src="data:image/svg+xml;base64,')[1].split('"', 1)[0]
            assert base64.b64decode(payload) == (STATIC / 'logo_bot.svg').read_bytes()
        else:
            assert 'src="/static/kz-site.js"' in html
            assert 'href="/static/kz-tokens.css"' in html
            assert 'src="/static/logo_bot.svg"' in html
