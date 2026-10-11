"""Record real emulator observations; never inject state or change settings."""
import argparse
import json
import time
from pathlib import Path
from websockets.sync.client import connect


def observe(seconds, output):
    report={}
    deadline=time.monotonic()+seconds
    with connect('ws://127.0.0.1:8765/ws',origin='http://127.0.0.1:8765') as ws:
        while time.monotonic()<deadline:
            try: payload=json.loads(ws.recv(timeout=5))
            except TimeoutError: continue
            if payload.get('type')!='state': continue
            state=payload['state']
            if state['source']!='real' or state['rom_id'] is None: continue
            key=state['game_id']
            row=report.setdefault(key,{'samples':0,'connected_samples':0,'first':state,'last':state,'party_observed':False,'observed_locations':[]})
            row['samples']+=1;row['last']=state
            if state['connection']=='connected':
                row['connected_samples']+=1
                row['last_connected']=state
                if state['party']: row['party_observed']=True;row['party_sample']=state
                if state['location'] and state['location'] not in row['observed_locations']: row['observed_locations'].append(state['location'])
            output.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    return report


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--seconds',type=int,default=600)
    parser.add_argument('--output',type=Path,default=Path('data/rom-live-validation.json'))
    args=parser.parse_args()
    print(json.dumps(observe(args.seconds,args.output),ensure_ascii=False,indent=2))
