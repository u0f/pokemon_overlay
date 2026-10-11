import {useRef,useState} from 'react';
import {checkRom,readRom} from './rom';
import type {RomGame,RomResult} from './rom';

export function RomCheck(){
  const input=useRef<HTMLInputElement>(null);
  const [busy,setBusy]=useState(false);
  const [filename,setFilename]=useState('');
  const [result,setResult]=useState<RomResult|null>(null);
  async function test(file?:File){
    if(!file)return;
    setFilename(file.name);setResult(null);setBusy(true);
    try{
      if(!/\.gba$/i.test(file.name))throw Error('Elige un archivo .gba. Si está en un ZIP, extráelo primero.');
      if(file.size!==16*1024*1024)throw Error('El archivo debe ocupar 16 MB. Puede estar incompleto o comprimido.');
      const response=await fetch('/api/games');
      if(!response.ok)throw Error('No se pudo consultar la compatibilidad. Comprueba que PokeStream esté abierto y vuelve a probar.');
      const games:RomGame[]=await response.json();
      setResult(await checkRom(await readRom(file),games));
    }catch(e){setResult({status:'error',title:'No se pudo validar la ROM',message:e instanceof TypeError?'No se pudo completar la comprobación. Comprueba la conexión con PokeStream y usa un navegador actualizado.':e instanceof Error?e.message:'Vuelve a seleccionar el archivo.'})}
    finally{setBusy(false)}
  }
  return <section className="panel padded rom-check" aria-labelledby="rom-heading">
    <div className="rom-check-heading"><div><div className="eyebrow">ANTES DE EMPEZAR</div><h2 id="rom-heading">Comprueba tu ROM</h2><p>Elige tu juego y comprueba que el archivo esté completo y sea compatible con el overlay.</p></div><span className="rom-local">100% local</span></div>
    <div className="rom-picker"><span className="rom-file-icon" aria-hidden="true"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5"><path d="M5 3h9l5 5v13H5zM14 3v6h5M8 14h8M8 17h5"/></svg></span><div><strong>{filename||'Tu archivo Pokémon .gba'}</strong><p>{busy?'Comprobando el archivo completo…':'Esmeralda, Rubí, Zafiro, Rojo Fuego o Verde Hoja en español'}</p></div><button className="button primary" disabled={busy} onClick={()=>input.current?.click()}>{busy?'Comprobando…':'Probar ROM'}</button><input ref={input} type="file" accept=".gba" style={{display:'none'}} aria-label="Seleccionar ROM para comprobar" onChange={e=>{const file=e.target.files?.[0];e.target.value='';void test(file)}}/></div>
    <div className="rom-result-area" role="status" aria-live="polite" aria-atomic="true" aria-busy={busy}>
      {busy?<p className="rom-progress">Revisando tamaño, cabecera e integridad. Un momento…</p>:result?<div className={`rom-result ${result.status}`}><span className="rom-result-symbol" aria-hidden="true">{result.status==='success'?'✓':result.status==='warning'?'!':'×'}</span><div><h3>{result.title}</h3>{result.game&&<p className="rom-game-name">{result.game.name} · Revisión {result.game.revision}</p>}<p>{result.message}</p>{result.status==='success'&&<p className="rom-next-step"><strong>Siguiente paso:</strong> coloca el archivo en la carpeta roms, reinicia PokeStream y abre el juego en mGBA.</p>}</div></div>:<div className="rom-checks"><span>01 · Archivo completo</span><span>02 · ROM original</span><span>03 · Juego compatible</span></div>}
    </div><p className="rom-privacy">El archivo se revisa en este navegador. No se sube ni se modifica. Esta prueba verifica la ROM; no prueba tu partida guardada ni ejecuta el juego.</p>
  </section>;
}
