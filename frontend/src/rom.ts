export type RomGame={id:string;name:string;code:string;revision:number;sha1:string};
export type RomResult={status:'success'|'warning'|'error';title:string;message:string;game?:RomGame};

export async function checkRom(buffer:ArrayBuffer,games:RomGame[]):Promise<RomResult>{
  const bytes=new Uint8Array(buffer);
  if(bytes.length!==16*1024*1024)return {status:'error',title:'Tamaño de ROM incorrecto',message:'Los juegos compatibles ocupan 16 MB. Elige el archivo .gba original, sin comprimir.'};
  let checksum=0;
  for(let i=0xa0;i<=0xbc;i++)checksum=(checksum-bytes[i])&255;
  if(bytes[0xb2]!==0x96||((checksum-0x19)&255)!==bytes[0xbd])return {status:'error',title:'La cabecera no es válida',message:'El archivo puede estar incompleto o dañado. Prueba con otra copia de tu ROM original.'};
  const digest=await crypto.subtle.digest('SHA-1',buffer);
  const sha1=Array.from(new Uint8Array(digest),b=>b.toString(16).padStart(2,'0')).join('');
  const game=games.find(g=>g.sha1===sha1);
  if(game)return {status:'success',title:'ROM correcta y compatible',message:'El archivo coincide íntegramente con una ROM original reconocida. Puedes abrirlo en mGBA y conectar tu overlay.',game};
  const code=String.fromCharCode(...bytes.slice(0xac,0xb0));
  if(games.some(g=>g.code===code&&g.revision===bytes[0xbc]))return {status:'error',title:'La ROM no coincide con el original',message:'La cabecera se reconoce, pero el contenido ha cambiado. Puede ser una ROM modificada o dañada; PokeStream no puede validarla.'};
  return {status:'warning',title:'ROM no compatible con PokeStream',message:'La cabecera es válida, pero este juego, idioma o revisión no está reconocido. Esto no significa que no pueda funcionar en el emulador.'};
}

export function readRom(file:File):Promise<ArrayBuffer>{
  return new Promise((resolve,reject)=>{
    const reader=new FileReader();
    reader.onerror=()=>reject(Error('No se pudo leer el archivo. Vuelve a seleccionarlo.'));
    reader.onload=()=>resolve(reader.result as ArrayBuffer);
    reader.readAsArrayBuffer(file);
  });
}
