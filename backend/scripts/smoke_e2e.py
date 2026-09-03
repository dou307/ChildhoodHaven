import argparse
from uuid import uuid4

import httpx


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the 童心驿站 HTTP smoke flow")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--token", default="")
    args = parser.parse_args()

    headers = {"Authorization": f"Bearer {args.token}"} if args.token else {}
    suffix = uuid4().hex[:10]
    child_id = f"smoke-child-{suffix}"
    conversation_id = f"smoke-conversation-{suffix}"
    turn_id = f"smoke-turn-{suffix}"
    payload = {
        "turn_id": turn_id,
        "message": "今天画画分组时，他们没有先选我，我有一点难过。",
        "child": {"child_id": child_id, "nickname": "小雨", "age": 6},
    }

    with httpx.Client(base_url=args.base_url, headers=headers, timeout=15) as client:
        health = client.get("/api/v1/health")
        health.raise_for_status()
        print("health", health.json())

        first = client.post(f"/api/v1/conversations/{conversation_id}/turns", json=payload)
        first.raise_for_status()
        first_body = first.json()
        assert first_body["action"] == "create_story"
        assert first_body["memory_candidate"] is not None
        print("turn", first_body["action"], first.headers.get("x-request-id"))

        repeated = client.post(f"/api/v1/conversations/{conversation_id}/turns", json=payload)
        repeated.raise_for_status()
        assert repeated.json() == first_body
        print("idempotency", "ok")

        confirmed = client.post(
            f"/api/v1/children/{child_id}/memories",
            json={"candidate": first_body["memory_candidate"], "guardian_confirmed": True},
        )
        confirmed.raise_for_status()
        memory_id = confirmed.json()["memory_id"]

        memories = client.get(f"/api/v1/children/{child_id}/memories")
        memories.raise_for_status()
        assert [item["memory_id"] for item in memories.json()] == [memory_id]
        print("memory", "confirmed")

        deleted = client.delete(f"/api/v1/children/{child_id}/memories/{memory_id}")
        deleted.raise_for_status()
        assert client.get(f"/api/v1/children/{child_id}/memories").json() == []
        print("memory", "deleted")

        conflict_payload = {
            **payload,
            "turn_id": f"conflict-{suffix}",
            "child": {"child_id": f"other-{suffix}", "nickname": "小云", "age": 7},
        }
        conflict = client.post(
            f"/api/v1/conversations/{conversation_id}/turns", json=conflict_payload
        )
        assert conflict.status_code == 409
        assert conflict.json()["code"] == "conflict"
        print("ownership", "protected")

    print("SMOKE E2E PASSED")


if __name__ == "__main__":
    main()
