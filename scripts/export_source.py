"""Build a source-only archive from an explicit allowlist, never from the workspace."""
import re
import zipfile
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
FILES=['.gitignore','LICENSE','README.md','launcher.py','requirements.txt',
       'requirements-dev.txt','Instalar.cmd','Iniciar PokeStream.cmd',
       'frontend/index.html','frontend/package.json','frontend/package-lock.json','frontend/tsconfig.json',
       'frontend/vite.config.ts','bridge/mgba/pokestream.lua','roms/LEEME.txt',
       'assets/pokestream-logo.png','assets/pokestream.ico']
FOLDERS={'backend':{'.py'},'tests':{'.py'},'scripts':{'.py','.ps1'},
         'frontend/src':{'.ts','.tsx','.css'},'docs':{'.md'},'.github':{'.md','.yml','.yaml'}}
PATTERNS=[r'[A-Z]:[/\\]Users[/\\]',r'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----',
          r'(?:ghp_|github_pat_|sk-proj-)[A-Za-z0-9_]{20,}',
          r'AKIA[A-Z0-9]{16}',r'https?://[^/\s]+:[^/\s]+@']


def source_files(root):
    paths=[root/file for file in FILES]
    for folder,extensions in FOLDERS.items():
        paths.extend(p for p in (root/folder).rglob('*') if p.is_file()
                     and not p.is_symlink() and p.suffix in extensions
                     and not any(part.startswith('.') or part=='__pycache__'
                                 for part in p.relative_to(root/folder).parts))
    for path in sorted(set(paths)):
        if path.is_symlink(): raise ValueError(f'Enlace no permitido: {path.relative_to(root)}')
        if path.suffix in {'.png','.ico'}:
            yield path
            continue
        content=path.read_text('utf-8')
        if any(re.search(pattern,content) for pattern in PATTERNS):
            raise ValueError(f'Revisar información privada en {path.relative_to(root)}')
        yield path


def export(root=ROOT):
    files=list(source_files(root))
    destination=root/'dist'/'PokeStream-source.zip'
    destination.parent.mkdir(exist_ok=True)
    with zipfile.ZipFile(destination,'w',zipfile.ZIP_DEFLATED) as archive:
        for path in files: archive.write(path,path.relative_to(root).as_posix())
    print(f'Código público preparado: {len(files)} archivos en dist/PokeStream-source.zip')
    return destination


if __name__=='__main__': export()
