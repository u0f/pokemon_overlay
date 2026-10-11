"""Synthetic ROM tables test extraction; these are not retail ROM validation."""
import hashlib
import json
import struct
from dataclasses import replace
import pytest
from backend.app.games import GAMES
from scripts import prepare_rom


@pytest.mark.parametrize('game',[GAMES[0],GAMES[1],GAMES[-1]],ids=lambda g:g.family)
def test_catalog_tables_and_per_rom_assets(tmp_path,monkeypatch,game):
    rom=bytearray(0x14000)
    def put(at,value): struct.pack_into('<I',rom,at,value)
    def pointer(at,target): put(at,0x08000000+target)
    rom[0xAC:0xB0]=game.code.encode();rom[0xBC]=game.revision
    rom[0x108:0x110]=b'pokemon '
    layout=game.memory
    for offset,value in {0x50:layout['flags'],0x58:0x18,0x5C:layout['seen1'],0x60:layout['seen2'],0x88:layout['size2'],0x8C:layout['size1']}.items():
        put(0x100+offset,value)
    names,stats,icons,ids,palettes=0x1000,0x3000,0x6000,0x6800,0x7000
    for offset,target in {0x44:names,0xBC:stats,0x38:icons,0x3C:ids,0x40:palettes}.items(): pointer(0x100+offset,target)
    if game.family=='rs': put(0x1BC,0)
    pointer(palettes,0x7100)
    for i in range(412):
        rom[names+i*11:names+(i+1)*11]=bytes.fromhex('c0bbccc0bfcebdc2b4beff')
        rom[stats+i*28:stats+i*28+8]=bytes([30,30,30,30,30,30,12,3])
        pointer(icons+i*4,0x8000)
    rom[stats+28:stats+36]=bytes([45,49,49,45,65,65,12,3])
    rom[stats+56:stats+64]=bytes([60,62,63,60,80,80,12,3])
    rom[0xA000:0xA005]=bytes.fromhex('bbbcbdbeff')
    for i in range(game.location_count): pointer(0x9000+i*(4 if game.family=='frlg' else 8)+(0 if game.family=='frlg' else 4),0xA000)
    game=replace(game,locations=0x08009000,sha1=hashlib.sha1(rom).hexdigest())
    monkeypatch.setattr(prepare_rom,'identify',lambda *args:game)
    source=tmp_path/'sample.gba';source.write_bytes(rom)
    out=tmp_path/'data'
    report=prepare_rom.prepare(source,out)
    assert source.read_bytes()==rom and report['species_count']==386
    catalog=json.loads((out/'catalogs'/f'{game.sha1}.json').read_text('utf-8'))
    assert catalog['species']['83']['name']=='FARFETCH’D'
    assert catalog['species']['1']['types']==['Planta','Veneno']
    assert (out/'assets'/game.sha1/'1.png').exists()
    assert catalog['locations']['88' if game.family=='frlg' else '0']=='ABCD'


def test_unknown_rom_rejected_before_assets(tmp_path):
    source=tmp_path/'bad.gba';source.write_bytes(bytes(512))
    with pytest.raises(ValueError): prepare_rom.prepare(source,tmp_path/'data')
    assert not (tmp_path/'data').exists()
