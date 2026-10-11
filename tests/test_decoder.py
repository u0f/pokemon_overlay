import struct
from pathlib import Path
import pytest
from backend.app.decoder import ORDERS, CRC32, decode_mon, EmeraldDecoder, text
from backend.app.models import Wire


def mon(pid=24,species=277,hp=20,max_hp=30,level=5):
    raw=bytearray(100)
    ot=0x12345678
    struct.pack_into('<II',raw,0,pid,ot)
    raw[8:18]=bytes([0xBB,0xC6,0xBC,0xBB])+b'\xff'*6
    raw[19]=2
    clear=bytearray(48)
    struct.pack_into('<H',clear,ORDERS[pid%24][0]*12,species)
    struct.pack_into('<H',raw,28,sum(struct.unpack('<24H',clear))&65535)
    for i in range(0,48,4): struct.pack_into('<I',raw,32+i,struct.unpack_from('<I',clear,i)[0]^pid^ot)
    raw[84]=level
    struct.pack_into('<HH',raw,86,hp,max_hp)
    return bytes(raw)


def packet():
    sb1=bytearray(0x494); sb2=bytearray(0xB0); flags=bytearray(300)
    sb2[:8]=bytes([0xBB,0xC6,0xBC,0xBB])+b'\xff'*4
    struct.pack_into('<I',sb2,10,1234)
    struct.pack_into('<I',sb2,0xAC,0xAABBCCDD)
    struct.pack_into('<I',sb1,0x490,3000^0xAABBCCDD)
    sb2[14]=2;sb2[16]=3
    flags[0x867//8]=1<<(0x867%8)
    sb2[0x28]=1;sb2[0x5C]=3
    return Wire(protocol=1,code='BPES',crc32=CRC32,revision=0,sequence=1,epoch=1,frame=60,ready=True,
        party_count=1,party=(mon()+bytes(500)).hex(),save1=sb1.hex(),save2=sb2.hex(),flags=flags.hex(),
        seen1=(b'\x03'+bytes(51)).hex(),seen2=(b'\x03'+bytes(51)).hex(),map_header=bytes(28).hex(),
        in_battle=False,battle_outcome=0,battle_flags=0)


@pytest.mark.parametrize('pid',range(24))
def test_all_substructure_orders(pid):
    m=decode_mon(mon(pid=pid),0,{})
    assert m.species_id==277 and m.hp==20 and m.level==5
    assert m.nickname=='ALBA'


def test_corrupt_partial_and_invalid_hp():
    raw=bytearray(mon());raw[38]^=1
    with pytest.raises(ValueError,match='Checksum'): decode_mon(bytes(raw),0,{})
    with pytest.raises(ValueError): decode_mon(mon()[:-1],0,{})
    with pytest.raises(ValueError): decode_mon(mon(hp=31),0,{})


def test_state_and_all_six_slots(tmp_path):
    p=packet();p.party_count=6;p.party=b''.join(mon(pid=i) for i in range(6)).hex()
    s=EmeraldDecoder(tmp_path).decode(p)
    assert len(s.party)==6 and s.money==3000 and s.play_seconds==7380
    assert s.badges==[True]+[False]*7 and s.seen==2 and s.caught==1
    assert s.location is None and s.location_code=='0.0'


def test_dex_redundancy_and_revision(tmp_path):
    decoder=EmeraldDecoder(tmp_path);p=packet();p.seen2=bytes(52).hex()
    assert decoder.decode(p).seen==0
    p.revision=1
    with pytest.raises(ValueError,match='ROM'):decoder.decode(p)
    p=packet();p.save1=p.save1[:-2]
    with pytest.raises(ValueError,match='parcial'):decoder.decode(p)


def test_zero_hp_is_valid(tmp_path):
    p=packet();p.party=(mon(hp=0)+bytes(500)).hex()
    assert EmeraldDecoder(tmp_path).decode(p).party[0].hp==0


def test_spanish_text():
    assert text(bytes([0x14,0xD5,0x29,0x51,0x52,0xFF]))=='Ñañ¿¡'
    assert text(bytes.fromhex('c0bbccc0bfcebdc2b4beff'))=='FARFETCH’D'
    assert text(bytes.fromhex('d0c3c6c6bb00fc00ccbb5ad4ff'))=='VILLA RAÍZ'


def test_uninitialized_save_waits_with_game_identity(tmp_path):
    p=packet();p.save2=bytes(0xB0).hex();p.party_count=0
    state=EmeraldDecoder(tmp_path).decode(p)
    assert state.connection=='waiting' and state.game_id=='emerald-es-r0'
