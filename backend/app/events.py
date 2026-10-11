"""Conservative events: discontinuities establish a new baseline, never a burst."""
from datetime import datetime, timezone
from uuid import uuid4
from .models import State

PRIORITY={'BADGE_EARNED':90,'POKEMON_EVOLVED':80,'POKEMON_CAPTURED':70,'POKEMON_FAINTED':60,'POKEMON_LEVEL_UP':50}


def event(kind, before=None, after=None, pokemon=None, **meta):
    return dict(id=str(uuid4()),type=kind,timestamp=datetime.now(timezone.utc).isoformat(),
        pokemon=pokemon, before=before,after=after,metadata=meta,priority=PRIORITY.get(kind,10))


class EventEngine:
    def __init__(self):
        self.previous: State | None = None
        self.cooldowns={}

    def reset(self):
        self.previous=None
        self.cooldowns.clear()

    def compare(self, current: State):
        previous=self.previous
        self.previous=current if current.connection=='connected' else None
        if previous is None or self.previous is None: return []
        a,b=previous.extensions,current.extensions
        old={m.identity:m for m in previous.party}
        new={m.identity:m for m in current.party}
        discontinuity=(previous.source!=current.source or previous.rom_id!=current.rom_id or
            previous.trainer_id!=current.trainer_id or a.epoch!=b.epoch or b.frame<=a.frame or
            b.frame-a.frame>180 or current.sequence<=previous.sequence or
            (current.play_seconds or 0)<(previous.play_seconds or 0) or
            any(old[k].level>new[k].level for k in old.keys()&new.keys()) or
            not set(a.owned).issubset(b.owned) or
            any(x and not y for x,y in zip(previous.badges or [],current.badges or [])))
        if discontinuity:
            self.cooldowns.clear()
            return []
        result=[]
        def emit(kind,before=None,after=None,mon=None,**meta):
            key=(kind,mon.identity if mon else '',str(after))
            if b.frame-self.cooldowns.get(key,-100000)<180: return
            self.cooldowns[key]=b.frame
            result.append(event(kind,before,after,mon.model_dump() if mon else None,**meta))
        self.cooldowns={k:f for k,f in self.cooldowns.items() if b.frame-f<3600}
        if [m.identity for m in previous.party]!=[m.identity for m in current.party]:
            emit('PARTY_CHANGED',[m.identity for m in previous.party],[m.identity for m in current.party])
        for key in old.keys()&new.keys():
            p,n=old[key],new[key]
            if n.egg or p.egg: continue
            if n.species_id!=p.species_id: emit('POKEMON_EVOLVED',p.species,n.species,n)
            if n.level>p.level: emit('POKEMON_LEVEL_UP',p.level,n.level,n)
            if p.hp>0 and n.hp==0: emit('POKEMON_FAINTED',p.hp,0,n,confirmation_required=True)
            if p.status!=n.status: emit('STATUS_CHANGED',p.status,n.status,n)
        for i,(p,n) in enumerate(zip(previous.badges or [],current.badges or [])):
            if n and not p: emit('BADGE_EARNED',False,True,badge=i+1)
        if previous.location_code!=current.location_code:
            emit('LOCATION_CHANGED',previous.location,current.location)
        if previous.money!=current.money: emit('MONEY_CHANGED',previous.money,current.money)
        # B_OUTCOME_CAUGHT is 7. An added party member or a dex bit alone is NOT a capture.
        if a.in_battle and not b.in_battle and b.battle_outcome==7 and not b.battle_flags&8:
            added=[m for m in current.party if m.identity not in old]
            emit('POKEMON_CAPTURED',None,added[0].species if len(added)==1 else 'Enviado a una caja',
                added[0] if len(added)==1 else None, evidence='battle_outcome_7')
        return sorted(result,key=lambda e:-e['priority'])
