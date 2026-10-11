export interface Pokemon {identity:string;slot:number;species_id:number;species:string;nickname:string;level:number;hp:number;max_hp:number;status:string;types:string[];sprite:string|null;egg:boolean;shiny:boolean;form:string}
export interface State {game:string;game_id:string;rom_id:string|null;revision:number|null;console:string;emulator:string;source:'demo'|'real';connection:'connected'|'disconnected'|'waiting'|'error';message:string;timestamp:string|null;sequence:number;trainer:string|null;trainer_id:string|null;party:Pokemon[];badges:boolean[]|null;location:string|null;location_code:string|null;money:number|null;play_seconds:number|null;seen:number|null;caught:number|null}
export interface Component {x:number;y:number;width:number;height:number;visible:boolean}
export interface Profile {name:string;theme:'modern'|'retro'|'neon';resolution:'1920x1080'|'2560x1440';accent:string;opacity:number;components:Record<string,Component>}
export interface Settings {demo:boolean;interval_frames:number;alerts:boolean;alert_seconds:number;nuzlocke:boolean;disconnect_indicator:boolean}
export interface Event {id:string;type:string;timestamp:string;pokemon:Pokemon|null;before:unknown;after:unknown;metadata:Record<string,unknown>;priority:number}
export interface Death {id:string;run:string;status:'pending'|'confirmed'|'dismissed';event:Event}
export interface Payload {type:'state';state:State;settings:Settings;profiles:Record<string,Profile>;events:Event[];nuzlocke:{run:string;deaths:Death[]};errors:{message:string;timestamp:string}[]}
