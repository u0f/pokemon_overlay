"""Read-only check of the actual local WebSocket. No demo toggle or emulator input."""
import json
import statistics
import time
from pathlib import Path
from websockets.sync.client import connect

samples=[]
with connect('ws://127.0.0.1:8765/ws',origin='http://127.0.0.1:8765') as ws:
    deadline=time.monotonic()+20
    while len(samples)<12 and time.monotonic()<deadline:
        message=json.loads(ws.recv(timeout=6))
        if message.get('type')!='state':continue
        s=message['state']
        samples.append({'received':time.monotonic(),'sequence':s['sequence'],'connection':s['connection'],
            'source':s['source'],'trainer':s['trainer'],'location':s['location'],'money':s['money'],
            'play_seconds':s['play_seconds'],'party':s['party'],'rom_id':s['rom_id']})
live=[s for s in samples if s['source']=='real' and s['connection']=='connected']
gaps=[b['received']-a['received'] for a,b in zip(live,live[1:])]
report={'samples':samples,'real_samples':len(live),'median_interval_seconds':statistics.median(gaps) if gaps else None,
    'party_observed':bool(live and live[-1]['party'])}
Path('data/live-validation.json').write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding='utf-8')
print(json.dumps({k:v for k,v in report.items() if k!='samples'},indent=2))
if live:print(json.dumps(live[-1],ensure_ascii=False,indent=2))
