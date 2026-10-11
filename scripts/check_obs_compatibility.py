"""Read-only browser smoke test; works with Chromium 75 and current Chromium.
Usage: python scripts/check_obs_compatibility.py --browser PATH --label chrome75
The test opens the local overlay and previews, without changing profiles or demo mode.
"""
import argparse
import base64
import json
import io
import socket
import subprocess
import tempfile
import time
import urllib.request
from pathlib import Path
from websockets.sync.client import connect
from PIL import Image


def check(browser: Path, label: str, shutdown=False):
    with socket.socket() as sock:
        sock.bind(('127.0.0.1', 0))
        port = sock.getsockname()[1]
    errors = []
    with tempfile.TemporaryDirectory(prefix='pokestream-browser-', ignore_cleanup_errors=True) as profile:
        startup = subprocess.STARTUPINFO()
        startup.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        startup.wShowWindow = subprocess.SW_HIDE
        process = subprocess.Popen([
            str(browser), '--headless', '--disable-gpu', '--no-first-run',
            '--no-default-browser-check', '--disable-background-networking',
            '--disable-component-update', '--hide-scrollbars', '--window-size=1920,1080',
            '--remote-debugging-address=127.0.0.1', f'--remote-debugging-port={port}',
            f'--user-data-dir={profile}', 'about:blank',
        ], startupinfo=startup, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        try:
            def get(path):
                with urllib.request.urlopen(f'http://127.0.0.1:{port}{path}', timeout=1) as response:
                    return json.load(response)
            for _ in range(80):
                try:
                    version = get('/json/version')
                    break
                except OSError:
                    time.sleep(.1)
            else:
                raise RuntimeError('El navegador de prueba no arrancó')
            target = next(t for t in get('/json/list') if t['type'] == 'page')
            with connect(target['webSocketDebuggerUrl']) as ws:
                seq = 0
                def command(method, params=None):
                    nonlocal seq
                    seq += 1
                    ws.send(json.dumps({'id':seq,'method':method,'params':params or {}}))
                    while True:
                        message = json.loads(ws.recv(timeout=5))
                        if message.get('method') == 'Runtime.exceptionThrown':
                            errors.append(message['params']['exceptionDetails'])
                        if message.get('id') == seq:
                            if 'error' in message: raise RuntimeError(message['error'])
                            return message.get('result', {})
                command('Runtime.enable')
                command('Page.enable')
                command('Emulation.setDeviceMetricsOverride', {'width':1920,'height':1080,'deviceScaleFactor':1,'mobile':False})
                command('Emulation.setDefaultBackgroundColorOverride', {'color':{'r':0,'g':0,'b':0,'a':0}})
                command('Page.navigate', {'url':'http://127.0.0.1:8765/overlay?profile=default'})
                expression = '''(function(){var host=document.querySelector('.canvas-host');var frame=document.querySelector('.c-game');return {background:getComputedStyle(document.body).backgroundColor,height:host?host.getBoundingClientRect().height:0,frameWidth:frame?frame.getBoundingClientRect().width:0,slots:document.querySelectorAll('.overlay-party .mon').length,controls:document.querySelectorAll('button,input,select,nav').length,text:document.body.innerText};})()'''
                geometry = {}
                for _ in range(60):
                    geometry = command('Runtime.evaluate', {'expression':expression,'returnByValue':True})['result'].get('value', {})
                    if geometry.get('slots') == 6 and geometry.get('height') == 1080: break
                    time.sleep(.1)
                time.sleep(.5)
                geometry = command('Runtime.evaluate', {'expression':expression,'returnByValue':True})['result'].get('value', {})
                png = command('Page.captureScreenshot', {'format':'png'})['data']
                pixels = base64.b64decode(png)
                Path(f'data/overlay-{label}.png').write_bytes(pixels)
                image = Image.open(io.BytesIO(pixels)).convert('RGBA')
                transparency = {'corner':image.getpixel((0,0))[3],'game_area':image.getpixel((200,200))[3]}
                assert transparency == {'corner':0,'game_area':0}, transparency
                assert not errors, errors
                assert geometry['background'] == 'rgba(0, 0, 0, 0)', geometry
                assert geometry['height'] == 1080 and geometry['frameWidth'] == 1280, geometry
                assert geometry['slots'] == 6 and geometry['controls'] == 0, geometry
                report = {'browser':version['Browser'],'errors':errors,'geometry':geometry,'alpha':transparency}
                preview_labels={}
                for view in ('dashboard','designer','preview'):
                    if view=='designer':
                        command('Runtime.evaluate',{'expression':"document.querySelector('nav button[aria-label=\"Diseñador\"]').click()"})
                    else:
                        command('Page.navigate',{'url':f'http://127.0.0.1:8765/{view}?profile=default'})
                    for _ in range(60):
                        ready=command('Runtime.evaluate',{'expression':"document.querySelectorAll('.preview-canvas .frame-label').length===2",'returnByValue':True})['result'].get('value')
                        if ready: break
                        time.sleep(.1)
                    command('Runtime.evaluate',{'expression':"document.querySelector('.preview-canvas').scrollIntoView({block:'start'})"})
                    time.sleep(.2)
                    labels=command('Runtime.evaluate',{'expression':'''Array.from(document.querySelectorAll('.preview-canvas .frame-label'),function(label){var r=label.getBoundingClientRect();var hit=document.elementFromPoint(r.left+r.width/2,r.top+r.height*.75);return {text:label.textContent,visible:hit===label||label.contains(hit)};})''','returnByValue':True})['result']['value']
                    Path(f'data/preview-{view}-{label}.png').write_bytes(base64.b64decode(command('Page.captureScreenshot',{'format':'png'})['data']))
                    assert len(labels)==2 and all(item['visible'] for item in labels),(view,labels)
                    preview_labels[view]=labels
                assert not errors,errors
                report['preview_labels']=preview_labels
                if shutdown:
                    command('Page.navigate',{'url':'http://127.0.0.1:8765/dashboard'})
                    for _ in range(60):
                        ready=command('Runtime.evaluate',{'expression':"!!document.querySelector('nav button[aria-label=\"Configuración\"]')",'returnByValue':True})['result'].get('value')
                        if ready: break
                        time.sleep(.1)
                    command('Runtime.evaluate',{'expression':"document.querySelector('nav button[aria-label=\"Configuración\"]').click()"})
                    time.sleep(.2)
                    command('Runtime.evaluate',{'expression':"document.querySelector('.shutdown-control button').click()"})
                    for _ in range(60):
                        closed=command('Runtime.evaluate',{'expression':"!!document.querySelector('.shutdown-page')",'returnByValue':True})['result'].get('value')
                        if closed: break
                        time.sleep(.1)
                    assert closed,'La web no muestra el cierre'
                    Path(f'data/shutdown-{label}.png').write_bytes(base64.b64decode(command('Page.captureScreenshot',{'format':'png'})['data']))
                    for _ in range(60):
                        try: urllib.request.urlopen('http://127.0.0.1:8765/api/health',timeout=.2).close()
                        except OSError: break
                        time.sleep(.1)
                    else: raise AssertionError('El servidor sigue escuchando después de cerrar')
                    report['shutdown']={'closed_page':True,'port_released':True}
                Path(f'data/obs-compatibility-{label}.json').write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding='utf-8')
                print(json.dumps(report,indent=2,ensure_ascii=True))
                ws.send(json.dumps({'id':seq+1,'method':'Browser.close'}))
        finally:
            try:
                process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                process.terminate()
                process.wait(timeout=10)
            time.sleep(.3)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--browser', type=Path, required=True)
    parser.add_argument('--label', choices=['chrome75','current'], required=True)
    parser.add_argument('--shutdown', action='store_true', help='Also click Cerrar PokeStream and stop the local server.')
    args = parser.parse_args()
    check(args.browser.resolve(), args.label,args.shutdown)
