"""Executes the shipped Lua in Lua 5.4 with a strict read-only mGBA double.
This checks framing, not a substitute for a real mGBA gameplay session.
"""
import json
import pytest
from pathlib import Path
from lupa.lua54 import LuaRuntime
from backend.app.models import Wire
from backend.app.decoder import EmeraldDecoder
from tests.test_decoder import packet
from backend.app.games import GAMES


def runtime(game=GAMES[0]):
    lua=LuaRuntime(encoding=None)
    source=Path('bridge/mgba/pokestream.lua').read_bytes()
    from tests.test_games import game_packet
    p=game_packet(game)
    m=game.memory
    sb1=0x02025A00 if m['pointers'] else m['sb1']
    sb2=0x02024A54 if m['pointers'] else m['sb2']
    segments={0x080000AC:game.code.encode(),0x080000BC:bytes([game.revision]),
        m['count']:b'\1',m['party']:bytes.fromhex(p.party),
        sb1:bytes.fromhex(p.save1),sb2:bytes.fromhex(p.save2),
        sb1+m['flags']:bytes.fromhex(p.flags),sb1+m['seen1']:bytes.fromhex(p.seen1),
        sb1+m['seen2']:bytes.fromhex(p.seen2),m['header']:bytes(28),m['battle']:b'\0',
        m['outcome']:b'\0',m['battle_flags']:bytes(4)}
    if m['pointers']:
        segments[m['sb1']]=sb1.to_bytes(4,'little')
        segments[m['sb2']]=sb2.to_bytes(4,'little')
    if m['key']: segments[sb2+m['key']]=(0xAABBCCDD).to_bytes(4,'little')
    def read(address,length):
        data=segments[address]
        assert len(data)==length
        return data
    lua.globals()[b'readMemory']=read
    lua.globals()[b'crcBytes']=bytes.fromhex(game.crc32)
    lua.execute(b'''
        frame=60; calls={}; removed={}; output=''; blocked=false; maxSend=100000
        emu={}
        function emu:readRange(a,n) return readMemory(a,n) end
        function emu:read8(a) return string.byte(readMemory(a,1)) end
        function emu:read32(a) return string.unpack('<I4',readMemory(a,4)) end
        function emu:currentFrame() return frame end
        function emu:checksum(c) return crcBytes end
        console={log=function() end,error=function(_,msg) error(msg) end}
        C={CHECKSUM={CRC32=0}}
        callbacks={add=function(_,name,fn) calls[name]=fn; return name end,
            remove=function(_,id) removed[id]=true end}
        client={}
        function client:add(name,fn) self[name]=fn end
        function client:close() self.closed=true end
        function client:receive(n) local r=input;input=nil;return r,'again' end
        function client:send(s)
            if blocked then return nil,'again' end
            local n=math.min(#s,maxSend);output=output..s:sub(1,n);return n
        end
        server={}
        function server:listen() return 0 end
        function server:add(name,fn) self[name]=fn end
        function server:accept() return client end
        function server:close() self.closed=true end
        socket={ERRORS={AGAIN='again'},bind=function(host,port)
            assert(host=='127.0.0.1' and port==8766);return server end}
    ''')
    lua.execute(source)
    lua.execute(b'server.received()')
    return lua


@pytest.mark.parametrize('game', GAMES, ids=lambda g:g.id)
def test_lua_snapshot_decodes(tmp_path, game):
    lua=runtime(game)
    lua.execute(b'for i=1,15 do frame=frame+1;calls.frame() end')
    raw=lua.globals()[b'output']
    p=Wire.model_validate_json(raw)
    state=EmeraldDecoder(tmp_path).decode(p)
    assert state.trainer=='ALBA' and state.party[0].hp==20 and state.money==3000
    assert state.game_id==game.id


def test_partial_sends_and_backpressure():
    lua=runtime()
    lua.execute(b'blocked=true;for i=1,100 do calls.frame() end')
    assert lua.globals()[b'output']==b''
    assert len(lua.globals()[b'PokeStream'][b'pending'])<12000
    lua.execute(b'blocked=false;maxSend=127;for i=1,100 do calls.frame() end')
    lines=lua.globals()[b'output'].split(b'\n')[:-1]
    assert lines
    for line in lines:Wire.model_validate_json(line)


def test_interval_and_reset():
    lua=runtime()
    lua.execute(b"input='INTERVAL 30\\n';client.received();calls.reset()")
    assert lua.globals()[b'PokeStream'][b'interval']==30
    epoch=lua.globals()[b'PokeStream'][b'epoch']
    lua.execute(b"input='INTERVAL 1\\n';client.received()")
    assert lua.globals()[b'PokeStream'][b'interval']==30 and epoch>=2
