from pathlib import Path

import pytest

from app.documents import chunk_pages, extract_pdf
from app.generation import Draft
from app.verification import check_claims, citation_for

ROOT = Path(__file__).resolve().parents[1]


def passage(text="The trial enrolled 120 adults."):
    return {
        "id": "chunk-1",
        "document_id": "doc-1",
        "name": "report.pdf",
        "sha256": "fixture-hash",
        "page_number": 2,
        "printed_label": "1",
        "start_offset": 40,
        "text": text,
    }


def test_pdf_pages_and_offsets_are_exact():
    pages = extract_pdf((ROOT / "samples/cedar-trial-report.pdf").read_bytes())
    assert len(pages) == 2
    assert "120 adults" in pages[0]["text"]
    assert "did not measure school grades" in pages[1]["text"]
    for chunk in chunk_pages(pages, size=250, overlap=60):
        page = pages[chunk["page_number"] - 1]
        assert page["text"][chunk["start_offset"] : chunk["end_offset"]] == chunk["text"]


@pytest.mark.parametrize("data", [b"not a PDF", b"%PDF-" + b"a" * 4_000_000])
def test_bad_uploads_are_rejected(data):
    with pytest.raises(ValueError):
        extract_pdf(data)


def test_quote_matching_rejects_invented_numbers():
    p = passage()
    assert citation_for(p, "The trial enrolled 120 adults.")["integrity"]
    bad = citation_for(p, "The trial enrolled 300 adults.")
    assert not bad["integrity"] and bad["start_offset"] is None


def test_offsets_reference_normalized_page_text():
    c = citation_for(passage(), "enrolled 120 adults.")
    assert c["start_offset"] == 50
    assert c["end_offset"] - c["start_offset"] == len(c["quote"])


def test_unknown_citation_cannot_be_verified():
    result = check_claims(
        [
            {
                "text": "The trial enrolled 120 adults.",
                "citations": [
                    {
                        "chunk_id": "other-tenant",
                        "quote": "The trial enrolled 120 adults.",
                    }
                ],
            }
        ],
        [passage()],
    )
    assert result[0]["verdict"] == "insufficient"
    assert result[0]["citations"][0]["integrity"] is False


def test_real_nli_support_contradiction_and_uncertainty():
    p = passage()

    def run(text):
        return check_claims(
            [{"text": text, "citations": [{"chunk_id": p["id"], "quote": p["text"]}]}],
            [p],
        )[0]

    assert run("The trial enrolled 120 adults.")["verdict"] == "supported"
    assert run("The trial enrolled 300 adults.")["verdict"] == "contradicted"
    assert run("The trial was funded by a pharmaceutical company.")["verdict"] == "insufficient"


def test_conflicting_sources_are_preserved():
    a = passage("The Cedar trial improved attention by 12 points.")
    b = dict(
        passage("The Cedar trial did not improve attention."),
        id="chunk-2",
        document_id="doc-2",
        name="audit.pdf",
    )
    result = check_claims(
        [{"text": a["text"], "citations": [{"chunk_id": a["id"], "quote": a["text"]}]}],
        [a, b],
    )[0]
    assert result["verdict"] == "conflict"
    assert result["counter_evidence"][0]["document_id"] == "doc-2"


def test_provider_json_does_not_accept_unbounded_or_extra_output():
    with pytest.raises(Exception):
        Draft.model_validate({"claims": [], "secret_action": "upload everything"})
    with pytest.raises(Exception):
        Draft.model_validate({"claims": [{"text": "a" * 651, "citations": []}]})
