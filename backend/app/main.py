import asyncio
import contextlib
import os
import re
from contextlib import asynccontextmanager
from pathlib import Path
from uuid import uuid4
from fastapi import FastAPI, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.trustedhost import TrustedHostMiddleware
from .models import Profile, Settings
from .events import event
from .service import Service
from .games import GAMES

ROOT=Path(__file__).resolve().parents[2]
ORIGINS={'http://127.0.0.1:8765','http://localhost:8765','http://127.0.0.1:5173','http://localhost:5173'}


def create_app(data_dir=None, frontend=None, run_bridge=True, shutdown=None, port=8765):
    data=Path(data_dir or os.environ.get('POKESTREAM_DATA',ROOT/'data'))
    frontend=Path(frontend or ROOT/'frontend'/'dist')
    service=Service(data)
    origins=ORIGINS | {f'http://127.0.0.1:{port}',f'http://localhost:{port}'}
    @asynccontextmanager
    async def lifespan(app):
        task=asyncio.create_task(service.run()) if run_bridge else None
        yield
        if task:
            task.cancel()
            with contextlib.suppress(asyncio.CancelledError): await task
        service.store.db.close()

    app=FastAPI(title='PokeStream Overlay',lifespan=lifespan)
    app.state.service=service
    app.add_middleware(TrustedHostMiddleware,allowed_hosts=['127.0.0.1','localhost','testserver'])

    @app.middleware('http')
    async def local_only(request:Request,call_next):
        origin=request.headers.get('origin')
        if origin and origin not in origins: return JSONResponse({'detail':'Origen no permitido'},status_code=403)
        if request.method not in ('GET','HEAD','OPTIONS'):
            length=request.headers.get('content-length')
            if not length or not length.isascii() or not length.isdecimal() or len(length)>10:
                return JSONResponse({'detail':'Longitud de petición inválida'},status_code=400)
            if int(length)>65536: return JSONResponse({'detail':'Petición demasiado grande'},status_code=413)
            if 'application/json' not in request.headers.get('content-type',''): return JSONResponse({'detail':'Se requiere JSON'},status_code=415)
            body=bytearray()
            async for chunk in request.stream():
                body.extend(chunk)
                if len(body)>65536:
                    return JSONResponse({'detail':'Petición demasiado grande'},status_code=413)
            # Starlette replays its cached body to the downstream JSON parser.
            request._body=bytes(body)
        response=await call_next(request)
        response.headers['X-Content-Type-Options']='nosniff'
        return response

    @app.get('/api/health')
    async def health(): return {'ok':True,'connection':service.state.connection,'source':service.state.source,'protocol':1}
    @app.post('/api/shutdown')
    async def stop_server():
        if shutdown is None: raise HTTPException(409,'Este servidor debe cerrarse desde su terminal.')
        for queue in service.clients:
            if queue.full(): queue.get_nowait()
            queue.put_nowait({'type':'shutdown'})
        # Let the browser receive the reply before Uvicorn closes its connections.
        asyncio.get_running_loop().call_later(.3,shutdown)
        return {'ok':True}
    @app.get('/api/state')
    async def state(): return service.state
    @app.get('/api/events')
    async def events(): return service.store.events()
    @app.get('/api/games')
    async def games():
        return [{'id':g.id,'name':f'Pokémon {g.name} · España','code':g.code,'revision':g.revision,
                 'crc32':g.crc32,'sha1':g.sha1,'experimental':g.family!='emerald'} for g in GAMES]
    @app.get('/api/settings')
    async def settings(): return service.settings
    @app.put('/api/settings')
    async def save_settings(settings:Settings):
        if service.settings.demo!=settings.demo:
            service.engine.reset()
        service.settings=settings; service.publish()
        return settings
    @app.get('/api/profiles')
    async def profiles(): return service.store.get('profiles')
    @app.put('/api/profiles/{key}')
    async def save_profile(key:str,profile:Profile):
        if not re.fullmatch(r'[a-z0-9_-]{1,40}',key): raise HTTPException(422,'Identificador inválido')
        saved=service.store.get('profiles')
        if key not in saved and len(saved)>=20: raise HTTPException(422,'Máximo 20 perfiles')
        saved[key]=profile.model_dump(); service.store.put('profiles',saved); service.publish()
        return profile
    @app.get('/api/diagnostics')
    async def diagnostics(): return {'errors':service.errors,'state':service.state,'catalog_ready':bool(service.decoder.catalog['species'])}
    @app.post('/api/alerts/test')
    async def test_alert(body:dict):
        kind=body.get('type','POKEMON_LEVEL_UP')
        if kind not in ['POKEMON_LEVEL_UP','POKEMON_EVOLVED','POKEMON_CAPTURED','POKEMON_FAINTED','BADGE_EARNED']:
            raise HTTPException(422,'Alerta desconocida')
        ev=event(kind,1,2,test=True)
        for queue in service.clients:
            if queue.full(): queue.get_nowait()
            queue.put_nowait({'type':'test_alert','event':ev})
        return ev
    @app.get('/api/nuzlocke')
    async def nuzlocke(): return {'run':service.store.get('run'),'deaths':service.store.deaths()}
    @app.put('/api/nuzlocke/{key:path}')
    async def death(key:str,body:dict):
        status=body.get('status')
        if status not in ('confirmed','dismissed','pending'): raise HTTPException(422,'Estado inválido')
        with service.store.db:
            cursor=service.store.db.execute('UPDATE deaths SET status=? WHERE id=?',(status,key))
        if cursor.rowcount!=1: raise HTTPException(404,'Registro inexistente')
        service.publish(); return {'ok':True}
    @app.post('/api/runs')
    async def new_run(body:dict):
        service.store.put('run',str(uuid4())); service.engine.reset(); service.publish()
        return {'run':service.store.get('run')}
    @app.websocket('/ws')
    async def websocket(ws:WebSocket):
        if ws.headers.get('origin') not in origins and ws.headers.get('origin') is not None:
            await ws.close(code=1008); return
        await ws.accept()
        queue=asyncio.Queue(maxsize=2)
        service.clients.add(queue)
        try:
            await ws.send_json(service.payload())
            while True:
                try: message=await asyncio.wait_for(queue.get(),15)
                except asyncio.TimeoutError: message={'type':'heartbeat'}
                await asyncio.wait_for(ws.send_json(message),3)
                if message['type']=='shutdown':
                    await ws.close()
                    break
        except (WebSocketDisconnect,RuntimeError,asyncio.TimeoutError,OSError): pass
        finally: service.clients.discard(queue)
    (data/'assets').mkdir(exist_ok=True)
    app.mount('/assets',StaticFiles(directory=data/'assets'),name='assets')
    if (frontend/'static').exists(): app.mount('/static',StaticFiles(directory=frontend/'static'),name='static')
    @app.get('/')
    @app.get('/dashboard')
    @app.get('/overlay')
    @app.get('/preview')
    def page():
        if not (frontend/'index.html').exists(): raise HTTPException(503,'Compila el frontend: npm run build --prefix frontend')
        return FileResponse(frontend/'index.html')
    return app
