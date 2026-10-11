"""Read only the user-supplied, hash-verified ROM; cache local names and icons.
No ROM bytes or derived assets belong in the distributable.
"""
import argparse
import hashlib
import json
import struct
import sys
import zlib
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from backend.app.decoder import SHA1, text, u32
from backend.app.games import identify

TYPES = ['Normal','Lucha','Volador','Veneno','Tierra','Roca','Bicho','Fantasma','Acero','???','Fuego','Agua','Planta','Eléctrico','Psíquico','Hielo','Dragón','Siniestro']


def prepare(rom_path: Path, data_dir: Path):
    from PIL import Image
    rom = rom_path.read_bytes()
    if len(rom) < 0x200: raise ValueError('ROM incompleta')
    game = identify(rom[0xAC:0xB0].decode('ascii'), rom[0xBC], f'{zlib.crc32(rom):08x}')
    if hashlib.sha1(rom).hexdigest() != game.sha1: raise ValueError('SHA1 de ROM no reconocido')
    def ptr(at):
        value = u32(rom, at)-0x08000000
        if not 0 <= value < len(rom): raise ValueError('Puntero ROM inválido')
        return value
    gf = 0x100
    layout = game.memory
    if not rom[gf+8:gf+40].startswith(b'pokemon '): raise ValueError('Cabecera GF no reconocida')
    expected = {0x50:layout['flags'],0x58:0x18,0x5C:layout['seen1'],0x60:layout['seen2'],
                0x88:layout['size2'],0x8C:layout['size1']}
    if any(u32(rom,gf+offset)!=value for offset,value in expected.items()):
        raise ValueError('Estructura de guardado inesperada')
    names = ptr(gf+0x44)
    if game.family == 'rs':
        # RS GF headers omit base stats. Match two complete stat/type prefixes,
        # spaced by the documented 28-byte structure; reject ambiguous matches.
        signature = bytes([45,49,49,45,65,65,12,3])
        candidates=[]; start=0
        while (at := rom.find(signature,start)) >= 0:
            if rom[at+28:at+36] == bytes([60,62,63,60,80,80,12,3]): candidates.append(at-28)
            start=at+1
        if len(candidates)!=1: raise ValueError('Tabla de estadísticas RS ambigua o ausente')
        stats=candidates[0]
    else:
        stats=ptr(gf+0xBC)
    icons, palette_ids, palettes = ptr(gf+0x38), ptr(gf+0x3C), ptr(gf+0x40)
    assets = data_dir/'assets'/game.sha1
    assets.mkdir(parents=True,exist_ok=True)
    species = {}
    for i in range(1,412):
        if 252 <= i <= 276: continue
        name = text(rom[names+i*11:names+i*11+11])
        types = list(dict.fromkeys(TYPES[n] for n in rom[stats+i*28+6:stats+i*28+8]))
        pixels = ptr(icons+i*4)
        pal = ptr(palettes+rom[palette_ids+i]*8)
        colors = []
        for j in range(16):
            c = struct.unpack_from('<H',rom,pal+j*2)[0]
            colors.append(((c&31)*255//31,((c>>5)&31)*255//31,((c>>10)&31)*255//31,0 if j==0 else 255))
        img=Image.new('RGBA',(32,32))
        for y in range(32):
            for x in range(32):
                index=(y//8*4+x//8)*32+(y%8)*4+(x%8)//2
                color=(rom[pixels+index] >> (4*(x%2))) & 15
                img.putpixel((x,y),colors[color])
        img.save(assets/f'{i}.png')
        if not name or '�' in name: raise ValueError('Nombre de especie no válido')
        species[str(i)]={'name':name,'types':types,'sprite':f'/assets/{game.sha1}/{i}.png'}
    locations={}
    for i in range(game.location_count):
        table=game.locations-0x08000000
        at=ptr(table+i*4 if game.family=='frlg' else table+i*8+4)
        raw=rom[at:at+64].split(b'\xff',1)[0]
        # The hideout name uses the EVIL_TEAM placeholder rather than literal text.
        team='MAGMA' if game.code=='AXVS' else 'AQUA'
        raw=raw.replace(b'\xfd\x08',bytes(0xBB+ord(c)-ord('A') for c in team))
        name=text(raw)
        if '�' in name: raise ValueError('Nombre de ubicación no válido')
        locations[str(i+0x58 if game.family=='frlg' else i)] = name
    catalog={'rom_sha1':game.sha1,'species':species,'locations':locations}
    catalogs=data_dir/'catalogs'; catalogs.mkdir(parents=True,exist_ok=True)
    target=catalogs/f'{game.sha1}.json'
    temporary=target.with_suffix('.tmp')
    temporary.write_text(json.dumps(catalog,ensure_ascii=False),encoding='utf-8')
    temporary.replace(target)
    report={'rom':str(rom_path.resolve()),'sha1':game.sha1,'code':game.code,'revision':game.revision,
        'gf_header':'0x08000100','names':hex(names+0x08000000),'species_info':hex(stats+0x08000000),
        'species_count':len(species),'locations_count':len(locations)}
    (catalogs/f'{game.sha1}-validation.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    return report


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('rom',type=Path,nargs='?')
    parser.add_argument('--data',type=Path,default=Path('data'))
    args=parser.parse_args()
    rom=args.rom or next(Path('.').glob('mGBA*/*.gba'),None)
    if rom is None: parser.error('Indica la ruta de tu ROM')
    print(json.dumps(prepare(rom,args.data),ensure_ascii=False,indent=2))
