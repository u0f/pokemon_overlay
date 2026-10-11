from fastapi.testclient import TestClient
from backend.app.main import create_app
from backend.app.models import Profile
from backend.app.events import event
from tests.test_decoder import packet
import time


def test_http_websocket_profiles_persistence(tmp_path):
    app=create_app(tmp_path,run_bridge=False)
    with TestClient(app) as client:
        assert client.get('/api/health').json()['ok']
        with client.websocket_connect('/ws') as ws:
            assert ws.receive_json()['state']['connection']=='disconnected'
            client.put('/api/profiles/default',json=Profile(name='Mi perfil').model_dump())
            assert ws.receive_json()['profiles']['default']['name']=='Mi perfil'
        bad=Profile().model_dump();bad['components']['party']['x']=1900
        assert client.put('/api/profiles/default',json=bad).status_code==422
        assert client.put('/api/settings',json={'demo':True},headers={'Origin':'https://evil.example'}).status_code==403
        assert client.get('/api/state',headers={'Host':'evil.example'}).status_code==400
    with TestClient(create_app(tmp_path,run_bridge=False)) as client:
        assert client.get('/api/profiles').json()['default']['name']=='Mi perfil'


def test_nuzlocke_manual_correction_preserves_runs(tmp_path):
    app=create_app(tmp_path,run_bridge=False)
    with TestClient(app) as client:
        service=app.state.service;service.accept(packet())
        ev=event('POKEMON_FAINTED',20,0,service.state.party[0].model_dump())
        service.store.record(ev,True)
        death=client.get('/api/nuzlocke').json()['deaths'][0]
        assert death['status']=='pending'
        assert client.put('/api/nuzlocke/'+death['id'],json={'status':'confirmed'}).status_code==200
        client.post('/api/runs',json={})
        data=client.get('/api/nuzlocke').json()
        assert data['deaths'][0]['run']!=data['run']
        client.put('/api/nuzlocke/'+death['id'],json={'status':'dismissed'})
        assert client.get('/api/nuzlocke').json()['deaths'][0]['status']=='dismissed'


def test_test_alert_is_never_real_history(tmp_path):
    with TestClient(create_app(tmp_path,run_bridge=False)) as client:
        assert client.post('/api/alerts/test',json={'type':'POKEMON_LEVEL_UP'}).json()['metadata']['test']
        assert client.get('/api/events').json()==[]


def test_shutdown_replies_before_stopping_and_rejects_foreign_origin(tmp_path):
    stopped=[]
    with TestClient(create_app(tmp_path,run_bridge=False,shutdown=lambda:stopped.append(True))) as client:
        settings=client.get('/api/settings').json()
        assert client.post('/api/shutdown',json={},headers={'Origin':'https://evil.example'}).status_code==403
        assert stopped==[]
        with client.websocket_connect('/ws') as ws:
            assert ws.receive_json()['type']=='state'
            assert client.post('/api/shutdown',json={}).json()=={'ok':True}
            assert ws.receive_json()=={'type':'shutdown'}
        assert stopped==[]
        time.sleep(.4)
        assert stopped==[True]
        assert client.get('/api/settings').json()==settings


def test_terminal_server_does_not_claim_to_shutdown(tmp_path):
    with TestClient(create_app(tmp_path,run_bridge=False)) as client:
        assert client.post('/api/shutdown',json={}).status_code==409


def test_request_limits_and_custom_port(tmp_path):
    with TestClient(create_app(tmp_path,run_bridge=False,port=9876)) as client:
        for length in ('broken','-1','999999999999999999999'):
            assert client.post('/api/runs',json={},headers={'Content-Length':length}).status_code==400
        assert client.post('/api/runs',content=b' '*65537,headers={'Content-Length':'2','Content-Type':'application/json'}).status_code==413
        assert client.put('/api/settings',json={'demo':True},headers={'Origin':'http://127.0.0.1:9876'}).status_code==200
        assert client.get('/api/settings').json()['demo']
        with client.websocket_connect('/ws',headers={'Origin':'http://127.0.0.1:9876'}) as ws:
            assert ws.receive_json()['settings']['demo']
    with TestClient(create_app(tmp_path,run_bridge=False)) as client:
        assert client.get('/api/settings').json()['demo']
