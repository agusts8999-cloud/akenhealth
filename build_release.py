"""Build a distributable from the current clean Git commit, on development."""
import argparse
import hashlib
import io
from pathlib import Path
import re
import subprocess
import tarfile
import tempfile
import zipfile

parser=argparse.ArgumentParser()
parser.add_argument('version')
parser.add_argument('destination',type=Path)
args=parser.parse_args()
if not re.fullmatch(r'\d+\.\d+\.\d+(?:-[a-z0-9]+)?',args.version):
    raise SystemExit('Invalid version')
root=Path(__file__).resolve().parent

def git(*args):return subprocess.check_output(['git','-C',str(root),*args])
if git('status','--porcelain').strip():
    raise SystemExit('Refusing to package a dirty working tree')
commit=git('rev-parse','HEAD').decode().strip()
args.destination.mkdir(parents=True,exist_ok=True)
with tempfile.TemporaryDirectory(prefix='chg-release-') as tmp:
    base=Path(tmp)
    with tarfile.open(fileobj=io.BytesIO(git('archive','--format=tar','HEAD'))) as archive:
        archive.extractall(base/'coding-health-guard',filter='data')
    (base/'coding-health-guard/SOURCE_COMMIT.txt').write_text(commit+'\n')
    prefix='coding-health-guard-'+args.version
    tarpath=args.destination/(prefix+'.tar.gz')
    with tarfile.open(tarpath,'w:gz') as archive:
        archive.add(base/'coding-health-guard',arcname='coding-health-guard')
    zippath=args.destination/(prefix+'.zip')
    with zipfile.ZipFile(zippath,'w',compression=zipfile.ZIP_DEFLATED) as archive:
        for item in sorted((base/'coding-health-guard').rglob('*')):
            if item.is_file():archive.write(item,item.relative_to(base))
    for path in (tarpath,zippath):
        digest=hashlib.sha256(path.read_bytes()).hexdigest()
        path.with_name(path.name+'.sha256').write_text(digest+'  '+path.name+'\n')
        print(path.name,digest)
print('Source commit:',commit)
