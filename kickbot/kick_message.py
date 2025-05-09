import json


class KickMessage:
    def __init__(self, raw_data: str) -> None:
        try:
            data = json.loads(raw_data)
        except Exception as e:
            raise ValueError(f"Failed to parse KickMessage JSON: {e} | Raw: {raw_data}")
        self.data = data
        self.id: str | None = data.get('id')
        self.chatroom_id: int | None = data.get('chatroom_id')
        self.content: str | None = data.get('content')
        self.args: list[str] | None = self.content.split() if self.content else []
        self.type: str | None = data.get('type')
        self.created_at: str | None = data.get('created_at')
        sender_data = data.get('sender')
        self.sender: _Sender | None = _Sender(sender_data) if isinstance(sender_data, dict) else None

    def __repr__(self) -> str:
        return f"KickMessage({self.data})"


class _Sender:
    def __init__(self, raw_sender: dict) -> None:
        if not isinstance(raw_sender, dict):
            raise ValueError(f"Invalid sender data: {raw_sender}")
        self.raw_sender = raw_sender
        self.user_id: int | None = raw_sender.get('id')
        self.username: str | None = raw_sender.get('username')
        self.slug: str | None = raw_sender.get('slug')
        self.identity: dict = raw_sender.get('identity', {})
        self.badges: list = self.identity.get('badges', [])

    def __repr__(self) -> str:
        return f"KickMessage.sender({self.raw_sender})"
