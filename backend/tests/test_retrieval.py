from app.knowledge import KnowledgeChunk, KnowledgeDocument, build_chunks
from app.retrieval import retrieve_chunks


def test_build_chunks_preserves_heading_source_and_stable_ids():
    documents = (
        KnowledgeDocument(source="个人资料", content="# 技术栈\n\nReact、FastAPI"),
    )

    chunks = build_chunks(documents)

    assert chunks == (
        KnowledgeChunk(
            chunk_id="个人资料:0",
            source="个人资料",
            heading="技术栈",
            content="React、FastAPI",
        ),
    )


def test_retrieve_chunks_prefers_matching_project_content():
    chunks = build_chunks(
        (
            KnowledgeDocument(source="个人资料", content="# 技术\n\nReact、FastAPI"),
            KnowledgeDocument(
                source="SPMTrack 项目资料",
                content="# 流程\n\nROI、任务队列和跟踪引擎",
            ),
        )
    )

    result = retrieve_chunks("SPMTrack 的 ROI 和任务队列", chunks)

    assert result[0].source == "SPMTrack 项目资料"


def test_retrieve_chunks_returns_empty_for_unknown_question():
    chunks = build_chunks(
        (KnowledgeDocument(source="个人资料", content="# 技术\n\nReact、FastAPI"),)
    )

    assert retrieve_chunks("喜欢什么颜色", chunks) == ()


def test_retrieve_chunks_is_bounded_and_deterministic():
    chunks = tuple(
        KnowledgeChunk(str(index), "资料", "标题", "FastAPI")
        for index in range(6)
    )

    result = retrieve_chunks("FastAPI", chunks)

    assert len(result) == 4
    assert [chunk.chunk_id for chunk in result] == ["0", "1", "2", "3"]
