from backend.app.decoder import EmeraldDecoder
from backend.app.events import EventEngine
from tests.test_decoder import packet


def states(tmp_path):
    a=EmeraldDecoder(tmp_path).decode(packet())
    b=a.model_copy(deep=True);b.sequence+=1;b.extensions.frame+=15
    return a,b


def test_level_evolution_faint_identity(tmp_path):
    a,b=states(tmp_path);b.party[0].level=6;b.party[0].species='GROVYLE';b.party[0].species_id=278;b.party[0].hp=0
    engine=EventEngine();assert engine.compare(a)==[]
    result=engine.compare(b)
    assert {e['type'] for e in result}=={'POKEMON_LEVEL_UP','POKEMON_EVOLVED','POKEMON_FAINTED'}
    assert result[0]['priority']>=result[-1]['priority']
    assert engine.compare(b)==[]


def test_reset_load_and_disconnect_suppress(tmp_path):
    for mode in ('epoch','frame','time','level','badge','trainer'):
        a,b=states(tmp_path);b.money+=100
        if mode=='epoch':b.extensions.epoch+=1
        if mode=='frame':b.extensions.frame=0
        if mode=='time':b.play_seconds-=1
        if mode=='level':b.party[0].level-=1
        if mode=='badge':b.badges[0]=False
        if mode=='trainer':b.trainer_id='other'
        engine=EventEngine();engine.compare(a);assert engine.compare(b)==[]


def test_party_add_is_not_capture(tmp_path):
    a,b=states(tmp_path);b.party=[];b.caught+=1;b.extensions.owned=[1,2]
    engine=EventEngine();engine.compare(a)
    assert 'POKEMON_CAPTURED' not in {e['type'] for e in engine.compare(b)}


def test_capture_evidence_and_badges(tmp_path):
    a,b=states(tmp_path);a.extensions.in_battle=True;b.extensions.battle_outcome=7;b.badges[1]=True
    engine=EventEngine();engine.compare(a)
    assert {e['type'] for e in engine.compare(b)}=={'POKEMON_CAPTURED','BADGE_EARNED'}
