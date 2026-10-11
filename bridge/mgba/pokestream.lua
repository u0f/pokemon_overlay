-- PokeStream / Spanish Gen III. Read-only bridge. See docs/MEMORY.md.
-- BEGIN GENERATED PROFILES
local profiles = {
    ['8c4d3108'] = {code='BPES', revision=0, sb1=50355596, sb2=50355600, pointers=true, size1=15752, size2=3884, count=33703145, party=33703148, money=1168, key=172, flags=4720, badge=2151, seen1=2440, seen2=15140, header=33780504, battle=50341625, outcome=33702714, battle_flags=33697772},
    ['eb0729cf'] = {code='AXVS', revision=0, sb1=33707828, sb2=33705636, pointers=false, size1=15040, size2=2192, count=50348896, party=50348912, money=1168, key=0, flags=4640, badge=2055, seen1=2360, seen2=14988, header=33744936, battle=50338733, outcome=33705254, battle_flags=33700344},
    ['b980fff5'] = {code='AXVS', revision=1, sb1=33707828, sb2=33705636, pointers=false, size1=15040, size2=2192, count=50348896, party=50348912, money=1168, key=0, flags=4640, badge=2055, seen1=2360, seen2=14988, header=33744936, battle=50338733, outcome=33705254, battle_flags=33700344},
    ['a04f5f0b'] = {code='AXPS', revision=0, sb1=33707828, sb2=33705636, pointers=false, size1=15040, size2=2192, count=50348896, party=50348912, money=1168, key=0, flags=4640, badge=2055, seen1=2360, seen2=14988, header=33744936, battle=50338733, outcome=33705254, battle_flags=33700344},
    ['f2c88931'] = {code='AXPS', revision=1, sb1=33707828, sb2=33705636, pointers=false, size1=15040, size2=2192, count=50348896, party=50348912, money=1168, key=0, flags=4640, badge=2055, seen1=2360, seen2=14988, header=33744936, battle=50338733, outcome=33705254, battle_flags=33700344},
    ['9f08064e'] = {code='BPRS', revision=0, sb1=50351960, sb2=50351964, pointers=true, size1=15720, size2=3876, count=33701929, party=33702532, money=656, key=3872, flags=3808, badge=2080, seen1=1528, seen2=14872, header=33779196, battle=50345081, outcome=33701514, battle_flags=33696588},
    ['2ca11d59'] = {code='BPGS', revision=0, sb1=50351960, sb2=50351964, pointers=true, size1=15720, size2=3876, count=33701929, party=33702532, money=656, key=3872, flags=3808, badge=2080, seen1=1528, seen2=14872, header=33779196, battle=50345081, outcome=33701514, battle_flags=33696588},
}
-- END GENERATED PROFILES
-- Python is the TCP client because socket.connect blocks in mGBA 0.10.
if PokeStream then PokeStream.stop() end
local P = {client=nil, server=nil, ids={}, sequence=0, epoch=0, ticks=0,
    interval=15, pending='', input='', code='', crc='00000000', revision=0}
PokeStream = P
local function hex(s)
    return (s:gsub('.', function(c) return string.format('%02x', string.byte(c)) end))
end
local function closeClient()
    if P.client then P.client:close() end
    P.client=nil; P.pending=''; P.input=''
end
function P.stop()
    closeClient()
    if P.server then P.server:close() end
    for _,id in ipairs(P.ids) do callbacks:remove(id) end
end
local function identify()
    P.epoch=P.epoch+1
    if not emu then P.code=''; return end
    P.code=emu:readRange(0x080000AC,4)
    if not P.code:match('^[A-Z0-9]+$') then P.code='UNKNOWN' end
    P.crc=hex(emu:checksum(C.CHECKSUM.CRC32))
    P.revision=emu:read8(0x080000BC)
    console:log('PokeStream: '..P.code..' rev '..P.revision..' CRC '..P.crc)
end
local function flush()
    if not P.client or #P.pending==0 then return end
    local n,err=P.client:send(P.pending)
    if n then P.pending=P.pending:sub(n+1)
    elseif err~=socket.ERRORS.AGAIN then closeClient() end
end
local function readInput()
    if not P.client then return end
    local chunk,err=P.client:receive(128)
    if not chunk then
        if err~=socket.ERRORS.AGAIN then closeClient() end
        return
    end
    P.input=P.input..chunk
    if #P.input>256 then closeClient(); return end
    local line,rest=P.input:match('^(.-)\n(.*)$')
    if line then
        P.input=rest
        local n=tonumber(line:match('^INTERVAL (%d+)$'))
        if n and n>=6 and n<=60 then P.interval=n end
    end
end
local function tick()
    P.ticks=P.ticks+1
    flush()
    if not P.client or #P.pending>0 or P.ticks%P.interval~=0 or not emu then return end
    local layout=profiles[P.crc]
    local supported=layout and P.code==layout.code and P.revision==layout.revision
    local sb1,sb2,count=0,0,0
    if supported then
        sb1=layout.pointers and emu:read32(layout.sb1) or layout.sb1
        sb2=layout.pointers and emu:read32(layout.sb2) or layout.sb2
        count=emu:read8(layout.count)
    end
    local ready=not not (supported and sb1>=0x02000000 and sb1+layout.size1<=0x02040000
        and sb2>=0x02000000 and sb2+layout.size2<=0x02040000 and count<=6)
    layout=layout or profiles['8c4d3108']
    local function read(addr,len) if ready then return hex(emu:readRange(addr,len)) end return '' end
    P.sequence=P.sequence+1
    P.pending=string.format(
        '{"protocol":1,"code":"%s","crc32":"%s","revision":%d,"sequence":%d,"epoch":%d,"frame":%d,"ready":%s,"party_count":%d,"party":"%s","save1":"%s","save2":"%s","flags":"%s","seen1":"%s","seen2":"%s","map_header":"%s","in_battle":%s,"battle_outcome":%d,"battle_flags":%d,"money_key":%d}\n',
        P.code,P.crc,P.revision,P.sequence,P.epoch,emu:currentFrame(),tostring(ready),math.min(count,6),
        read(layout.party,600),read(sb1,layout.money+4),read(sb2,0xB0),read(sb1+layout.flags,300),
        read(sb1+layout.seen1,52),read(sb1+layout.seen2,52),read(layout.header,28),
        tostring(ready and (emu:read8(layout.battle)&2)~=0),
        ready and emu:read8(layout.outcome) or 0,ready and emu:read32(layout.battle_flags) or 0,
        ready and layout.key~=0 and emu:read32(sb2+layout.key) or 0)
    flush()
end
local err
P.server,err=socket.bind('127.0.0.1',8766)
if not P.server then console:error('PokeStream: '..tostring(err)); return end
local ok
ok,err=P.server:listen()
if not ok then P.server:close(); console:error(tostring(err)); return end
P.server:add('received',function()
    local client=P.server:accept()
    if not client then return end
    closeClient(); P.client=client
    client:add('error',closeClient); client:add('received',readInput)
    P.epoch=P.epoch+1
    console:log('PokeStream: backend conectado')
end)
P.ids[#P.ids+1]=callbacks:add('frame',tick)
P.ids[#P.ids+1]=callbacks:add('start',identify)
P.ids[#P.ids+1]=callbacks:add('reset',identify)
if emu then identify() end
console:log('PokeStream listo en 127.0.0.1:8766')
