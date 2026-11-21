import asyncio
import json
from collections.abc import Sequence
from uuid import uuid4

import httpx
from langchain_core.messages import AIMessage, BaseMessage, ToolMessage
from pydantic import ValidationError
import pytest

from agent_service.app.knowledge.embeddings import (
    LocalSentenceTransformerEmbeddingAdapter,
    OllamaEmbeddingAdapter,
    OpenAICompatibleEmbeddingAdapter,
)
from agent_service.app.knowledge.schemas import KnowledgeSearchHit, KnowledgeSearchResult
from agent_service.app.knowledge.service import split_text
from agent_service.app.recruitment.prompt import RECRUITMENT_SYSTEM_PROMPT
from agent_service.app.recruitment.schemas import RecruitmentReport, recruitment_fallback
from agent_service.app.recruitment.tool_schemas import (
    PlayerSearchToolResult,
    SquadToolResult,
    ToolPlayer,
)
from agent_service.app.recruitment.tools import RECRUITMENT_TOOL_NAMES, build_recruitment_tool_registry
from agent_service.app.runtime.model_adapter import ToolSchema
from agent_service.app.runtime.runner import AgentRunner
from agent_service.app.runtime.schemas import AgentLimits, AgentRunContext


def test_text_splitter_prefers_paragraphs_and_overlaps_long_text() -> None:
    chunks = split_text("First paragraph.\n\nSecond paragraph.", chunk_size=200, overlap=20)
    assert chunks == ["First paragraph.\n\nSecond paragraph."]
    long_chunks = split_text("x" * 350, chunk_size=200, overlap=50)
    assert len(long_chunks) == 3
    assert long_chunks[0][-50:] == long_chunks[1][:50]


def test_openai_compatible_embedding_adapter_orders_and_validates_vectors() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["Authorization"] == "Bearer secret"
        return httpx.Response(200, json={
            "data": [
                {"index": 1, "embedding": [0.0, 1.0, 0.0]},
                {"index": 0, "embedding": [1.0, 0.0, 0.0]},
            ]
        })

    async def scenario() -> None:
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            adapter = OpenAICompatibleEmbeddingAdapter(
                api_url="http://embedding.test/v1/embeddings",
                api_key="secret",
                model="test-model",
                dimensions=3,
                http_client=client,
            )
            vectors = await adapter.embed_documents(["one", "two"])
            assert vectors == [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0]]

    asyncio.run(scenario())


def test_ollama_embedding_adapter_uses_embed_api_and_validates_vectors() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url == "http://ollama.test/api/embed"
        assert json.loads(request.content) == {
            "model": "bge-m3",
            "input": ["squad depth", "pressing structure"],
        }
        return httpx.Response(200, json={
            "model": "bge-m3",
            "embeddings": [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0]],
        })

    async def scenario() -> None:
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            adapter = OllamaEmbeddingAdapter(
                base_url="http://ollama.test/",
                model="bge-m3",
                dimensions=3,
                http_client=client,
            )
            vectors = await adapter.embed_documents(["squad depth", "pressing structure"])
            assert vectors == [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0]]

    asyncio.run(scenario())


def test_local_embedding_adapter_adds_e5_prefixes_and_normalizes(monkeypatch) -> None:
    async def run_inline(function):
        # 测试环境不需要创建工作线程；生产环境仍由 asyncio.to_thread
        # 将耗时的本地推理移出事件循环。
        return function()

    monkeypatch.setattr(asyncio, "to_thread", run_inline)

    class FakeSentenceTransformer:
        def __init__(self) -> None:
            self.calls = []

        def get_sentence_embedding_dimension(self):
            return 3

        def encode(self, texts, **kwargs):
            self.calls.append((texts, kwargs))
            return [[1.0, 0.0, 0.0] for _ in texts]

    async def scenario() -> None:
        model = FakeSentenceTransformer()
        adapter = LocalSentenceTransformerEmbeddingAdapter(
            model_name="unused-in-test",
            dimensions=3,
            model_instance=model,
        )
        await adapter.embed_documents(["football pressing"])
        await adapter.embed_query("striker role")
        assert model.calls[0][0] == ["passage: football pressing"]
        assert model.calls[1][0] == ["query: striker role"]
        assert model.calls[0][1]["normalize_embeddings"] is True

    asyncio.run(scenario())


class FakeBackendClient:
    async def get_squad(self, _context):
        return SquadToolResult(
            club_name="Arsenal",
            players=[ToolPlayer(
                player_id=1, name="Current winger", positions="RW", overall="B",
                potential="B", age=28, value_eur=20_000_000, wage_eur=100_000,
                preferred_foot="Right", club_name="Arsenal", nationality_name="England",
            )],
            total=1,
        )

    async def get_tactic(self, _context):
        raise AssertionError("Unexpected tactic call")

    async def get_injuries(self, _arguments, _context):
        raise AssertionError("Unexpected injury call")

    async def search_players(self, _arguments, _context):
        return PlayerSearchToolResult(
            items=[ToolPlayer(
                player_id=7, name="Young Winger", positions="RW, LW", overall="A",
                potential="A+", age=21, value_eur=25_000_000, wage_eur=50_000,
                preferred_foot="Left", club_name="Candidate FC", nationality_name="France",
            )],
            total_matched=1,
            returned=1,
        )


