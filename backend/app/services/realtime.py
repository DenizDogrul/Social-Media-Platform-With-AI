from collections import defaultdict
from fastapi import WebSocket


class NotificationHub:
    def __init__(self) -> None:
        self._connections: dict[int, set[WebSocket]] = defaultdict(set)

    async def connect(self, user_id: int, websocket: WebSocket) -> None:
        await websocket.accept()
        self._connections[user_id].add(websocket)

    def disconnect(self, user_id: int, websocket: WebSocket) -> None:
        if user_id in self._connections:
            self._connections[user_id].discard(websocket)
            if not self._connections[user_id]:
                del self._connections[user_id]

    async def send_to_user(self, user_id: int, payload: dict) -> None:
        sockets = list(self._connections.get(user_id, []))
        for socket in sockets:
            try:
                await socket.send_json(payload)
            except Exception:
                self.disconnect(user_id, socket)


class AmbientHub:
    def __init__(self) -> None:
        self._connections: set[WebSocket] = set()
        self._latest_lux: float | None = None

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        self._connections.add(websocket)

    def disconnect(self, websocket: WebSocket) -> None:
        self._connections.discard(websocket)

    def latest_lux(self) -> float | None:
        return self._latest_lux

    async def broadcast_lux(self, lux: float, source: str = "sensor") -> None:
        self._latest_lux = lux
        payload = {"type": "lux", "lux": lux, "source": source}
        sockets = list(self._connections)
        for socket in sockets:
            try:
                await socket.send_json(payload)
            except Exception:
                self.disconnect(socket)


notification_hub = NotificationHub()
ambient_hub = AmbientHub()


class MessageHub:
    def __init__(self) -> None:
        self._connections: dict[int, set[WebSocket]] = defaultdict(set)

    async def connect(self, user_id: int, websocket: WebSocket) -> None:
        await websocket.accept()
        self._connections[user_id].add(websocket)

    def disconnect(self, user_id: int, websocket: WebSocket) -> None:
        if user_id in self._connections:
            self._connections[user_id].discard(websocket)
            if not self._connections[user_id]:
                del self._connections[user_id]

    async def send_to_user(self, user_id: int, payload: dict) -> None:
        sockets = list(self._connections.get(user_id, []))
        for socket in sockets:
            try:
                await socket.send_json(payload)
            except Exception:
                self.disconnect(user_id, socket)


message_hub = MessageHub()
