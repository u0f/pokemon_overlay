"""Exercise the local ROM checker using real files in a headless browser."""
import argparse
import base64
import json
import socket
import subprocess
import tempfile
import time
import urllib.request
from pathlib import Path
from websockets.sync.client import connect


def check(browser, label):
    with socket.socket() as sock:
        sock.bind(('127.0.0.1', 0)); port=sock.getsockname()[1]
    with tempfile.TemporaryDirectory(prefix='pokestream-rom-ui-',ignore_cleanup_errors=True) as temp:
        startup=subprocess.STARTUPINFO(); startup.dwFlags|=subprocess.STARTF_USESHOWWINDOW; startup.wShowWindow=subprocess.SW_HIDE
        process=subprocess.Popen([str(browser),'--headless','--disable-gpu','--no-first-run',
            '--disable-background-networking','--disable-component-update',
            '--remote-debugging-address=127.0.0.1',f'--remote-debugging-port={port}',
            f'--user-data-dir={temp}', 'about:blank'],startupinfo=startup,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        try:
            for _ in range(80):
                try:
                    with urllib.request.urlopen(f'http://127.0.0.1:{port}/json/list',timeout=1) as response: targets=json.load(response)
                    break
                except OSError: time.sleep(.1)
            else: raise RuntimeError('No arrancó el navegador')
            with connect(next(t for t in targets if t['type']=='page')['webSocketDebuggerUrl']) as ws:
                sequence=0; errors=[]
                def command(method,params=None):
                    nonlocal sequence
                    sequence+=1; ws.send(json.dumps({'id':sequence,'method':method,'params':params or {}}))
                    while True:
                        message=json.loads(ws.recv(timeout=10))
                        if message.get('method')=='Runtime.exceptionThrown': errors.append(message['params'])
                        if message.get('id')==sequence:
                            if 'error' in message: raise RuntimeError(message['error'])
                            return message.get('result',{})
                def evaluate(expression):
                    response=command('Runtime.evaluate',{'expression':expression,'returnByValue':True})
                    assert 'exceptionDetails' not in response,response
                    return response['result'].get('value')
                def screenshot(name):
                    Path(f'data/rom-ui-{label}-{name}.png').write_bytes(base64.b64decode(command('Page.captureScreenshot',{'format':'png'})['data']))
                command('Runtime.enable'); command('Page.enable')
                command('Emulation.setDeviceMetricsOverride',{'width':1440,'height':1100,'deviceScaleFactor':1,'mobile':False})
                command('Page.navigate',{'url':'http://127.0.0.1:8765/dashboard'})
                for _ in range(80):
                    if evaluate("!!document.querySelector('nav button[aria-label=\"Configuración\"]')"): break
                    time.sleep(.1)
                evaluate("document.querySelector('nav button[aria-label=\"Configuración\"]').click()")
                assert evaluate("getComputedStyle(document.querySelector('.rom-picker input')).display==='none'")
                time.sleep(.2); screenshot('initial')
                root=command('DOM.getDocument')['root']['nodeId']
                node=command('DOM.querySelector',{'nodeId':root,'selector':'.rom-picker input'})['nodeId']
                report=[]
                def test(path,expected):
                    command('DOM.setFileInputFiles',{'nodeId':node,'files':[str(path.resolve())]})
                    for _ in range(100):
                        result=evaluate("(function(){var r=document.querySelector('.rom-result');return r?{className:r.className,text:r.innerText}:null})()")
                        if result: break
                        time.sleep(.1)
                    assert result and expected in result['className'],(path,result)
                    report.append({'file':path.name,**result})
                roms=sorted(Path('roms').glob('*.gba')); assert len(roms)==5
                for rom in roms: test(rom,'success')
                screenshot('success')
                bad=Path(temp)/'incompleta.gba'; bad.write_bytes(b'broken');test(bad,'error');screenshot('error')
                original=bytearray(roms[0].read_bytes()); original[-1]^=1
                bad=Path(temp)/'modificada.gba';bad.write_bytes(original);test(bad,'error')
                original[0xac:0xb0]=b'BPEE';original[0xbd]=(-sum(original[0xa0:0xbd])-0x19)&255
                bad=Path(temp)/'no-compatible.gba';bad.write_bytes(original);test(bad,'warning');screenshot('warning')
                command('Network.enable');command('Network.setBlockedURLs',{'urls':['*/api/games']})
                test(roms[0],'error')
                assert 'Comprueba la conexión' in report[-1]['text']
                command('Network.setBlockedURLs',{'urls':[]})
                test(roms[0],'success')
                command('Emulation.setDeviceMetricsOverride',{'width':390,'height':1000,'deviceScaleFactor':1,'mobile':False})
                time.sleep(.2);screenshot('mobile')
                overflow=evaluate('document.documentElement.scrollWidth>window.innerWidth')
                assert not overflow,'Desbordamiento horizontal en móvil'
                assert not errors,errors
                Path(f'data/rom-ui-{label}.json').write_text(json.dumps({'cases':report,'errors':errors,'mobile_overflow':overflow},ensure_ascii=False,indent=2),'utf-8')
                print(f'{label}: cinco ROMs válidas, incompleta, modificada y no compatible; móvil sin desbordamiento; sin errores JS.')
                ws.send(json.dumps({'id':sequence+1,'method':'Browser.close'}))
        finally:
            try: process.wait(timeout=3)
            except subprocess.TimeoutExpired: process.terminate(); process.wait(timeout=10)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--browser',type=Path,required=True);parser.add_argument('--label',choices=['current','chrome75'],required=True)
    args=parser.parse_args();check(args.browser.resolve(),args.label)
