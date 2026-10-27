import json

import pytest

from ciw.sources.document import capture_document


@pytest.mark.parametrize("kind,host,publisher", [
    ("company", "example.com", ""), ("wechat", "mp.weixin.qq.com", "医药魔方Info")])
def test_visible_article_to_content_keyed_inbox(cfg, ws, monkeypatch, kind, host, publisher):
    url = f"https://{host}/article"
    body = "鼻息肉试验结果。" * 40
    doc = dict(url=url, title="研究结果", text=body, publisher=publisher,
               published_at="2026-10-27T08:00:00Z", fetched_at="2026-10-27T09:00:00Z")
    monkeypatch.setattr("ciw.sources.document.run_script", lambda *a, **k: ([doc], {"status": "ok"}))
    result = capture_document(ws, cfg, 40, url, kind)
    assert result["status"] == "ok"
    path = ws.root / "captures/docs" / result["file"]
    assert path.read_text() == body
    meta = json.loads(path.with_name(path.name + ".meta.json").read_text())
    assert meta["url"] == url and meta["published_at"] == "2026-10-27"
    assert capture_document(ws, cfg, 40, url, kind)["file"] == path.name


def test_capture_rejects_wrong_account_and_unrelated_or_blocked_body(cfg, ws, monkeypatch):
    doc = dict(url="https://mp.weixin.qq.com/s/x", title="文章", text="鼻息肉" * 100,
               publisher="其他账号", fetched_at="2026-10-27T09:00:00Z")
    monkeypatch.setattr("ciw.sources.document.run_script", lambda *a, **k: ([doc], {"status": "ok"}))
    assert capture_document(ws, cfg, 40, doc["url"], "wechat")["status"] == "not_adopted"
    doc["publisher"], doc["text"] = "医药魔方Info", "请完成验证"
    assert capture_document(ws, cfg, 40, doc["url"], "wechat")["status"] == "not_adopted"
    assert not (ws.root / "captures/docs").exists()
    with pytest.raises(ValueError):
        capture_document(ws, cfg, 40, "https://user:password@example.com/", "company")
