"""src/ingestion/pdf_loader.py

Resume PDF loader.

Extracts plain text from a PDF file — either from a local path
or a remote URL. Cleans extracted text for consistent chunking.

Responsibility: extract text from PDF. Nothing else.
Does NOT: chunk, embed, or store the document.

Typical usage:
    from src.ingestion.pdf_loader import load_pdf

    text = await load_pdf("https://chitrankagnihotri.com/resume.pdf")
    text = await load_pdf("data/resume.pdf")
"""

import io
from pathlib import Path

import httpx
from pypdf import PdfReader

from src.core.logger import logger


async def load_pdf(source: str | Path) -> str:
    """Extract plain text from a PDF — local file or remote URL.

    Detects whether source is a URL or local path and loads
    accordingly. Strips excessive whitespace for cleaner chunking.

    Args:
        source: Local file path or HTTPS URL to the PDF.

    Returns:
        Extracted plain text from all pages.

    Raises:
        FileNotFoundError: If local path does not exist.
        httpx.HTTPError: If URL fetch fails.
        pypdf.errors.PdfReadError: If file is not a valid PDF.

    Example:
        >>> text = await load_pdf("https://chitrankagnihotri.com/resume.pdf")
        >>> len(text) > 0
        True
    """
    source_str = str(source)

    if source_str.startswith("http://") or source_str.startswith("https://"):
        pdf_bytes = await _fetch_url(source_str)
        reader = PdfReader(io.BytesIO(pdf_bytes))
        logger.info(f"Loaded PDF from URL: {source_str}")
    else:
        path = Path(source)
        if not path.exists():
            raise FileNotFoundError(f"PDF not found: {path}")
        reader = PdfReader(str(path))
        logger.info(f"Loaded PDF from path: {path}")

    return _extract_text(reader)


async def _fetch_url(url: str) -> bytes:
    """Fetch PDF bytes from a remote URL.

    Args:
        url: HTTPS URL to the PDF file.

    Returns:
        Raw PDF bytes.

    Raises:
        httpx.HTTPError: If the request fails or returns non-200.
    """
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.get(url)
        response.raise_for_status()
        return response.content


def _extract_text(reader: PdfReader) -> str:
    """Extract and clean text from a PdfReader instance.

    Args:
        reader: Initialised PdfReader object.

    Returns:
        Clean plain text from all pages joined with newlines.
    """
    pages = []

    for i, page in enumerate(reader.pages):
        text = page.extract_text()
        if text and text.strip():
            pages.append(text.strip())
            logger.debug(f"Extracted page {i + 1}/{len(reader.pages)}")

    full_text = "\n\n".join(pages)

    # Normalise whitespace — pypdf sometimes produces excessive spaces
    lines = [line.strip() for line in full_text.splitlines()]
    clean_text = "\n".join(line for line in lines if line)

    logger.info(f"Extracted {len(clean_text)} characters from PDF")
    return clean_text
