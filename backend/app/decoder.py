"""Emerald BPES rev 0. Sources and address validation: docs/MEMORY.md."""
import json
import struct
from datetime import datetime, timezone
from pathlib import Path
from .models import Pokemon, State, Wire, EmeraldExtension
from .games import identify

SHA1 = 'fe1558a3dcb0360ab558969e09b690888b846dd9'
CRC32 = '8c4d3108'
# Position of Growth, Attacks, EVs, Misc in each of the 24 physical orders.
ORDERS = ((0,1,2,3),(0,1,3,2),(0,2,1,3),(0,3,1,2),(0,2,3,1),(0,3,2,1),
          (1,0,2,3),(1,0,3,2),(2,0,1,3),(3,0,1,2),(2,0,3,1),(3,0,2,1),
          (1,2,0,3),(1,3,0,2),(2,1,0,3),(3,1,0,2),(2,3,0,1),(3,2,0,1),
          (1,2,3,0),(1,3,2,0),(2,1,3,0),(3,1,2,0),(2,3,1,0),(3,2,1,0))
CHARS = {0:' ',1:'À',2:'Á',3:'Â',4:'Ç',5:'È',6:'É',7:'Ê',8:'Ë',9:'Ì',11:'Î',12:'Ï',13:'Ò',14:'Ó',15:'Ô',16:'Œ',17:'Ù',18:'Ú',19:'Û',20:'Ñ',21:'ß',22:'à',23:'á',25:'ç',26:'è',27:'é',28:'ê',29:'ë',30:'ì',32:'î',33:'ï',34:'ò',35:'ó',36:'ô',37:'œ',38:'ù',39:'ú',40:'û',41:'ñ',42:'º',43:'ª',45:'&',46:'+',81:'¿',82:'¡',90:'Í',91:'%',92:'(',93:')',104:'â',111:'í',171:'!',172:'?',173:'.',174:'-',176:'…',181:'♂',182:'♀',183:'$',184:',',185:'×',186:'/',240:':',241:'Ä',242:'Ö',243:'Ü',244:'ä',245:'ö',246:'ü'}
CHARS.update({0xBB+i:chr(65+i) for i in range(26)})
CHARS.update({0xD5+i:chr(97+i) for i in range(26)})
CHARS.update({0xA1+i:str(i) for i in range(10)})
CHARS.update({0xB1:'“',0xB2:'”',0xB3:'‘',0xB4:'’'})


def text(data: bytes) -> str:
    # RS Spanish location strings contain NAME_END (FC 00), a zero-argument control.
    data = data.replace(b'\xfc\x00',b'')
    return ''.join(CHARS.get(c, '�') for c in data.split(b'\xff')[0]).strip()


def u16(data, at=0):
    return struct.unpack_from('<H', data, at)[0]


def u32(data, at=0):
    return struct.unpack_from('<I', data, at)[0]


def status_name(value):
    if value & 7: return 'Dormido'
    for flag, name in [(0x88,'Envenenado'),(0x10,'Quemado'),(0x20,'Congelado'),(0x40,'Paralizado')]:
        if value & flag: return name
    return 'Sano'


def decode_mon(raw: bytes, slot: int, catalog: dict) -> Pokemon:
    if len(raw) != 100: raise ValueError('Slot incompleto')
    pid, ot = u32(raw), u32(raw,4)
    key = pid ^ ot
    clear = b''.join(struct.pack('<I', u32(raw,i)^key) for i in range(32,80,4))
    if sum(struct.unpack('<24H', clear)) & 0xFFFF != u16(raw,28):
        raise ValueError(f'Checksum inválido en slot {slot+1}')
    if raw[19] & 1 or not raw[19] & 2: raise ValueError('Huevo malo o slot vacío')
    order = ORDERS[pid % 24]
    species = u16(clear, order[0]*12)
    if species == 0 or 252 <= species <= 276 or species > 411:
        raise ValueError('Especie inválida')
    entry = catalog.get(str(species), {})
    egg = bool(u32(clear, order[3]*12+4) & (1<<30))
    shiny = ((pid>>16) ^ (pid&65535) ^ (ot>>16) ^ (ot&65535)) < 8
    form = str((((pid & 0x3000000)>>18)|((pid & 0x30000)>>12)|((pid & 0x300)>>6)|(pid & 3)) % 28) if species == 201 else 'normal'
    return Pokemon(identity=f'{pid:08x}-{ot:08x}',slot=slot,species_id=species,
        species=entry.get('name',f'Especie {species}'), nickname=text(raw[8:18]),
        level=raw[84], hp=u16(raw,86), max_hp=u16(raw,88),status=status_name(u32(raw,80)),
        types=entry.get('types',[]),sprite=(entry['sprite'] if isinstance(entry.get('sprite'),str) else f'/assets/{species}.png') if entry.get('sprite') and not egg else None,
        egg=egg,shiny=shiny,form=form)


