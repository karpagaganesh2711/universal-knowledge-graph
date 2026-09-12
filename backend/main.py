from pathlib import Path
from tempfile import NamedTemporaryFile

from fastapi import FastAPI, File, HTTPException, UploadFile

from services.document_processor import extract_text
from services.graph_processor import build_knowledge_graph
from services.nlp_processor import analyze_text


app = FastAPI(
    title="Universal Knowledge Graph Generator",
    description=(
        "An AI-powered system that converts documents "
        "into interactive knowledge graphs."
    ),
    version="0.4.0",
)


@app.get("/")
def root():
    return {
        "message": "Universal Knowledge Graph Generator API is running!"
    }


@app.get("/health")
def health():
    return {
        "status": "healthy"
    }


@app.post("/documents/analyze")
async def analyze_document(file: UploadFile = File(...)):
    """
    Upload a PDF, DOCX, or TXT document,
    extract its text, analyze it using NLP,
    and generate a knowledge graph.
    """

    if not file.filename:
        raise HTTPException(
            status_code=400,
            detail="No filename was provided."
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
            detail="Only PDF, DOCX, and TXT files are supported."
        )

    file_content = await file.read()

    temporary_path = None

    try:
        # -----------------------------------------------------
        # STEP 1: Save uploaded file temporarily
        # -----------------------------------------------------

        with NamedTemporaryFile(
            delete=False,
            suffix=extension
        ) as temporary_file:
            temporary_file.write(file_content)
            temporary_path = temporary_file.name

        # -----------------------------------------------------
        # STEP 2: Extract document text
        # -----------------------------------------------------

        text = extract_text(temporary_path)

        if not text:
            raise HTTPException(
                status_code=422,
                detail="No readable text was found in the document."
            )

        # -----------------------------------------------------
        # STEP 3: Analyze text using spaCy
        # -----------------------------------------------------

        analysis = analyze_text(text)

        # -----------------------------------------------------
        # STEP 4: Build knowledge graph
        # -----------------------------------------------------

        graph = build_knowledge_graph(analysis)

        # -----------------------------------------------------
        # STEP 5: Return complete analysis
        # -----------------------------------------------------

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