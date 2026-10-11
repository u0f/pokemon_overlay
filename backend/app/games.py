"""Exact Spanish Gen III ROM profiles. Evidence and validation limits: docs/MEMORY.md."""
from dataclasses import dataclass


@dataclass(frozen=True)
class Game:
    id: str
    name: str
    code: str
    revision: int
    crc32: str
    sha1: str
    family: str
    locations: int
    location_count: int

    @property
    def memory(self):
        return LAYOUTS[self.family]


LAYOUTS = {
    'emerald': dict(sb1=0x03005D8C, sb2=0x03005D90, pointers=True,
        size1=0x3D88, size2=0xF2C, count=0x020244E9, party=0x020244EC,
        money=0x490, key=0xAC, flags=0x1270, badge=0x867,
        seen1=0x988, seen2=0x3B24, header=0x02037318,
        battle=0x030026F9, outcome=0x0202433A, battle_flags=0x02022FEC),
    'rs': dict(sb1=0x02025734, sb2=0x02024EA4, pointers=False,
        size1=0x3AC0, size2=0x890, count=0x03004360, party=0x03004370,
        money=0x490, key=0, flags=0x1220, badge=0x807,
        seen1=0x938, seen2=0x3A8C, header=0x0202E828,
        battle=0x03001BAD, outcome=0x02024D26, battle_flags=0x020239F8),
    'frlg': dict(sb1=0x03004F58, sb2=0x03004F5C, pointers=True,
        size1=0x3D68, size2=0xF24, count=0x02024029, party=0x02024284,
        money=0x290, key=0xF20, flags=0xEE0, badge=0x820,
        seen1=0x5F8, seen2=0x3A18, header=0x02036DFC,
        battle=0x03003479, outcome=0x02023E8A, battle_flags=0x02022B4C),
}

GAMES = (
    Game('emerald-es-r0', 'Esmeralda', 'BPES', 0, '8c4d3108', 'fe1558a3dcb0360ab558969e09b690888b846dd9', 'emerald', 0x085A41E4, 213),
    Game('ruby-es-r0', 'Rubí', 'AXVS', 0, 'eb0729cf', '1f49f7289253dcbfecbc4c5ba3e67aa0652ec83c', 'rs', 0x083EB370, 88),
    Game('ruby-es-r1', 'Rubí', 'AXVS', 1, 'b980fff5', '9ac73481d7f5d150a018309bba91d185ce99fb7c', 'rs', 0x083EB370, 88),
    Game('sapphire-es-r0', 'Zafiro', 'AXPS', 0, 'a04f5f0b', '3a6489189e581c4b29914071b79207883b8c16d8', 'rs', 0x083EB0AC, 88),
    Game('sapphire-es-r1', 'Zafiro', 'AXPS', 1, 'f2c88931', '0fe9ad1e602e2fafa090aee25e43d6980625173c', 'rs', 0x083EB0A4, 88),
    Game('firered-es-r0', 'Rojo Fuego', 'BPRS', 0, '9f08064e', 'ab8f6bfe0ccdaf41188cd015c8c74c314d02296a', 'frlg', 0x083EBF80, 109),
    Game('leafgreen-es-r0', 'Verde Hoja', 'BPGS', 0, '2ca11d59', 'f9ebee5d228cb695f18ef2ced41630a09fa9eb05', 'frlg', 0x083EBDBC, 109),
)


def identify(code, revision, crc32):
    for game in GAMES:
        if (game.code, game.revision, game.crc32) == (code, revision, crc32):
            return game
    raise ValueError(f'ROM no compatible: {code} rev. {revision}, CRC32 {crc32}. Se requieren originales españoles reconocidos.')
