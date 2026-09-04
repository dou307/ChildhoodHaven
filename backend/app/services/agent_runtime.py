from app.domain.models import TurnRequest, TurnResponse


class ConversationOwnershipError(Exception):
    pass


async def run_agent_turn(
    graph,
    memory_repository,
    conversation_id: str,
    payload: TurnRequest,
) -> TurnResponse:
    graph_config = {"configurable": {"thread_id": conversation_id}}
    snapshot = await graph.aget_state(graph_config)
    previous_child = snapshot.values.get("child")
    if previous_child is not None and previous_child.child_id != payload.child.child_id:
        raise ConversationOwnershipError("该会话已属于另一个儿童档案")
    if (
        payload.turn_id is not None
        and snapshot.values.get("turn_id") == payload.turn_id
        and snapshot.values.get("response") is not None
    ):
        return snapshot.values["response"]

    confirmed_memories = await memory_repository.list_for_child(payload.child.child_id)
    result = await graph.ainvoke(
        {
            "conversation_id": conversation_id,
            "turn_id": payload.turn_id,
            "child": payload.child,
            "latest_message": payload.message,
            "messages": [{"role": "child", "content": payload.message}],
            "confirmed_memories": confirmed_memories,
            "analysis": None,
            "story": None,
            "parent_guidance": None,
            "memory_candidate": None,
            "response": None,
            "trace": [],
        },
        config=graph_config,
    )
    return result["response"]
