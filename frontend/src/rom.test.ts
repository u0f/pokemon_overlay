import {describe,it,expect,vi,afterEach} from 'vitest';
import {checkRom,readRom} from './rom';

const game={id:'emerald-es-r0',name:'Pokémon Esmeralda · España',code:'BPES',revision:0,sha1:'ab'.repeat(20)};
function rom(code='BPES'){
  const bytes=new Uint8Array(16*1024*1024);
  bytes.set(Array.from(code,c=>c.charCodeAt(0)),0xac);bytes[0xb2]=0x96;
  let sum=0;for(let i=0xa0;i<=0xbc;i++)sum-=bytes[i];bytes[0xbd]=(sum-0x19)&255;
  return bytes.buffer;
}
afterEach(()=>vi.unstubAllGlobals());
describe('ROM validation',()=>{
  it('rejects incomplete and invalid headers before hashing',async()=>{
    expect((await checkRom(new ArrayBuffer(128),[game])).status).toBe('error');
    expect((await checkRom(new ArrayBuffer(16*1024*1024),[game])).title).toContain('cabecera');
  });
  it('accepts only the complete known digest',async()=>{
    vi.stubGlobal('crypto',{subtle:{digest:vi.fn().mockResolvedValue(new Uint8Array(20).fill(0xab).buffer)}});
    expect((await checkRom(rom(),[game])).game).toEqual(game);
  });
  it('distinguishes changed originals from unsupported games',async()=>{
    vi.stubGlobal('crypto',{subtle:{digest:vi.fn().mockResolvedValue(new Uint8Array(20).buffer)}});
    expect((await checkRom(rom(),[game])).title).toContain('no coincide');
    expect((await checkRom(rom('BPEE'),[game])).status).toBe('warning');
  });
  it('propagates unreadable files without showing success',async()=>{
    class FailedReader{onerror:()=>void=()=>{};readAsArrayBuffer(){this.onerror()}}
    vi.stubGlobal('FileReader',FailedReader);
    await expect(readRom({} as File)).rejects.toThrow('No se pudo leer');
  });
});
