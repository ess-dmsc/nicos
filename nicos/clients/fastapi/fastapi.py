import asyncio
import datetime
import functools
import logging
import secrets
import threading
import time
from pathlib import Path
from typing import Any, Dict

from fastapi import (
    Depends,
    FastAPI,
    HTTPException,
    Request,
    WebSocket,
    WebSocketDisconnect,
)
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from pydantic import BaseModel, Field, PositiveInt

from nicos.clients.base import ConnectionData, NicosClient
from nicos.core.status import BUSY, DISABLED, ERROR, NOTREACHED, OK, UNKNOWN, WARN
from nicos.protocols.daemon import STATUS_IDLE, STATUS_IDLEEXC

_STATUS_CSS = {
    OK: "ok",
    BUSY: "busy",
    WARN: "warn",
    NOTREACHED: "err",
    DISABLED: "err",
    ERROR: "err",
    UNKNOWN: "unk",
}


JWT_SECRET = "CHANGE-ME-before-prod"
JWT_ALGORITHM = "HS256"
JWT_TTL_MINUTES = 60

LOG = logging.getLogger("nicos-bridge")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")


def create_jwt(data: dict, minutes: int = JWT_TTL_MINUTES) -> str:
    to_encode = data.copy()
    expire = datetime.datetime.now(datetime.UTC) + datetime.timedelta(minutes=minutes)
    to_encode["exp"] = expire
    return jwt.encode(to_encode, JWT_SECRET, algorithm=JWT_ALGORITHM)


def decode_jwt(token: str) -> dict:
    return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])


class BridgeClient(NicosClient):
    def __init__(self, loop: asyncio.AbstractEventLoop, log_func):
        super().__init__(log_func)
        self.loop = loop
        self.status = "idle"
        self.msg_queue: asyncio.Queue[str] = asyncio.Queue(maxsize=1_000)

    def _emit(self, line: str):
        self.loop.call_soon_threadsafe(
            functools.partial(self.msg_queue.put_nowait, line[:5000])
        )

    def signal(self, name, data=None, exc=None):
        if name == "status":
            st, _ = data
            self.status = "idle" if st in (STATUS_IDLE, STATUS_IDLEEXC) else "run"
        elif name == "message":
            src, ts, _lvl, txt = data[0], data[1], data[2], data[3]
            t = time.strftime("%H:%M:%S", time.localtime(ts))
            self._emit(f"[{t}] {src}: {txt.rstrip()}")
        elif name in ("broken", "disconnected"):
            LOG.warning("daemon event: %s", name)


app = FastAPI(title="NICOS web demo (JWT)", version="0.2.0")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/login")

_sessions: Dict[str, BridgeClient] = {}
_lock = threading.Lock()


def get_client(token: str = Depends(oauth2_scheme)) -> BridgeClient:
    try:
        payload = decode_jwt(token)
        sid = payload["sid"]
    except (JWTError, KeyError):
        raise HTTPException(status_code=401, detail="Invalid token")

    cli = _sessions.get(sid)
    if not cli or not cli.isconnected:
        raise HTTPException(status_code=503, detail="NICOS not connected")
    return cli


class LoginBody(BaseModel):
    host: str
    port: PositiveInt = Field(default=1301)
    user: str
    password: str
    viewonly: bool = False
    expertmode: bool = False


class CommandBody(BaseModel):
    command: str


class EvalBody(BaseModel):
    expr: str
    stringify: bool = True


class DeviceInfo(BaseModel):
    name: str
    value: Any
    status_code: int
    css: str
    status_text: str


STATIC_ROOT = Path(__file__).parent / "static"


@app.get("/", response_class=HTMLResponse)
def root():
    return FileResponse(STATIC_ROOT / "index.html")


@app.post("/api/login")
async def api_login(body: LoginBody):
    loop = asyncio.get_running_loop()
    cli = BridgeClient(loop, log_func=LOG.warning)
    cli.connect(
        ConnectionData(
            body.host,
            body.port,
            body.user,
            body.password,
            body.viewonly,
            body.expertmode,
        ),
        eventmask=("watch",),
    )
    if not cli.isconnected:
        raise HTTPException(401, "NICOS login failed")

    sid = secrets.token_hex(8)
    with _lock:
        _sessions[sid] = cli

    token = create_jwt({"sub": body.user, "sid": sid})
    LOG.info("NICOS session started for %s (sid=%s)", body.user, sid)
    return {"access_token": token, "token_type": "bearer"}


@app.post("/api/logout")
def api_logout(client: BridgeClient = Depends(get_client)):
    client.disconnect()
    for sid, c in list(_sessions.items()):
        if c is client:
            _sessions.pop(sid, None)
    return {"status": "bye"}


@app.get("/api/status")
def api_status(client: BridgeClient = Depends(get_client)):
    return {"status": client.status}


@app.get("/api/device/{dev}/value")
def api_dev_value(dev: str, client: BridgeClient = Depends(get_client)):
    val = client.getDeviceValue(dev)
    if val is None:
        raise HTTPException(404, f"Unknown device {dev}")
    return {"device": dev, "value": val}


@app.get("/api/devices", response_model=list[DeviceInfo])
def devices(client: BridgeClient = Depends(get_client)):
    out = []
    for dev in client.getDeviceList():
        val = client.getDeviceValue(dev)
        cache_entry = client.getCacheKey(dev.lower() + "/status")  # (ts, (code, txt))
        code, txt = cache_entry[1] if cache_entry else (UNKNOWN, "?")
        out.append(
            DeviceInfo(
                name=dev,
                value=val,
                status_code=code,
                css=_STATUS_CSS.get(code, "unk"),
                status_text=str(txt),
            )
        )
    return out


@app.post("/api/eval")
def api_eval(body: EvalBody, client: BridgeClient = Depends(get_client)):
    res = client.eval(body.expr, default="<error>", stringify=body.stringify)
    return {"result": res}


@app.post("/api/command")
def api_command(body: CommandBody, client: BridgeClient = Depends(get_client)):
    cmd = body.command.strip()
    if not cmd:
        raise HTTPException(400, "Empty command")
    if client.status == "idle":
        client.run(cmd)
    else:
        client.tell("exec", cmd)
    return {"sent": cmd}


async def _jwt_to_client(raw: str) -> BridgeClient | None:
    try:
        payload = decode_jwt(raw)
        return _sessions[payload["sid"]]
    except Exception:
        return None


@app.websocket("/ws")
async def ws_status(sock: WebSocket):
    await sock.accept()
    data = await sock.receive_json()
    client = await _jwt_to_client(data.get("token", ""))
    if not client:
        await sock.close(code=4401)
        return

    try:
        while True:
            await sock.send_json({"status": client.status})
            await asyncio.sleep(2)
    except WebSocketDisconnect:
        pass


@app.websocket("/ws/logs")
async def ws_logs(sock: WebSocket):
    await sock.accept()
    data = await sock.receive_json()
    client = await _jwt_to_client(data.get("token", ""))
    if not client:
        await sock.close(code=4401)
        return

    q = client.msg_queue
    try:
        while True:
            line = await q.get()
            await sock.send_text(line)
    except WebSocketDisconnect:
        pass
