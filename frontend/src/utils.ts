export const labels:Record<string,string>={POKEMON_LEVEL_UP:'¡Un nivel más!',POKEMON_EVOLVED:'¡Ha evolucionado!',POKEMON_CAPTURED:'¡Pokémon capturado!',POKEMON_FAINTED:'Pokémon debilitado',BADGE_EARNED:'¡Nueva medalla!',PARTY_CHANGED:'Equipo actualizado',STATUS_CHANGED:'Cambio de estado',LOCATION_CHANGED:'Nueva ubicación',MONEY_CHANGED:'Dinero actualizado'};
export const componentNames:Record<string,string>={game:'Marco del juego',webcam:'Marco de webcam',party:'Equipo Pokémon',info:'Información de partida',badges:'Medallas',alerts:'Alertas'};
export function clock(seconds:number|null){if(seconds===null)return '—';return `${Math.floor(seconds/3600).toString().padStart(2,'0')}:${Math.floor(seconds/60)%60<10?'0':''}${Math.floor(seconds/60)%60}`}
export function hpPercent(hp:number,max:number){return max>0?Math.max(0,Math.min(100,hp/max*100)):0}
export function clamp(n:number,min:number,max:number){return Math.max(min,Math.min(max,n))}
