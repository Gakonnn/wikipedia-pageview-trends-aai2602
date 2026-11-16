"""Create a complete local delivery archive and an independent backup."""
from pathlib import Path
import argparse,hashlib,json,shutil,zipfile
ROOT=Path(__file__).resolve().parents[1]
output=ROOT/'output/Final_Project_Wikipedia_Trends_AAI-2602.zip'
paths=[]
for p in sorted(ROOT.rglob('*')):
 if not p.is_file():continue
 relative=p.relative_to(ROOT)
 if any(x in {'.git','.venv','__pycache__','qa','tmp'} for x in relative.parts):continue
 if p.suffix in {'.zip','.pyc','.part','.log'} or p.name=='.DS_Store':continue
 if relative.parts[0]=='output' and relative.parts[1]!='pdf':continue
 paths.append(p)
checks={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
(ROOT/'output/checksums.json').write_text(json.dumps(checks,indent=2))
with zipfile.ZipFile(output,'w',zipfile.ZIP_DEFLATED,compresslevel=5) as z:
 for p in paths:z.write(p,'Wikipedia_Trends_AAI-2602/'+str(p.relative_to(ROOT)))
 z.write(ROOT/'output/checksums.json','Wikipedia_Trends_AAI-2602/checksums.json')
with zipfile.ZipFile(output) as z:
 bad=z.testzip()
 if bad:raise RuntimeError(bad)
parser=argparse.ArgumentParser()
parser.add_argument('--backup',type=Path,help='Optional second copy of the archive')
backup=parser.parse_args().backup
if backup:
 backup.parent.mkdir(parents=True,exist_ok=True)
 shutil.copy2(output,backup)
print(json.dumps({'archive':str(output),'bytes':output.stat().st_size,'files':len(paths),'backup':str(backup)},indent=2))
