from collections.abc import Callable

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph

from app.agent.state import AgentState
from app.checkpointing import create_checkpoint_serializer
from app.domain.models import (
    AgentAction,
    MemoryCandidate,
    MemoryCategory,
    RiskLevel,
    ToolTraceItem,
    TurnResponse,
)
from app.providers.base import ModelProvider
from app.services.safety import screen_safety


def _trace(state: AgentState, node: str, summary: str) -> list[ToolTraceItem]:
    current = state.get("trace", [])
    return current + [ToolTraceItem(step=len(current) + 1, node=node, summary=summary)]


def build_agent_graph(provider: ModelProvider, checkpointer=None):
    async def safety_screen(state: AgentState) -> dict:
        result = screen_safety(state["latest_message"])
        return {
            "safety": result,
            "trace": _trace(state, "safety_screen", f"安全等级：{result.risk_level}"),
        }

    def route_after_safety(state: AgentState) -> str:
        return "guardian" if state["safety"].risk_level == RiskLevel.URGENT else "understand"

    async def understand_context(state: AgentState) -> dict:
        analysis = await provider.analyze(
            state["latest_message"],
            state.get("messages", [])[:-1],
            state.get("confirmed_memories", []),
            state["child"],
        )
        return {
            "analysis": analysis,
            "trace": _trace(
                state,
                "understand_context",
                (
                    f"识别主要情绪：{analysis.primary_emotion}，置信度：{analysis.confidence:.2f}；"
                    f"读取 {len(state.get('confirmed_memories', []))} 条家长确认记忆"
                ),
            ),
        }

    async def decide(state: AgentState) -> dict:
        analysis = state["analysis"]
        needs_question = bool(analysis.missing_information) or analysis.confidence < 0.6
        action = AgentAction.ASK_CHILD if needs_question else AgentAction.CREATE_STORY
        return {
            "action": action,
            "trace": _trace(state, "decide", f"选择下一步：{action}"),
        }

    def route_after_decision(state: AgentState) -> str:
        return "ask" if state["action"] == AgentAction.ASK_CHILD else "story"

    async def ask_child(state: AgentState) -> dict:
        missing = state["analysis"].missing_information
        focus = missing[0] if missing else "刚才发生的事情"
        message = f"我在听。你愿意告诉我，{focus}吗？"
        return {
            "child_message": message,
            "trace": _trace(state, "ask_child", "生成一个低压力澄清问题"),
        }

    async def guardian_response(state: AgentState) -> dict:
        return {
            "action": AgentAction.ESCALATE_GUARDIAN,
            "child_message": (
                "谢谢你告诉我。现在请马上去找身边信任的大人，让他陪着你；我也会提醒家长来帮助你。"
            ),
            "trace": _trace(state, "guardian_escalation", "停止故事生成并请求监护人立即介入"),
        }

    async def create_story(state: AgentState) -> dict:
        story = await provider.create_story(
            state["latest_message"],
            state["analysis"],
            state["child"],
        )
        return {
            "story": story,
            "child_message": "我把你的心情画进了一个小故事，我们一起看看吧。",
            "trace": _trace(state, "create_story", f"调用绘本工具生成《{story.title}》"),
        }

    async def create_parent_guidance(state: AgentState) -> dict:
        guidance = await provider.create_parent_guidance(
            state["latest_message"],
            state["analysis"],
            state["story"],
            state["child"],
        )
        return {
            "parent_guidance": guidance,
            "trace": _trace(state, "parent_guidance", "调用家长建议工具"),
        }

    async def propose_memory(state: AgentState) -> dict:
        analysis = state["analysis"]
        if analysis is None or state["safety"].risk_level != RiskLevel.NONE:
            return {
                "memory_candidate": None,
                "trace": _trace(state, "propose_memory", "当前内容不生成长期记忆候选"),
            }
        candidate = MemoryCandidate(
            summary=analysis.event_summary,
            category=MemoryCategory.SOCIAL_EVENT,
            reason="后续陪伴时可避免重复询问事件背景",
        )
        return {
            "memory_candidate": candidate,
            "trace": _trace(state, "propose_memory", "提出候选记忆，等待家长确认后保存"),
        }

    async def finalize(state: AgentState) -> dict:
        final_trace = _trace(state, "finalize", "组装本轮结构化响应")
        response = TurnResponse(
            conversation_id=state["conversation_id"],
            action=state["action"],
            child_message=state["child_message"],
            safety=state["safety"],
            analysis=state.get("analysis"),
            story=state.get("story"),
            parent_guidance=state.get("parent_guidance"),
            memory_candidate=state.get("memory_candidate"),
            tool_trace=final_trace,
            model_provider=provider.name,
        )
        return {
            "response": response,
            "messages": [{"role": "assistant", "content": state["child_message"]}],
        }

    builder = StateGraph(AgentState)
    nodes: dict[str, Callable] = {
        "safety_screen": safety_screen,
        "understand_context": understand_context,
        "decide": decide,
        "ask_child": ask_child,
        "guardian_response": guardian_response,
        "create_story": create_story,
        "parent_guidance": create_parent_guidance,
        "propose_memory": propose_memory,
        "finalize": finalize,
    }
    for name, node in nodes.items():
        builder.add_node(name, node)

    builder.add_edge(START, "safety_screen")
    builder.add_conditional_edges(
        "safety_screen",
        route_after_safety,
        {"guardian": "guardian_response", "understand": "understand_context"},
    )
    builder.add_edge("guardian_response", "finalize")
    builder.add_edge("understand_context", "decide")
    builder.add_conditional_edges(
        "decide",
        route_after_decision,
        {"ask": "ask_child", "story": "create_story"},
    )
    builder.add_edge("ask_child", "finalize")
    builder.add_edge("create_story", "parent_guidance")
    builder.add_edge("parent_guidance", "propose_memory")
    builder.add_edge("propose_memory", "finalize")
    builder.add_edge("finalize", END)
    return builder.compile(
        checkpointer=checkpointer or InMemorySaver(serde=create_checkpoint_serializer())
    )
