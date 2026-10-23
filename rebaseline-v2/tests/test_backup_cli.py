"""CLI contract independently exercises dispatch and safe failures, no live data."""
import sys
from types import ModuleType

import pytest

from ciw2.cli import main


@pytest.fixture
def backup_api(monkeypatch):
    module=ModuleType('ciw2.store.backup')
    class BackupError(ValueError):pass
    module.BackupError=BackupError
    calls=[]
    def operation(*args):
        calls.append(args)
        return {'schema_version':'ciw2-backup-v1','files':{'ciw2.sqlite3':'0'*64}}
    module.create_backup=operation
    module.restore_backup=operation
    monkeypatch.setitem(sys.modules,'ciw2.store.backup',module)
    return module,calls


def test_backup_uses_current_data_root_without_initializing_or_migrating_it(tmp_path,monkeypatch,backup_api,capsys):
    _,calls=backup_api
    source=tmp_path/'untouched-data'
    target=tmp_path/'new-backup'
    monkeypatch.setenv('CIW_DATA_DIR',str(source))
    assert main(['backup','--output',str(target)])==0
    assert calls==[(source,target)] and not source.exists() and not target.exists()
    assert 'ciw2-backup-v1' in capsys.readouterr().out


def test_restore_uses_explicit_new_target_not_current_application_data(tmp_path,monkeypatch,backup_api):
    _,calls=backup_api
    current=tmp_path/'current'
    monkeypatch.setenv('CIW_DATA_DIR',str(current))
    source,target=tmp_path/'backup',tmp_path/'recovered'
    assert main(['restore','--input',str(source),'--output',str(target)])==0
    assert calls==[(source,target)] and not current.exists()


@pytest.mark.parametrize('command',['backup','restore'])
def test_backup_failure_is_nonzero_without_private_exception_dump(command,tmp_path,backup_api,capsys):
    module,_=backup_api
    def fail(*args):raise module.BackupError('private-token-and-file-path')
    module.create_backup=module.restore_backup=fail
    args=[command,'--output',str(tmp_path/'new')]
    if command=='restore':args+=['--input',str(tmp_path/'backup')]
    assert main(args)!=0
    error=capsys.readouterr().err
    assert error and 'private-token' not in error


def test_help_exposes_backup_and_restore_without_optional_service_start(capsys):
    with pytest.raises(SystemExit) as result:main(['--help'])
    assert result.value.code==0
    out=capsys.readouterr().out
    assert 'backup' in out and 'restore' in out
