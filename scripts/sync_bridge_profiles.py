"""Embed the Python registry in the standalone Lua file (no runtime dependencies)."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from backend.app.games import GAMES


def table():
    rows = ['-- BEGIN GENERATED PROFILES', 'local profiles = {']
    for game in GAMES:
        fields = dict(code=game.code, revision=game.revision, **game.memory)
        values = []
        for key, value in fields.items():
            encoded = str(value).lower() if isinstance(value, bool) else repr(value)
            values.append(f'{key}={encoded}')
        rows.append(f"    ['{game.crc32}'] = {{" + ', '.join(values) + '},')
    return '\n'.join(rows + ['}', '-- END GENERATED PROFILES'])


if __name__ == '__main__':
    path = Path(__file__).resolve().parents[1]/'bridge/mgba/pokestream.lua'
    source = path.read_text('utf-8')
    start = source.index('-- BEGIN GENERATED PROFILES')
    end = source.index('-- END GENERATED PROFILES') + len('-- END GENERATED PROFILES')
    path.write_text(source[:start] + table() + source[end:], encoding='utf-8')
