from pathlib import Path
from PyInstaller.archive.readers import CArchiveReader
import struct
import pefile
archive=CArchiveReader(str(Path('dist/PokeStream.exe')))
names=list(archive.toc)
for name in names:
    normal=name.replace('\\','/').lower()
    assert not normal.endswith(('.gba','.sav','.srm')),name
    assert not normal.startswith(('data/','mgba-')),name
assert any(name.replace('\\','/')=='bridge/mgba/pokestream.lua' for name in names)
assert any(name.replace('\\','/')=='frontend/dist/index.html' for name in names)
print(f'Paquete comprobado: {len(names)} entradas; sin ROM, emulador, partidas ni cache de recursos.')
icon=Path('assets/pokestream.ico').read_bytes()
count=struct.unpack_from('<H',icon,4)[0]
frames=[]
for index in range(count):
    size,offset=struct.unpack_from('<II',icon,6+index*16+8)
    frames.append(icon[offset:offset+size])
pe=pefile.PE('dist/PokeStream.exe')
embedded=[]
for entry in pe.DIRECTORY_ENTRY_RESOURCE.entries:
    if entry.id==3:
        for resource in entry.directory.entries:
            data=resource.directory.entries[0].data.struct
            embedded.append(pe.get_data(data.OffsetToData,data.Size))
assert len(frames)==7 and set(frames)==set(embedded),'Icono del ejecutable incorrecto'
pe.close()
print('Icono propio comprobado: siete tamaños incrustados en el ejecutable.')
