"""Start or reuse a local Streamlit server, detached from the terminal."""
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from urllib.request import urlopen
ROOT=Path(__file__).resolve().parents[1]
PORT=8504
URL=f'http://127.0.0.1:{PORT}'
def healthy():
 try:
  with urlopen(URL+'/_stcore/health',timeout=2) as r:return r.status==200
 except OSError:return False
if not healthy():
 (ROOT/'qa').mkdir(exist_ok=True)
 with (ROOT/'qa/dashboard.log').open('a') as log:
  process=subprocess.Popen([sys.executable,'-m','streamlit','run','app.py','--server.address=127.0.0.1',f'--server.port={PORT}','--server.headless=true','--browser.gatherUsageStats=false'],cwd=ROOT,stdout=log,stderr=log,stdin=subprocess.DEVNULL,start_new_session=True)
 for _ in range(30):
  if healthy():break
  if process.poll() is not None:raise RuntimeError('Server exited; inspect qa/dashboard.log')
  time.sleep(.5)
 else:raise RuntimeError('Server did not become healthy')
 (ROOT/'qa/dashboard_server.json').write_text(json.dumps({'pid':process.pid,'url':URL},indent=2),encoding='utf-8')
print(URL)
