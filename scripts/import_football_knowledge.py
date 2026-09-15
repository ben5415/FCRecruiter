"""把 UTF-8 Markdown/Text 文件切片、向量化并导入 Agent 数据库。"""

import argparse
import asyncio
from pathlib import Path

from agent_service.app.knowledge import build_knowledge_service_from_settings
from agent_service.app.knowledge.schemas import KnowledgeIngestRequest


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("file", type=Path)
    parser.add_argument("--title")
    parser.add_argument("--source-uri")
    parser.add_argument("--tenant-id", type=int, help="Omit for knowledge shared by all tenants")
    return parser.parse_args()


async def run() -> None:
    args = parse_args()
    path = args.file.resolve()
    content = path.read_text(encoding="utf-8")
    result = await build_knowledge_service_from_settings().ingest(KnowledgeIngestRequest(
        title=args.title or path.stem.replace("_", " ").title(),
        source_uri=args.source_uri or path.as_uri(),
        content=content,
        tenant_id=args.tenant_id,
        metadata={"filename": path.name},
    ))
    action = "created" if result.created else "already exists"
    print(f"Knowledge document {action}: {result.document_id} ({result.chunk_count} chunks)")


if __name__ == "__main__":
    asyncio.run(run())
