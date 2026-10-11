"""PokeStream launcher. Source and PyInstaller use the same entry point."""
import argparse
import logging
import os
from pathlib import Path
import sys
import shutil
import threading
import time
import urllib.request
import webbrowser
import uvicorn
from backend.app.main import create_app


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--no-browser',action='store_true')
    parser.add_argument('--port',type=int,default=8765)
    args=parser.parse_args()
    if not 1<=args.port<=65535: parser.error('El puerto debe estar entre 1 y 65535.')
    frozen=getattr(sys,'frozen',False)
    base=Path(sys.executable).parent if frozen else Path(__file__).resolve().parent
    resources=Path(getattr(sys,'_MEIPASS',base))
    data=base/'data'
    data.mkdir(exist_ok=True)
    bridge=base/'bridge'/'mgba'/'pokestream.lua'
    if frozen and (not bridge.exists() or bridge.read_bytes() != (resources/'bridge'/'mgba'/'pokestream.lua').read_bytes()):
        bridge.parent.mkdir(parents=True,exist_ok=True)
        if bridge.exists():
            import hashlib
            backup=bridge.with_name('pokestream-'+hashlib.sha1(bridge.read_bytes()).hexdigest()[:12]+'.lua.bak')
            if not backup.exists(): shutil.copyfile(bridge,backup)
        shutil.copyfile(resources/'bridge'/'mgba'/'pokestream.lua',bridge)
    logging.basicConfig(filename=data/'pokestream.log',level=logging.INFO,format='%(asctime)s %(levelname)s %(message)s')
    url=f'http://127.0.0.1:{args.port}'
    try:
        with urllib.request.urlopen(url+'/api/health',timeout=.5) as response:
            if response.status==200:
                if not args.no_browser: webbrowser.open(url+'/dashboard')
                return
    except OSError: pass
    from scripts.prepare_rom import prepare
    import hashlib
    roms = set(base.glob('mGBA*/*.gba')) | set((base/'roms').glob('*.gba')) | set(base.glob('*.gba'))
    for rom in sorted(roms):
        try:
            sha1=hashlib.sha1(rom.read_bytes()).hexdigest()
            if not (data/'catalogs'/f'{sha1}.json').exists(): prepare(rom,data)
        except (ValueError,OSError): logging.exception('No se pudo preparar el catálogo de %s',rom.name)
    def open_browser():
        for _ in range(40):
            try:
                urllib.request.urlopen(url+'/api/health',timeout=.3).close()
                webbrowser.open(url+'/dashboard'); return
            except OSError: time.sleep(.25)
    if not args.no_browser: threading.Thread(target=open_browser,daemon=True).start()
    def shutdown(): server.should_exit=True
    app=create_app(data,resources/'frontend'/'dist',shutdown=shutdown,port=args.port)
    server=uvicorn.Server(uvicorn.Config(app,host='127.0.0.1',port=args.port,log_config=None,timeout_graceful_shutdown=3))
    server.run()


if __name__=='__main__': main()
