"""默认 Skill 资源解析：安装包内嵌副本、可编辑检出回退与显式覆盖。"""

from __future__ import annotations

from pathlib import Path

from ciw2 import config as ciw2_config

ROOT = Path(__file__).resolve().parents[1]
EXPECTED_SKILLS = {
    "analysis-a",
    "analysis-b",
    "analysis-c",
    "coverage-review",
    "extract-design",
    "extract-results",
    "intake",
    "universe-china",
    "universe-global",
}


def _write_skill(root: Path, name: str) -> None:
    path = root / name / "SKILL.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"---\nname: {name}\ndescription: d\n---\n正文\n", encoding="utf-8")


def test_installed_package_uses_own_embedded_skills(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.delenv("CIW_SKILLS_DIR", raising=False)
    package = tmp_path / "site-packages" / "ciw2"
    embedded = package / "skills"
    _write_skill(embedded, "intake")
    _write_skill(embedded, "analysis-a")

    assert ciw2_config._default_skills_dir(package) == embedded


def test_editable_checkout_uses_repository_skills(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.delenv("CIW_SKILLS_DIR", raising=False)
    package = tmp_path / "repo" / "src" / "ciw2"
    package.mkdir(parents=True)

    assert ciw2_config._default_skills_dir(package) == tmp_path / "repo" / "skills"


def test_empty_embedded_dir_falls_back_to_checkout_skills(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.delenv("CIW_SKILLS_DIR", raising=False)
    package = tmp_path / "repo" / "src" / "ciw2"
    (package / "skills").mkdir(parents=True)

    assert ciw2_config._default_skills_dir(package) == tmp_path / "repo" / "skills"


def test_explicit_override_keeps_highest_priority_even_for_invalid_path(monkeypatch, tmp_path: Path) -> None:
    missing = tmp_path / "missing-skills"
    monkeypatch.setenv("CIW_SKILLS_DIR", str(missing))

    assert ciw2_config.Settings().skills_dir == missing


def test_settings_default_uses_embedded_package_skills(monkeypatch, tmp_path: Path) -> None:
    package = tmp_path / "site-packages" / "ciw2"
    embedded = package / "skills"
    _write_skill(embedded, "intake")
    monkeypatch.delenv("CIW_SKILLS_DIR", raising=False)
    monkeypatch.setattr(ciw2_config, "_PACKAGE_DIR", package)

    assert ciw2_config.Settings().skills_dir == embedded


def test_explicit_override_wins_over_embedded_package_skills(monkeypatch, tmp_path: Path) -> None:
    package = tmp_path / "site-packages" / "ciw2"
    _write_skill(package / "skills", "intake")
    missing = tmp_path / "missing-skills"
    monkeypatch.setattr(ciw2_config, "_PACKAGE_DIR", package)
    monkeypatch.setenv("CIW_SKILLS_DIR", str(missing))

    assert ciw2_config.Settings().skills_dir == missing


def test_default_settings_are_cwd_independent_and_load_the_nine_author_skills(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.delenv("CIW_SKILLS_DIR", raising=False)
    monkeypatch.chdir(tmp_path)

    from ciw2.harness.skills import load_skills

    settings = ciw2_config.Settings()
    assert settings.skills_dir == ROOT / "skills"
    skills = load_skills(settings.skills_dir)
    assert set(skills) == EXPECTED_SKILLS
    assert all(skill.output is not None for skill in skills.values())
