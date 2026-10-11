import zipfile
import pytest
from scripts.export_source import FILES,export


def prepare(root):
    for name in FILES:
        path=root/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_text('','utf-8')


def test_public_archive_excludes_user_data_and_builds(tmp_path):
    prepare(tmp_path)
    for name in ('data/private.json','roms/game.gba','roms/game.sav','research/notes.md',
                 'frontend/dist/bundle.js','frontend/node_modules/package/index.ts',
                 'backend/__pycache__/private.py','.env','bridge/mgba/old.lua.bak'):
        path=tmp_path/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(b'private')
    with zipfile.ZipFile(export(tmp_path)) as archive:
        assert set(archive.namelist())==set(FILES)
        assert 'frontend/index.html' in archive.namelist()
    assert (tmp_path/'roms/game.sav').read_bytes()==b'private'


def test_public_archive_rejects_personal_paths(tmp_path):
    prepare(tmp_path)
    (tmp_path/'README.md').write_text('C:'+ '/Users/example/private','utf-8')
    with pytest.raises(ValueError,match='README'): export(tmp_path)
