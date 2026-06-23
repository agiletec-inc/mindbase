"""Backend-as-brain: chat settings SSoT, conversation store-of-record, chat models."""

import json


def _sse_deltas(body: str) -> list[str]:
    out = []
    for line in body.splitlines():
        if line.startswith("data: "):
            evt = json.loads(line[6:])
            if "delta" in evt:
                out.append(evt["delta"])
    return out


async def test_chat_streams_reply_and_persists_turn(async_client):
    # rag_limit=0 keeps it self-contained (no stored vectors needed).
    r = await async_client.post(
        "/api/chat", json={"message": "hi there", "rag_limit": 0}
    )
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/event-stream")

    # The streamed deltas reconstruct the (stubbed) reply, and the stream is `done`.
    assert "".join(_sse_deltas(r.text)) == "Hello, world!"
    assert any(
        json.loads(line[6:]).get("done")
        for line in r.text.splitlines()
        if line.startswith("data: ")
    )

    # The completed turn is persisted (store-of-record), source mindbase-chat.
    listed = await async_client.get(
        "/conversations", params={"source": "mindbase-chat"}
    )
    assert listed.status_code == 200
    assert any(row["source"] == "mindbase-chat" for row in listed.json())


async def test_chat_can_skip_persistence(async_client):
    r = await async_client.post(
        "/api/chat", json={"message": "no save", "rag_limit": 0, "store": False}
    )
    assert r.status_code == 200
    assert "".join(_sse_deltas(r.text)) == "Hello, world!"
    listed = await async_client.get(
        "/conversations", params={"source": "mindbase-chat"}
    )
    assert listed.json() == []


async def test_chat_settings_are_single_source_of_truth(async_client):
    # Default seed comes through GET /settings.
    r = await async_client.get("/settings")
    assert r.status_code == 200
    assert r.json()["chatModel"]  # seeded from env default

    # Switching via PUT /settings persists to the store...
    r = await async_client.put("/settings", json={"chatModel": "llama3.1:8b"})
    assert r.status_code == 200
    assert r.json()["chatModel"] == "llama3.1:8b"

    # ...and every reader reflects it (GET /settings and GET /api/chat/models).
    assert (await async_client.get("/settings")).json()["chatModel"] == "llama3.1:8b"
    assert (await async_client.get("/api/chat/models")).json()["current"] == "llama3.1:8b"


async def test_chat_models_lists_installed(async_client):
    r = await async_client.get("/api/chat/models")
    assert r.status_code == 200
    body = r.json()
    assert body["available"] == ["bge-m3", "qwen2.5:3b"]  # from the stub
    assert "current" in body


async def test_conversations_list_and_get(async_client):
    payload = {
        "source": "claude-code",
        "source_conversation_id": "thread-list-1",
        "title": "store-of-record demo",
        "content": {
            "messages": [
                {"role": "user", "content": "how do I rebalance a uniswap v3 position"}
            ]
        },
    }
    stored = await async_client.post("/conversations/store", json=payload)
    assert stored.status_code == 200
    conv_id = stored.json()["id"]

    # Backend is the store-of-record: the conversation appears in the list.
    listed = await async_client.get("/conversations")
    assert listed.status_code == 200
    rows = listed.json()
    assert any(row["id"] == conv_id for row in rows)
    assert any(row["title"] == "store-of-record demo" for row in rows)

    # And can be fetched in full by id.
    got = await async_client.get(f"/conversations/{conv_id}")
    assert got.status_code == 200
    assert got.json()["id"] == conv_id
    assert "messages" in got.json()["content"]


async def test_get_unknown_conversation_404(async_client):
    r = await async_client.get("/conversations/00000000-0000-0000-0000-000000000000")
    assert r.status_code == 404
