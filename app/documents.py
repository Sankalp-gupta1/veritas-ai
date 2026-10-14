"""PDF extraction with reproducible, normalized character offsets."""

import hashlib
import io
import re
import unicodedata
from uuid import uuid4

from pypdf import PdfReader

from . import config


def normalize(text: str) -> str:
    return re.sub(r"\s+", " ", unicodedata.normalize("NFKC", text).replace("\x00", " ")).strip()


def extract_pdf(data: bytes):
    if len(data) > config.MAX_FILE_BYTES:
        raise ValueError("This PDF is larger than 4 MB. Please upload a smaller file.")
    if not data.startswith(b"%PDF-"):
        raise ValueError("Please choose a valid PDF file.")
    try:
        reader = PdfReader(io.BytesIO(data), strict=False)
        if reader.is_encrypted:
            raise ValueError("Password-protected PDFs are not supported. Upload an unlocked copy.")
        if not 1 <= len(reader.pages) <= config.MAX_PAGES:
            raise ValueError("Please upload a PDF with 1 to 80 pages.")
        labels = reader.page_labels
        pages = []
        for number, page in enumerate(reader.pages, 1):
            stream = page.get_contents()
            if stream and len(stream.get_data()) > 5_000_000:
                raise ValueError("One page is too complex to process safely. Export a simpler PDF.")
            raw_text = page.extract_text() or ""
            text = normalize(raw_text)
            if len(text) > config.MAX_PAGE_CHARS:
                raise ValueError("One page contains too much text. Split this document first.")
            # Keep short headings apart from prose; join likely wrapped lines.
            # Every resulting block is still located in the canonical page text.
            blocks, previous = [], ""
            for line in raw_text.splitlines():
                line = normalize(line)
                if not line:
                    previous = ""
                    continue
                if blocks and len(previous) >= 65 and not previous.endswith((".", "!", "?", ":")):
                    blocks[-1] += " " + line
                else:
                    blocks.append(line)
                previous = line
            pages.append(
                {
                    "page_number": number,
                    "printed_label": labels[number - 1],
                    "text": text,
                    "blocks": blocks,
                }
            )
        if sum(len(p["text"]) for p in pages) < 40:
            raise ValueError("No readable text was found. Scanned PDFs need OCR before upload.")
        return pages
    except ValueError:
        raise
    except Exception as error:
        raise ValueError("This PDF could not be read. Try exporting it again.") from error


def chunk_pages(pages, size=950, overlap=130):
    chunks = []
    for page in pages:
        text, cursor = page["text"], 0
        blocks = page.get("blocks") or [text]
        for block in blocks:
            start = text.find(block, cursor)
            if start < 0:
                continue
            stop = start + len(block)
            cursor = stop
            while start < stop:
                end = min(start + size, stop)
                if end < stop:
                    boundary = text.rfind(". ", start + size // 2, end)
                    if boundary > start:
                        end = boundary + 1
                    else:
                        boundary = text.rfind(" ", start + size // 2, end)
                        if boundary > start:
                            end = boundary
                if len(text[start:end].strip()) >= 20:
                    chunks.append(
                        {
                            "id": str(uuid4()),
                            "page_number": page["page_number"],
                            "start_offset": start,
                            "end_offset": end,
                            "text": text[start:end],
                        }
                    )
                if end == stop:
                    break
                next_start = max(start + 1, end - overlap)
                boundary = text.find(" ", next_start, end)
                start = boundary + 1 if boundary >= 0 else next_start
    return chunks


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()
