from collections import defaultdict
from typing import Any


class ConnectionManager:
    def __init__(self):
        self.rooms = defaultdict(list)

    async def connect(self, room: int, websocket):
        await websocket.accept()
        self.rooms[room].append(websocket)

    def disconnect(self, room: int, websocket):
        if websocket in self.rooms[room]:
            self.rooms[room].remove(websocket)

    async def broadcast(self, room: int, payload: dict[str, Any]):
        for ws in list(self.rooms.get(room, [])):
            try:
                await ws.send_json(payload)
            except Exception:
                self.disconnect(room, ws)


manager = ConnectionManager()
