from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator


class Model(BaseModel):
    model_config = ConfigDict(extra='forbid')


class Pokemon(Model):
    identity: str
    slot: int = Field(ge=0, le=5)
    species_id: int = Field(ge=1, le=439)
    species: str
    nickname: str
    level: int = Field(ge=1, le=100)
    hp: int = Field(ge=0, le=999)
    max_hp: int = Field(ge=1, le=999)
    status: str
    types: list[str] = Field(max_length=2)
    sprite: str | None = None
    egg: bool = False
    shiny: bool = False
    form: str = 'normal'

    @model_validator(mode='after')
    def check_hp(self):
        if self.hp > self.max_hp:
            raise ValueError('PS superiores al máximo')
        return self


class EmeraldExtension(Model):
    in_battle: bool = False
    battle_outcome: int = 0
    battle_flags: int = 0
    owned: list[int] = Field(default_factory=list)
    epoch: int = 0
    frame: int = 0


class State(Model):
    game: str = 'Juego pendiente'
    game_id: str = 'unknown'
    rom_id: str | None = None
    revision: int | None = None
    console: str = 'GBA'
    emulator: str = 'mGBA'
    source: Literal['real', 'demo'] = 'real'
    connection: Literal['disconnected', 'waiting', 'connected', 'error'] = 'disconnected'
    message: str = 'Abre mGBA y carga el script de conexión.'
    timestamp: str | None = None
    sequence: int = 0
    trainer: str | None = None
    trainer_id: str | None = None
    party: list[Pokemon] = Field(default_factory=list, max_length=6)
    badges: list[bool] | None = None
    location: str | None = None
    location_code: str | None = None
    money: int | None = Field(default=None, ge=0, le=999999)
    play_seconds: int | None = Field(default=None, ge=0)
    seen: int | None = Field(default=None, ge=0, le=386)
    caught: int | None = Field(default=None, ge=0, le=386)
    extensions: EmeraldExtension = Field(default_factory=EmeraldExtension)


class Wire(Model):
    protocol: Literal[1]
    code: str = Field(max_length=12)
    crc32: str = Field(pattern=r'^[0-9a-f]{8}$')
    revision: int = Field(ge=0, le=255)
    sequence: int = Field(ge=0)
    epoch: int = Field(ge=0)
    frame: int = Field(ge=0)
    ready: bool
    party_count: int = Field(ge=0, le=6)
    party: str = Field(max_length=1200, pattern=r'^[0-9a-f]*$')
    save1: str = Field(max_length=2400, pattern=r'^[0-9a-f]*$')
    save2: str = Field(max_length=352, pattern=r'^[0-9a-f]*$')
    flags: str = Field(max_length=600, pattern=r'^[0-9a-f]*$')
    seen1: str = Field(max_length=104, pattern=r'^[0-9a-f]*$')
    seen2: str = Field(max_length=104, pattern=r'^[0-9a-f]*$')
    map_header: str = Field(max_length=56, pattern=r'^[0-9a-f]*$')
    in_battle: bool
    battle_outcome: int = Field(ge=0, le=255)
    battle_flags: int = Field(ge=0, le=4294967295)
    money_key: int | None = Field(default=None, ge=0, le=4294967295)


class Component(Model):
    x: float = Field(ge=0, le=1920)
    y: float = Field(ge=0, le=1080)
    width: float = Field(ge=80, le=1920)
    height: float = Field(ge=40, le=1080)
    visible: bool = True


def layout():
    return {
        'game': Component(x=40, y=100, width=1280, height=854),
        'webcam': Component(x=1360, y=100, width=520, height=290),
        'party': Component(x=1360, y=420, width=520, height=500),
        'info': Component(x=40, y=20, width=1280, height=64),
        'badges': Component(x=1360, y=950, width=520, height=80),
        'alerts': Component(x=380, y=840, width=600, height=100),
    }


class Profile(Model):
    name: str = Field(default='Mi emisión', min_length=1, max_length=60)
    theme: Literal['modern', 'retro', 'neon'] = 'modern'
    resolution: Literal['1920x1080', '2560x1440'] = '1920x1080'
    accent: str = Field(default='#55edb0', pattern=r'^#[0-9a-fA-F]{6}$')
    opacity: float = Field(default=0.94, ge=0, le=1)
    components: dict[str, Component] = Field(default_factory=layout)

    @model_validator(mode='after')
    def check_layout(self):
        if set(self.components) != set(layout()):
            raise ValueError('Componentes de perfil desconocidos o ausentes')
        for c in self.components.values():
            if c.x + c.width > 1920 or c.y + c.height > 1080:
                raise ValueError('Componente fuera del lienzo')
        return self


class Settings(Model):
    demo: bool = False
    interval_frames: int = Field(default=15, ge=6, le=60)
    alerts: bool = True
    alert_seconds: int = Field(default=5, ge=1, le=20)
    nuzlocke: bool = False
    disconnect_indicator: bool = True
