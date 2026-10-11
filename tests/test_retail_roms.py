"""Optional integration test against the user's local ROMs (never distributed)."""
import json
from pathlib import Path
import pytest
from scripts.prepare_rom import prepare


ROMS=sorted(Path('roms').glob('*.gba'))


@pytest.mark.parametrize('rom',ROMS or [None],ids=lambda p:p.stem if p else 'no-local-roms')
def test_user_rom_catalog(rom,tmp_path):
    if rom is None: pytest.skip('No user ROMs supplied')
    result=prepare(rom,tmp_path)
    catalog=json.loads((tmp_path/'catalogs'/f"{result['sha1']}.json").read_text('utf-8'))
    assert catalog['species']['1']['name']=='BULBASAUR'
    assert catalog['species']['1']['types']==['Planta','Veneno']
    assert catalog['species']['25']['name']=='PIKACHU'
    assert len(list((tmp_path/'assets'/result['sha1']).glob('*.png')))==386
    assert all('�' not in name for name in catalog['locations'].values())
    assert catalog['locations']['88' if result['code'] in ('BPRS','BPGS') else '0']==('PUEBLO PALETA' if result['code'] in ('BPRS','BPGS') else 'VILLA RAÍZ')
