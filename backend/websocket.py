from fastapi import WebSocket


class ConnectionManager:
    def __init__(self):
        self.clients = set()

    async def broadcast(self,kind,payload):
        for client in list(self.clients):
            try:
                await client.send_json(dict(type=kind,payload=payload))
            except Exception:
                self.clients.discard(client)
