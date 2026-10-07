
import os, json, time, threading, urllib.parse, urllib.request, socket
from pathlib import Path
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler

ROOT=Path(__file__).resolve().parent.parent
WEB=ROOT/"web"
PORT=int(os.environ.get("NEXUS_PORT","8080"))
NANO_HOST=os.environ.get("NEXUS_NANO_IP","").strip()

try:
    import cv2
except Exception:
    cv2=None

_camera=None
_camera_lock=threading.Lock()

def get_camera():
    global _camera
    if cv2 is None:
        return None
    with _camera_lock:
        if _camera is None or not _camera.isOpened():
            _camera=cv2.VideoCapture(0, cv2.CAP_DSHOW)
            if not _camera.isOpened():
                _camera=cv2.VideoCapture(0)
        return _camera if _camera is not None and _camera.isOpened() else None

def local_ip():
    s=socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8",80))
        return s.getsockname()[0]
    except Exception:
        return "127.0.0.1"
    finally:
        s.close()

def send_nano(command):
    if not NANO_HOST:
        return False
    try:
        u="http://"+NANO_HOST+"/command?c="+urllib.parse.quote(command)
        urllib.request.urlopen(u,timeout=.5).read()
        return True
    except Exception:
        return False

class Handler(SimpleHTTPRequestHandler):
    def __init__(self,*args,**kwargs):
        super().__init__(*args,directory=str(WEB),**kwargs)

    def json(self,obj,status=200):
        b=json.dumps(obj).encode()
        self.send_response(status)
        self.send_header("Content-Type","application/json")
        self.send_header("Cache-Control","no-store")
        self.send_header("Content-Length",str(len(b)))
        self.end_headers()
        self.wfile.write(b)

    def do_GET(self):
        path=urllib.parse.urlparse(self.path).path
        if path=="/api/status":
            cam=get_camera() is not None
            self.json({"ok":True,"pc_ip":local_ip(),"port":PORT,
                       "nano_configured":bool(NANO_HOST),
                       "nano_ip":NANO_HOST,"camera":cam})
            return
        if path=="/camera.mjpeg":
            cam=get_camera()
            if cam is None:
                self.json({"ok":False,"error":"USB camera unavailable"},503); return
            self.send_response(200)
            self.send_header("Content-Type","multipart/x-mixed-replace; boundary=frame")
            self.send_header("Cache-Control","no-cache")
            self.end_headers()
            try:
                while True:
                    with _camera_lock:
                        ok,frame=cam.read()
                    if not ok:
                        time.sleep(.1); continue
                    ok,jpg=cv2.imencode(".jpg",frame,[int(cv2.IMWRITE_JPEG_QUALITY),82])
                    if not ok: continue
                    b=jpg.tobytes()
                    self.wfile.write(b"--frame\r\nContent-Type: image/jpeg\r\nContent-Length: "+
                                     str(len(b)).encode()+b"\r\n\r\n"+b+b"\r\n")
                    self.wfile.flush()
                    time.sleep(.025)
            except (BrokenPipeError,ConnectionResetError):
                pass
            return
        super().do_GET()

    def do_POST(self):
        path=urllib.parse.urlparse(self.path).path
        n=int(self.headers.get("Content-Length","0"))
        try: body=json.loads(self.rfile.read(n) or b"{}")
        except Exception: body={}
        if path=="/api/command":
            c=str(body.get("command","stop"))
            ok=send_nano(c)
            self.json({"ok":True,"command":c,"nano_received":ok}); return
        if path=="/api/nano-ip":
            global NANO_HOST
            NANO_HOST=str(body.get("ip","")).strip()
            self.json({"ok":True,"nano_ip":NANO_HOST}); return
        self.json({"ok":False,"error":"Not found"},404)

if __name__=="__main__":
    print("\nNEXUS CAM - ORIGINAL UPGRADED")
    print("PC: http://localhost:%d"%PORT)
    print("Phone: http://%s:%d"%(local_ip(),PORT))
    print("Nano IP:",NANO_HOST or "not configured")
    print("Press Ctrl+C to stop.\n")
    ThreadingHTTPServer(("0.0.0.0",PORT),Handler).serve_forever()