def blob(value: str, length: int):
    data = bytes.fromhex(value)
    if len(data) != length: raise ValueError('Lectura parcial rechazada')
    return data


class Gen3Decoder:
    def __init__(self, data_dir: Path):
        self.data_dir = data_dir
        self.catalog_id = None
        path = data_dir/'catalog.json'
        self.catalog = json.loads(path.read_text('utf-8')) if path.exists() else {'species':{}, 'locations':{}}

    def decode(self, packet: Wire) -> State:
        game = identify(packet.code, packet.revision, packet.crc32)
        layout = game.memory
        path = self.data_dir/'catalogs'/f'{game.sha1}.json'
        if not path.exists() and game.sha1 == SHA1:
            path = self.data_dir/'catalog.json'
        catalog_id = (game.sha1, path.stat().st_mtime_ns if path.exists() else None)
        if catalog_id != self.catalog_id:
            catalog = json.loads(path.read_text('utf-8')) if path.exists() else {}
            self.catalog = catalog if catalog.get('rom_sha1') == game.sha1 else {'species':{}, 'locations':{}}
            self.catalog_id = catalog_id
        base = dict(game=f'Pokémon {game.name} · España',game_id=game.id,rom_id=game.sha1,
            revision=game.revision,sequence=packet.sequence,timestamp=datetime.now(timezone.utc).isoformat())
        if not packet.ready:
            return State(**base, connection='waiting',message='ROM reconocida. Carga o inicia una partida.')
        party = blob(packet.party,600)
        sb1 = blob(packet.save1,layout['money']+4)
        sb2 = blob(packet.save2,0xB0)
        flags = blob(packet.flags,300)
        seen1, seen2 = blob(packet.seen1,52), blob(packet.seen2,52)
        header = blob(packet.map_header,28)
        trainer = text(sb2[:8])
        if not trainer:
            return State(**base, connection='waiting',message='ROM reconocida. Carga o inicia una partida.')
        if '�' in trainer or sb2[0x10] > 59 or sb2[0x11] > 59 or u16(sb2,14)>999:
            raise ValueError('Partida todavía sin inicializar')
        members = [decode_mon(party[i*100:(i+1)*100],i,self.catalog['species']) for i in range(packet.party_count)]
        if len({m.identity for m in members}) != len(members): raise ValueError('Identidades duplicadas')
        seen_bits = int.from_bytes(sb2[0x5C:0x90],'little') & int.from_bytes(seen1,'little') & int.from_bytes(seen2,'little') & ((1<<386)-1)
        owned_bits = int.from_bytes(sb2[0x28:0x5C],'little') & seen_bits
        region = header[0x14]
        location = self.catalog['locations'].get(str(region))
        key = 0 if game.family == 'rs' else u32(sb2,0xAC)
        if game.family == 'frlg':
            if packet.money_key is None: raise ValueError('Falta la clave de dinero; recarga el script Lua actualizado')
            key = packet.money_key
        message = 'Leyendo memoria real · solo lectura'
        if game.family != 'emerald': message += ' · conector experimental: validación completa de combate pendiente'
        if not self.catalog['species']: message += ' · catálogo pendiente: coloca la ROM en roms y reinicia PokeStream'
        return State(**base, connection='connected',message=message,
            trainer=trainer,trainer_id=f'{u32(sb2,10):08x}',party=members,
            money=u32(sb1,layout['money'])^key,play_seconds=u16(sb2,14)*3600+sb2[16]*60+sb2[17],
            badges=[bool(flags[(layout['badge']+i)//8] & (1<<((layout['badge']+i)%8))) for i in range(8)],
            location=location,location_code=f'{sb1[4]}.{sb1[5]}',seen=seen_bits.bit_count(),caught=owned_bits.bit_count(),
            extensions=EmeraldExtension(in_battle=packet.in_battle,battle_outcome=packet.battle_outcome,
                battle_flags=packet.battle_flags,owned=[i+1 for i in range(386) if owned_bits>>i&1],epoch=packet.epoch,frame=packet.frame))


# Existing callers and tests can continue to use the original public name.
EmeraldDecoder = Gen3Decoder
