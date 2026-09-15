import asyncio
from datetime import datetime, timezone
from uuid import uuid4

from httpx import ASGITransport, AsyncClient

from agent_service.app.config import get_agent_settings
from agent_service.app.knowledge.schemas import KnowledgeDocumentSummary, KnowledgeIngestResult
from agent_service.app.main import create_app


def test_knowledge_management_uses_trusted_tenant_identity(monkeypatch) -> None:
    monkeypatch.setenv("AGENT_SERVICE_TOKEN", "service-secret")
    get_agent_settings.cache_clear()
    document_id = uuid4()

    class FakeKnowledgeService:
        def __init__(self) -> None:
            self.ingested_tenant_id = None
            self.deleted = None

        def list_tenant_documents(self, tenant_id):
            assert tenant_id == 7
            return [KnowledgeDocumentSummary(
                document_id=document_id, title="Pressing", source_uri="upload://pressing.md",
                chunk_count=2, metadata={}, created_at=datetime.now(timezone.utc),
            )]

        async def ingest(self, request):
            self.ingested_tenant_id = request.tenant_id
            return KnowledgeIngestResult(document_id=document_id, chunk_count=2, created=True)

        def delete_tenant_document(self, tenant_id, target_id):
            self.deleted = (tenant_id, target_id)
            return True

    service = FakeKnowledgeService()
    monkeypatch.setattr(
        "agent_service.app.knowledge.api.build_knowledge_service_from_settings", lambda: service
    )
    app = create_app()
    headers = {
        "X-Agent-Service-Token": "service-secret",
        "X-Tenant-ID": "7",
        "X-User-ID": "12",
    }

    async def scenario() -> None:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://agent") as client:
            listed = await client.get("/knowledge/documents", headers=headers)
            assert listed.status_code == 200
            assert listed.json()["items"][0]["document_id"] == str(document_id)

            created = await client.post("/knowledge/documents", headers=headers, json={
                "title": "Pressing", "source_uri": "upload://pressing.md",
                "content": "Press together as a compact unit.", "tenant_id": 999,
            })
            assert created.status_code == 201
            assert service.ingested_tenant_id == 7

            deleted = await client.delete(f"/knowledge/documents/{document_id}", headers=headers)
            assert deleted.status_code == 200
            assert service.deleted == (7, document_id)

    try:
        asyncio.run(scenario())
    finally:
        get_agent_settings.cache_clear()
