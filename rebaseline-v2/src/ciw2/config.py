"""运行配置。全部来自环境变量，便于单机部署；不在任何文件中保存密钥。"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path


def _env(name: str, default: str = "") -> str:
    return os.environ.get(name, default).strip()


def _ego_space() -> int | None:
    value = _env('CIW_CHINA_EGO_SPACE_ID')
    if not value:
        return None
    if not value.isdecimal() or int(value) <= 0:
        raise ValueError('CIW_CHINA_EGO_SPACE_ID 必须为专用浏览器空间的正整数ID')
    return int(value)


_PACKAGE_DIR = Path(__file__).resolve().parent


def _default_skills_dir(package_dir: Path = _PACKAGE_DIR) -> Path:
    """安装包优先使用构建时嵌入的副本；可编辑检出回退到仓库 skills。"""
    embedded = package_dir / "skills"
    if any(embedded.glob("*/SKILL.md")):
        return embedded
    return package_dir.parents[1] / "skills"


def _skills_dir() -> Path:
    raw = os.environ.get("CIW_SKILLS_DIR")
    if raw is not None:
        return Path(raw.strip())
    return _default_skills_dir(_PACKAGE_DIR)


@dataclass(frozen=True)
class Settings:
    data_dir: Path = field(default_factory=lambda: Path(_env("CIW_DATA_DIR", "./ciw-data")).resolve())
    skills_dir: Path = field(default_factory=_skills_dir)
    # OpenAI 兼容接口：DeepSeek / GLM / Qwen / OpenAI 等均可。
    llm_base_url: str = field(default_factory=lambda: _env("CIW_LLM_BASE_URL", "http://127.0.0.1:20128/v1"))
    llm_api_key: str = field(default_factory=lambda: _env("CIW_LLM_API_KEY"), repr=False)
    llm_model: str = field(default_factory=lambda: _env("CIW_LLM_MODEL", "glm-5.3-flash"))
    llm_fallbacks: str = field(default_factory=lambda: _env('CIW_LLM_FALLBACKS', '[]'))
    # 关键字段二次核对使用的模型（可与主模型相同；留空则只做确定性原文核验）。
    llm_check_model: str = field(default_factory=lambda: _env("CIW_LLM_CHECK_MODEL"))
    # 全网搜索提供方：tavily | bing | serpapi | none
    websearch_provider: str = field(default_factory=lambda: _env("CIW_WEBSEARCH_PROVIDER", "none"))
    websearch_api_key: str = field(default_factory=lambda: _env("CIW_WEBSEARCH_API_KEY"))
    china_ego_space_id: int | None = field(default_factory=_ego_space)
    china_browser_timeout_s: float = field(default_factory=lambda: float(_env('CIW_CHINA_BROWSER_TIMEOUT_S', '240')))
    # 微信公众号搜索 Skill 的外部命令，例如 "python /opt/wechat-search/search.py"；留空则禁用。
    wechat_search_cmd: str = field(default_factory=lambda: _env("CIW_WECHAT_SEARCH_CMD"))
    ncbi_api_key: str = field(default_factory=lambda: _env("CIW_NCBI_API_KEY"))
    http_timeout_s: float = float(_env("CIW_HTTP_TIMEOUT_S", "30") or 30)
    max_agent_steps: int = int(_env("CIW_MAX_AGENT_STEPS", "24") or 24)

    @property
    def db_path(self) -> Path:
        return self.data_dir / "ciw2.sqlite3"

    @property
    def cas_dir(self) -> Path:
        return self.data_dir / "cas"

    @property
    def portals_dir(self) -> Path:
        return self.data_dir / "portals"

    def ensure_dirs(self) -> None:
        for p in (self.data_dir, self.cas_dir, self.portals_dir):
            p.mkdir(parents=True, exist_ok=True)


def get_settings() -> Settings:
    s = Settings()
    s.ensure_dirs()
    return s
