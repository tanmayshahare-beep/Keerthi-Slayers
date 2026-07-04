"""In-memory conversation store, one conversation per report.

Same tradeoff as auth.py's in-memory session store: acceptable for a local,
single-user desktop app whose backend restarts along with the app. Losing
chat history on restart is fine for what's explicitly a demo feature.
"""

_conversations: dict[str, list[dict]] = {}


def start_conversation(report_id: str, messages: list[dict]) -> None:
    _conversations[report_id] = list(messages)


def get_conversation(report_id: str) -> list[dict] | None:
    return _conversations.get(report_id)


def append_message(report_id: str, role: str, content: str) -> None:
    _conversations.setdefault(report_id, []).append({"role": role, "content": content})
