import json
import struct
from pathlib import Path
import pytest
from backend.app.games import GAMES, identify
from backend.app.decoder import Gen3Decoder
from backend.app.events import EventEngine
from tests.test_decoder import packet
from scripts.sync_bridge_profiles import table


def game_packet(game):
    p=packet()
    p.code, p.revision, p.crc32=game.code,game.revision,game.crc32
    money=bytearray(game.memory['money']+4)
    key=0 if game.family=='rs' else 0xAABBCCDD
    struct.pack_into('<I',money,game.memory['money'],3000^key)
    p.save1=money.hex()
    p.money_key=key
    flags=bytearray(300); badge=game.memory['badge']
    flags[badge//8]=1<<(badge%8)
    p.flags=flags.hex()
    return p


@pytest.mark.parametrize('game',GAMES,ids=lambda g:g.id)
def test_game_layout_and_identity(tmp_path,game):
    decoder=Gen3Decoder(tmp_path)
    p=game_packet(game)
    s=decoder.decode(p)
    assert (s.game_id,s.rom_id,s.revision)==(game.id,game.sha1,game.revision)
    assert s.money==3000 and s.badges==[True]+[False]*7
    assert s.seen==2 and s.caught==1 and s.play_seconds==7380
    assert s.party[0].species_id==277
    p.ready=False
    assert decoder.decode(p).game_id==game.id
    p.crc32='00000000'
    with pytest.raises(ValueError,match='ROM'): decoder.decode(p)


def test_catalog_isolation_reload_and_game_switch(tmp_path):
    catalogs=tmp_path/'catalogs'; catalogs.mkdir()
    decoder=Gen3Decoder(tmp_path); engine=EventEngine()
    a=decoder.decode(game_packet(GAMES[0])); assert engine.compare(a)==[]
    p=game_packet(GAMES[-1]);p.sequence+=1;p.frame+=15
    b=decoder.decode(p)
    assert b.party[0].sprite is None and engine.compare(b)==[]
    (catalogs/f'{GAMES[-1].sha1}.json').write_text(json.dumps({
        'rom_sha1':GAMES[-1].sha1,'species':{'277':{'name':'TREECKO','types':['Planta'],'sprite':'/assets/test/277.png'}},'locations':{'0':'Prueba'}}))
    assert decoder.decode(p).party[0].sprite=='/assets/test/277.png'
    assert decoder.decode(game_packet(GAMES[0])).party[0].sprite is None


def test_lua_registry_is_current():
    assert table() in Path('bridge/mgba/pokestream.lua').read_text('utf-8')


def test_frlg_rejects_missing_key(tmp_path):
    p=game_packet(GAMES[-1]);p.money_key=None
    with pytest.raises(ValueError,match='clave'): Gen3Decoder(tmp_path).decode(p)
