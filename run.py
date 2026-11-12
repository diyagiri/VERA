"""One-command local web app. Python 3.11+, no external dependencies."""
from pathlib import Path
from http.server import SimpleHTTPRequestHandler,ThreadingHTTPServer
import argparse,subprocess,sys
ROOT=Path(__file__).resolve().parent
class Handler(SimpleHTTPRequestHandler):
 def __init__(self,*args,**kwargs):super().__init__(*args,directory=str(ROOT/'dist'),**kwargs)
 def log_message(self,*args):pass
 def end_headers(self):
  self.send_header('Cache-Control','no-store')
  self.send_header('X-Content-Type-Options','nosniff')
  self.send_header('Referrer-Policy','no-referrer')
  super().end_headers()
if __name__=='__main__':
 parser=argparse.ArgumentParser();parser.add_argument('--port',type=int,default=8000);args=parser.parse_args()
 subprocess.run([sys.executable,str(ROOT/'scripts/build_web.py')],check=True)
 print(f'VERA: http://127.0.0.1:{args.port}  (Ctrl+C to stop)')
 with ThreadingHTTPServer(('127.0.0.1',args.port),Handler) as server:
  try:server.serve_forever()
  except KeyboardInterrupt:pass
