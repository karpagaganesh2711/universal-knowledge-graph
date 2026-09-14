from pathlib import Path
from tempfile import NamedTemporaryFile

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from services.document_processor import extract_text
from services.nlp_processor import analyze_text
from services.graph_processor import build_knowledge_graph
from services.semantic_search import semantic_search


LATEST_GRAPH = None


app = FastAPI(
    title="Universal Knowledge Graph Generator",
    description="An AI-powered system that converts documents into interactive knowledge graphs.",
    version="0.6.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def root():
    return {
        "message": "Universal Knowledge Graph Generator API is running!"
    }


@app.get("/health")
def health():
    return {"status": "healthy"}


@app.get("/graph/stats")
def graph_stats():
    if not LATEST_GRAPH:
        raise HTTPException(
            status_code=404,
            detail="No graph has been generated yet.",
        )

    return {
        "node_count": LATEST_GRAPH["node_count"],
        "relationship_count": LATEST_GRAPH["relationship_count"],
        "semantic_relationship_count": LATEST_GRAPH[
            "semantic_relationship_count"
        ],
        "average_relationship_confidence": LATEST_GRAPH[
            "average_relationship_confidence"
        ],
        "average_relationship_score": LATEST_GRAPH[
            "average_relationship_score"
        ],
    }


@app.get("/graph/important-nodes")
def important_nodes(limit: int = 10):
    if not LATEST_GRAPH:
        raise HTTPException(
            status_code=404,
            detail="No graph has been generated yet.",
        )

    if limit < 1 or limit > 50:
        raise HTTPException(
            status_code=400,
            detail="Limit must be between 1 and 50.",
        )

    return {
        "nodes": LATEST_GRAPH[
            "most_important_nodes"
        ][:limit]
    }


@app.get("/graph/strongest-relationships")
def strongest_relationships(limit: int = 10):
    if not LATEST_GRAPH:
        raise HTTPException(
            status_code=404,
            detail="No graph has been generated yet.",
        )

    if limit < 1 or limit > 50:
        raise HTTPException(
            status_code=400,
            detail="Limit must be between 1 and 50.",
        )

    relationships = sorted(
        LATEST_GRAPH["relationships"],
        key=lambda item: item.get(
            "score",
            0,
        ),
        reverse=True,
    )

    return {
        "relationships": relationships[:limit]
    }

@app.post("/graph/semantic-search")
def graph_semantic_search(
    query: str,
    limit: int = 10,
):
    if not LATEST_GRAPH:
        raise HTTPException(
            status_code=404,
            detail="No graph has been generated yet.",
        )

    if not query.strip():
        raise HTTPException(
            status_code=400,
            detail="Search query cannot be empty.",
        )

    if limit < 1 or limit > 20:
        raise HTTPException(
            status_code=400,
            detail="Limit must be between 1 and 20.",
        )

    results = semantic_search(
        query=query,
        nodes=LATEST_GRAPH["nodes"],
        relationships=LATEST_GRAPH["relationships"],
        limit=limit,
    )

    return {
        "query": query,
        "results": results,
        "result_count": len(results),
    }




@app.post("/documents/analyze")
async def analyze_document(file: UploadFile = File(...)):
    if not file.filename:
        raise HTTPException(
            status_code=400,
            detail="No filename was provided.",
        )

    extension = Path(file.filename).suffix.lower()

    allowed_extensions = {
        ".pdf",
        ".docx",
        ".txt",
    }

    if extension not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail="Only PDF, DOCX, and TXT files are supported.",
        )

    file_content = await file.read()

    temporary_path = None

    try:
        with NamedTemporaryFile(
            delete=False,
            suffix=extension,
        ) as temporary_file:
            temporary_file.write(file_content)
            temporary_path = temporary_file.name

        text = extract_text(temporary_path)

        if not text:
            raise HTTPException(
                status_code=422,
                detail="No readable text was found in the document.",
            )

        analysis = analyze_text(text)
        graph = build_knowledge_graph(analysis)

        global LATEST_GRAPH
        LATEST_GRAPH = graph

        return {
            "filename": file.filename,
            "file_type": extension.replace(".", "").upper(),
            "characters": len(text),
            "words": len(text.split()),
            "status": "graph_generated",
            "sentences": analysis["sentences"],
            "sentence_count": analysis["sentence_count"],
            "entities": analysis["entities"],
            "entity_count": analysis["entity_count"],
            "concepts": analysis["concepts"],
            "concept_count": analysis["concept_count"],
            "graph": graph,
        }

    except HTTPException:
        raise

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=f"Document analysis failed: {str(error)}",
        )

    finally:
        if temporary_path:
            Path(temporary_path).unlink(
                missing_ok=True
            )
