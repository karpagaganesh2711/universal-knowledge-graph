from pathlib import Path
from tempfile import NamedTemporaryFile

from fastapi import FastAPI, File, HTTPException, UploadFile

from services.document_processor import extract_text


app = FastAPI(
    title="Universal Knowledge Graph Generator",
    description=(
        "An AI-powered system that converts documents "
        "into interactive knowledge graphs."
    ),
    version="0.2.0",
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


@app.post("/documents/extract")
async def extract_document(file: UploadFile = File(...)):
    """
    Upload a PDF, DOCX, or TXT document and extract its text.
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
        with NamedTemporaryFile(
            delete=False,
            suffix=extension
        ) as temporary_file:
            temporary_file.write(file_content)
            temporary_path = temporary_file.name

        text = extract_text(temporary_path)

        if not text:
            raise HTTPException(
                status_code=422,
                detail=(
                    "No readable text was found in the document."
                ),
            )

        return {
            "filename": file.filename,
            "file_type": extension.replace(".", "").upper(),
            "characters": len(text),
            "words": len(text.split()),
            "status": "text_extracted",
            "text_preview": text[:1000],
        }

    except HTTPException:
        raise

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=f"Document processing failed: {str(error)}",
        )

    finally:
        if temporary_path:
            Path(temporary_path).unlink(
                missing_ok=True
            )