class FakeKnowledgeService:
    async def search(self, *, query, tenant_id, limit, min_similarity):
        assert tenant_id == 15
        return KnowledgeSearchResult(
            query=query,
            hits=[KnowledgeSearchHit(
                chunk_id=uuid4(),
                document_id=uuid4(),
                title="Inverted Winger Principles",
                source_uri="https://example.test/inverted-winger",
                content="A left-footed right winger can attack inside channels.",
                similarity=0.91,
                chunk_index=0,
                metadata={"author": "Analyst"},
            )],
        )


class SequenceModel:
    def __init__(self, responses: list[AIMessage]) -> None:
        self.responses = responses
        self.calls: list[tuple[list[BaseMessage], list[ToolSchema]]] = []

    async def invoke(self, messages: Sequence[BaseMessage], tools: Sequence[ToolSchema]):
        self.calls.append((list(messages), list(tools)))
        return self.responses.pop(0)


def test_runner_combines_squad_candidates_knowledge_and_structured_evidence() -> None:
    knowledge_id = uuid4()
    knowledge = FakeKnowledgeService()

    async def fixed_search(**kwargs):
        result = await FakeKnowledgeService().search(**kwargs)
        result.hits[0].chunk_id = knowledge_id
        return result

    knowledge.search = fixed_search
    registry = build_recruitment_tool_registry(FakeBackendClient(), knowledge_service=knowledge)
    report_json = json.dumps({
        "status": "completed",
        "summary": "The squad lacks a high-level inverted right winger.",
        "needs": [{
            "position": "RW",
            "priority": "high",
            "reason": "Current depth and tactical knowledge support an inverted winger profile.",
            "evidence": [
                {"source_type": "squad", "source_id": "squad:current", "description": "Current RW depth"},
                {"source_type": "knowledge", "source_id": f"knowledge:{knowledge_id}", "description": "Inverted winger principle"},
            ],
        }],
        "candidates": [{
            "player_id": 7,
            "player_name": "Young Winger",
            "fit_grade": "A",
            "reasons": ["Left-footed and within the deterministic age and budget filters."],
            "risks": ["Requires further scouting."],
            "evidence": [
                {"source_type": "player", "source_id": "player:7", "description": "Candidate search result"},
                {"source_type": "knowledge", "source_id": f"knowledge:{knowledge_id}", "description": "Role fit rationale"},
            ],
        }],
        "assumptions": ["Public grade bands are used instead of exact attributes."],
        "uncertainty": "medium",
    })
    model = SequenceModel([
        AIMessage(content="", tool_calls=[{
            "name": "get_squad", "args": {}, "id": "squad-call", "type": "tool_call",
        }]),
        AIMessage(content="", tool_calls=[{
            "name": "search_players",
            "args": {"positions": ["RW"], "max_age": 23, "max_value_eur": 30_000_000},
            "id": "player-call", "type": "tool_call",
        }]),
        AIMessage(content="", tool_calls=[{
            "name": "search_football_knowledge",
            "args": {"query": "left footed inverted right winger tactical fit", "limit": 3},
            "id": "knowledge-call", "type": "tool_call",
        }]),
        AIMessage(content=report_json),
    ])
    runner = AgentRunner(
        model=model,
        tools=registry,
        output_model=RecruitmentReport,
        fallback_factory=recruitment_fallback,
        limits=AgentLimits(max_steps=5, max_tool_calls=5),
        allowed_tools=RECRUITMENT_TOOL_NAMES,
    )
    result = asyncio.run(runner.run(
        question="Diagnose the squad and recommend a right winger.",
        system_prompt=RECRUITMENT_SYSTEM_PROMPT,
        context=AgentRunContext(tenant_id=15, user_id=29, role="manager"),
    ))
    assert result.degraded is False
    assert result.tool_call_count == 3
    assert result.output.candidates[0].player_id == 7
    tool_payloads = [
        json.loads(call[0][-1].content)
        for call in model.calls[1:]
        if isinstance(call[0][-1], ToolMessage)
    ]
    assert tool_payloads[0]["value"]["evidence_source_id"] == "squad:current"
    assert tool_payloads[1]["value"]["items"][0]["evidence_source_id"] == "player:7"
    assert tool_payloads[2]["value"]["hits"][0]["evidence_source_id"] == f"knowledge:{knowledge_id}"


def test_candidate_without_matching_player_evidence_is_rejected() -> None:
    with pytest.raises(ValidationError):
        RecruitmentReport.model_validate({
            "summary": "Recommendation",
            "needs": [],
            "candidates": [{
                "player_id": 7,
                "player_name": "Invented candidate",
                "fit_grade": "A",
                "reasons": [],
                "risks": [],
                "evidence": [],
            }],
            "assumptions": [],
            "uncertainty": "high",
        })
