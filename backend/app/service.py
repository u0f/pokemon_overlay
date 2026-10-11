import asyncio
import json
import logging
import time
from datetime import datetime, timezone
from pathlib import Path
from .decoder import Gen3Decoder
from .events import EventEngine
from .models import Settings, State, Wire, Pokemon, EmeraldExtension
from .storage import Storage

log=logging.getLogger('pokestream')


class Service:
    def __init__(self,data:Path,adapter_port=8766):
        self.data=data
        self.store=Storage(data/'pokestream.sqlite3')
        self._settings=Settings.model_validate(self.store.get('settings'))
        self.decoder=Gen3Decoder(data)
        self.engine=EventEngine()
        self.state=State()
        self.clients=set()
        self.last_read=None
        self.errors=[]
        self.version=0
        self.last_wire=None
        self.adapter_port=adapter_port

    @property
    def settings(self): return self._settings

    @settings.setter
    def settings(self,value:Settings):
        self.store.put('settings',value.model_dump())
        self._settings=value

    def payload(self):
        return {'type':'state','state':self.state.model_dump(),'settings':self.settings.model_dump(),
            'profiles':self.store.get('profiles'),'events':self.store.events(),
            'nuzlocke':{'run':self.store.get('run'),'deaths':self.store.deaths()},'errors':self.errors[-10:]}

    def publish(self):
        # Per-browser queue is bounded; a slow OBS source never delays memory reading.
        payload=self.payload()
        for queue in self.clients:
            if queue.full(): queue.get_nowait()
            queue.put_nowait(payload)

    def diagnose(self,message):
        if not self.errors or self.errors[-1]['message']!=message:
            self.errors.append({'timestamp':datetime.now(timezone.utc).isoformat(),'message':message})
            self.errors=self.errors[-50:]
            log.warning(message)

    def disconnected(self,message,kind='disconnected'):
        self.engine.reset()
        if self.state.connection!=kind or self.state.message!=message:
            self.state=self.state.model_copy(update={'connection':kind,'message':message})
            self.publish()

    def accept(self,packet:Wire):
        state=self.decoder.decode(packet)
        for ev in self.engine.compare(state): self.store.record(ev,self.settings.nuzlocke)
        self.state=state
        self.last_wire=packet.model_dump()
        self.last_read=time.monotonic()
        self.publish()

    def demo(self,seq):
        self.state=State(game='Pokémon Esmeralda · España',game_id='emerald-es-r0',source='demo',connection='connected',message='DEMO · datos de ejemplo, sin emulador',
            trainer='DEMO',trainer_id='demo',sequence=seq,timestamp=datetime.now(timezone.utc).isoformat(),
            party=[Pokemon(identity='demo-1',slot=0,species_id=277,species='TREECKO',nickname='Brote',level=12,
                hp=29,max_hp=36,status='Sano',types=['Planta']),
                Pokemon(identity='demo-2',slot=1,species_id=280,species='TORCHIC',nickname='Chispa',level=11,
                hp=18,max_hp=32,status='Sano',types=['Fuego'])],
            badges=[True,False,False,False,False,False,False,False],location='Villa Raíz',location_code='demo',
            money=3000,play_seconds=7380,seen=14,caught=3,extensions=EmeraldExtension(frame=seq*30))
        for mon in self.state.party:
            sprite=self.decoder.catalog['species'].get(str(mon.species_id),{}).get('sprite')
            if sprite: mon.sprite=sprite if isinstance(sprite,str) else f'/assets/{mon.species_id}.png'
        self.publish()

    async def run(self):
        seq=0
        while True:
            if self.settings.demo:
                self.engine.reset()
                seq+=1; self.demo(seq)
                await asyncio.sleep(0.5)
                continue
            if self.state.source=='demo': self.state=State()
            writer=None
            try:
                reader,writer=await asyncio.wait_for(asyncio.open_connection('127.0.0.1',self.adapter_port,limit=12000),timeout=2)
                self.engine.reset()
                interval=None
                while not self.settings.demo:
                    if interval!=self.settings.interval_frames:
                        interval=self.settings.interval_frames
                        writer.write(f'INTERVAL {interval}\n'.encode())
                        await writer.drain()
                    raw=await asyncio.wait_for(reader.readline(),timeout=4)
                    if not raw: raise ConnectionError('mGBA desconectado')
                    try:
                        self.accept(Wire.model_validate_json(raw))
                    except (ValueError,TypeError,KeyError) as e:
                        message=str(e)[:200]
                        self.diagnose(message)
                        self.disconnected('Lectura rechazada. '+message,'error')
            except (OSError,ConnectionError,asyncio.TimeoutError,ValueError) as e:
                self.disconnected('Sin lecturas: abre mGBA, carga pokestream.lua y reanuda la emulación.')
                if not isinstance(e,(OSError,asyncio.TimeoutError)): self.diagnose(str(e))
            finally:
                if writer:
                    writer.close()
                    try: await writer.wait_closed()
                    except OSError: pass
            await asyncio.sleep(1)
