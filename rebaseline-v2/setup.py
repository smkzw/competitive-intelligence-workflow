"""构建钩子：仅把作者维护的 skills/*/SKILL.md 嵌入 ciw2 包数据。

源码树不保留副本；可编辑安装与源码运行仍使用仓库根目录的 skills。
"""

from __future__ import annotations

import shutil
from pathlib import Path

from setuptools import setup
from setuptools.command.build_py import build_py as _build_py
from setuptools.command.sdist import sdist as _sdist

PROJECT_ROOT = Path(__file__).resolve().parent
AUTHOR_SKILLS = PROJECT_ROOT / "skills"


def _author_skills() -> list[Path]:
    sources=sorted(AUTHOR_SKILLS.glob("*/SKILL.md"))
    if not sources or AUTHOR_SKILLS.is_symlink() or any(
            source.is_symlink() or source.parent.is_symlink() or not source.is_file() for source in sources):
        raise RuntimeError("作者 Skill 缺失或包含符号链接")
    return sources


class BuildPy(_build_py):
    def run(self) -> None:
        sources = _author_skills()
        target = Path(self.build_lib) / "ciw2" / "skills"
        if any(path.is_symlink() for path in (target,*target.parents)) or (target.exists() and not target.is_dir()):
            raise RuntimeError("构建目录包含符号链接或不是目录，请选择新的构建目录")
        expected={Path(source.parent.name)/'SKILL.md' for source in sources}
        if any(path.is_symlink() or (not path.is_dir() and path.relative_to(target) not in expected)
               for path in target.rglob('*')):
            raise RuntimeError("构建目录包含非当前 Skill 文件，请选择新的构建目录")
        super().run()
        for source in sources:
            destination = target / source.parent.name / "SKILL.md"
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, destination)


class SDist(_sdist):
    def make_distribution(self) -> None:
        for source in _author_skills():
            self.filelist.append(source.relative_to(PROJECT_ROOT).as_posix())
        super().make_distribution()


setup(cmdclass={"build_py": BuildPy, "sdist": SDist})
