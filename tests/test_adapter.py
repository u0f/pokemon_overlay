import asyncio
import contextlib
from backend.app.service import Service
from tests.test_decoder import packet


def test_fragmented_tcp_reconnect_and_bad_read(tmp_path):
    async def run():
        connections=0
        commands=[]
        async def fake_emulator(reader,writer):
            nonlocal connections
            connections+=1
            commands.append(await reader.readline())
            p=packet();p.epoch=connections
            data=(p.model_dump_json()+'\n').encode()
            writer.write(data[:37]);await writer.drain()
            await asyncio.sleep(.02)
            writer.write(data[37:]);await writer.drain()
            if connections==1:
                await asyncio.sleep(.05)
                p.party='00'
                writer.write((p.model_dump_json()+'\n').encode());await writer.drain()
                await asyncio.sleep(.05)
            else:
                await asyncio.sleep(.1)
            writer.close();await writer.wait_closed()
        server=await asyncio.start_server(fake_emulator,'127.0.0.1',0)
        service=Service(tmp_path,server.sockets[0].getsockname()[1])
        task=asyncio.create_task(service.run())
        try:
            for _ in range(200):
                if connections>=2 and service.state.connection=='connected':break
                await asyncio.sleep(.01)
            assert connections>=2 and service.state.party[0].hp==20
            assert commands==[b'INTERVAL 15\n',b'INTERVAL 15\n']
            assert any('parcial' in e['message'] for e in service.errors)
            assert service.store.events()==[]
        finally:
            task.cancel()
            with contextlib.suppress(asyncio.CancelledError):await task
            server.close();await server.wait_closed()
            await asyncio.sleep(.15)
            service.store.db.close()
    asyncio.run(run())
