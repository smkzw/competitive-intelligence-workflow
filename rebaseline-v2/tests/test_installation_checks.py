"""Build-resource safety and the existing CLI preflight; all adversarial paths are temporary."""
import runpy
import sys
from pathlib import Path
from types import ModuleType

import pytest

from ciw2.cli import main


def build_hook(monkeypatch,tmp_path):
    class Build:
        def run(self):pass
    modules={name:ModuleType(name) for name in (
        'setuptools','setuptools.command','setuptools.command.build_py','setuptools.command.sdist')}
    modules['setuptools'].setup=lambda **_:None
    modules['setuptools.command.build_py'].build_py=Build
    modules['setuptools.command.sdist'].sdist=object
    for name,module in modules.items():monkeypatch.setitem(sys.modules,name,module)
    namespace=runpy.run_path(str(Path(__file__).parents[1]/'setup.py'))
    hook=namespace['BuildPy']()
    hook.build_lib=str(tmp_path/'build')
    author=tmp_path/'authors';(author/'intake').mkdir(parents=True)
    (author/'intake/SKILL.md').write_text('author bytes')
    hook.run.__globals__['AUTHOR_SKILLS']=author
    return hook,author,tmp_path/'build/ciw2/skills'


def test_build_rejects_a_symlink_destination_without_overwriting_external_data(monkeypatch,tmp_path):
    hook,_,target=build_hook(monkeypatch,tmp_path)
    external=tmp_path/'external';(external/'intake').mkdir(parents=True)
    marker=external/'intake/SKILL.md';marker.write_text('unrelated original')
    target.parent.mkdir(parents=True);target.symlink_to(external,target_is_directory=True)
    with pytest.raises(RuntimeError):hook.run()
    assert marker.read_text()=='unrelated original'


@pytest.mark.parametrize('linked',['file','directory'])
def test_build_rejects_external_author_symlinks(monkeypatch,tmp_path,linked):
    hook,author,_=build_hook(monkeypatch,tmp_path)
    external=tmp_path/'secret';external.write_text('private bytes')
    source=author/'intake/SKILL.md';source.unlink()
    if linked=='file':source.symlink_to(external)
    else:
        source.parent.rmdir()
        directory=tmp_path/'elsewhere';directory.mkdir()
        (directory/'SKILL.md').write_text('private bytes')
        (author/'intake').symlink_to(directory,target_is_directory=True)
    with pytest.raises(RuntimeError):hook.run()


def test_build_rejects_stale_unexpected_files_instead_of_recursively_deleting_them(monkeypatch,tmp_path):
    hook,_,target=build_hook(monkeypatch,tmp_path)
    target.mkdir(parents=True)
    marker=target/'private.log';marker.write_text('retain me')
    with pytest.raises(RuntimeError):hook.run()
    assert marker.read_text()=='retain me'


def test_empty_explicit_skill_directory_fails_preflight_without_creating_data(monkeypatch,tmp_path,capsys):
    data=tmp_path/'not-created'
    monkeypatch.setenv('CIW_DATA_DIR',str(data))
    monkeypatch.setenv('CIW_SKILLS_DIR',str(tmp_path/'missing'))
    assert main(['skills'])==2
    assert 'CIW_SKILLS_DIR' in capsys.readouterr().err
    assert not data.exists()
