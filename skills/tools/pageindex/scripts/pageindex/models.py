"""PageIndex data models — vendored, self-contained.

Ported verbatim (behaviour-preserving) from Memex
``memex_core.memory.extraction.models`` and ``...pipeline.asset_parser``.
Only the page-index types are kept; the fact-extraction / SQLModel types and
their ``memex_core`` config/type imports are intentionally dropped so this
module depends on nothing but ``tiktoken``, ``pydantic`` and the stdlib.
"""

from __future__ import annotations

import hashlib
import json
import re
import uuid
from os.path import basename
from typing import Any

import tiktoken
from pydantic import BaseModel, Field, computed_field

_ENCODER = tiktoken.get_encoding("cl100k_base")


def estimate_token_count(text: str | None) -> int:
    """Estimate the token count of a text string using cl100k_base encoding."""
    if not text:
        return 0
    return len(_ENCODER.encode(text))


def content_hash_md5(text: str) -> str:
    """MD5 hash of text content, used for node-level identity."""
    return hashlib.md5(text.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# Image-reference parser (vendored from pipeline/asset_parser.py)
# Pure, deterministic, stdlib-only. Used by TOCNode.assets.
# ---------------------------------------------------------------------------

# A fence opener/closer must sit on its own line (optionally indented), so a
# stray ``` token inside prose is not mistaken for a code block.
_FENCED_CODE_RE = re.compile(
    r"^[ \t]*(```|~~~).*?(?:^[ \t]*\1[ \t]*$|\Z)",
    re.DOTALL | re.MULTILINE,
)
_INLINE_CODE_RE = re.compile(r"`[^`\n]*`")

_MARKDOWN_IMG_RE = re.compile(r'!\[([^\]]*)\]\(([^)\s]+)(?:\s+"[^"]*")?\)')
_WIKI_IMG_RE = re.compile(r"!\[\[([^\]]+)\]\]")
_HTML_IMG_RE = re.compile(r"<img\b[^>]*>", re.IGNORECASE)
_HTML_SRC_RE = re.compile(r'\bsrc\s*=\s*["\']([^"\']*)["\']', re.IGNORECASE)
_HTML_ALT_RE = re.compile(r'\balt\s*=\s*["\']([^"\']*)["\']', re.IGNORECASE)

# Not stored assets: remote references and inline data URIs.
_SKIP_PREFIXES = ("http://", "https://", "data:")


def _is_skippable(path: str) -> bool:
    return path.lower().startswith(_SKIP_PREFIXES)


def _strip_code(text: str) -> str:
    """Blank out code spans so image-like syntax inside them is not parsed."""
    without_fenced = _FENCED_CODE_RE.sub("", text)
    return _INLINE_CODE_RE.sub("", without_fenced)


def _norm_alt(alt: str | None) -> str | None:
    if alt is None:
        return None
    alt = alt.strip()
    return alt or None


def extract_image_refs(text: str) -> list[dict[str, Any]]:
    """Return structured metadata for every embedded image reference.

    Each entry is ``{path, alt_text, filename}``. Order follows first
    appearance; duplicate paths are collapsed (first alt-text wins). External
    (http/https) and data-URI references are skipped. Returns ``[]`` for empty
    input.
    """
    if not text:
        return []

    scanned = _strip_code(text)

    candidates: list[tuple[int, str, str | None]] = []
    for m in _MARKDOWN_IMG_RE.finditer(scanned):
        candidates.append((m.start(), m.group(2), m.group(1)))
    for m in _WIKI_IMG_RE.finditer(scanned):
        raw = m.group(1)
        if "|" in raw:
            path, _, alias = raw.partition("|")
            candidates.append((m.start(), path, alias))
        else:
            candidates.append((m.start(), raw, None))
    for m in _HTML_IMG_RE.finditer(scanned):
        tag = m.group(0)
        src_match = _HTML_SRC_RE.search(tag)
        if src_match is None:
            continue
        alt_match = _HTML_ALT_RE.search(tag)
        candidates.append(
            (m.start(), src_match.group(1), alt_match.group(1) if alt_match else None)
        )

    candidates.sort(key=lambda c: c[0])

    refs: list[dict[str, Any]] = []
    seen: set[str] = set()
    for _pos, raw_path, alt in candidates:
        path = raw_path.strip()
        if not path or _is_skippable(path) or path in seen:
            continue
        seen.add(path)
        refs.append(
            {
                "path": path,
                "alt_text": _norm_alt(alt),
                "filename": basename(path),
            }
        )

    return refs


# ---------------------------------------------------------------------------
# PageIndex models
# ---------------------------------------------------------------------------


class SectionSummary(BaseModel):
    """Structured 5W summary of a document section."""

    who: str | None = Field(
        default=None, description="Entities, people, or systems involved."
    )
    what: str | None = Field(
        None, description="Core events, topics, or actions discussed."
    )
    how: str | None = Field(
        None, description="Methods, processes, or mechanisms described."
    )
    when: str | None = Field(
        None, description="Timeframes, dates, or sequences mentioned."
    )
    where: str | None = Field(
        default=None, description="Locations, contexts, or environments."
    )

    @property
    def formatted(self) -> str:
        parts: list[str] = []
        if self.who:
            parts.append(self.who)
        if self.what:
            parts.append(self.what)
        if self.how:
            parts.append(self.how)
        if self.when:
            parts.append(self.when)
        if self.where:
            parts.append(self.where)
        return " | ".join(parts)


class BlockSummary(BaseModel):
    """Synthesized summary of a block composed of multiple sections."""

    topic: str = Field(..., description="The overarching topic or theme of this block.")
    key_points: list[str] = Field(
        default_factory=list,
        description="3-5 key points covered in this block. "
        "Each point should be a complete sentence WITHOUT trailing punctuation.",
    )
    tags: list[str] = Field(
        default_factory=list,
        description="3-7 short, lowercase tags that categorize this block. "
        "Use existing domain terminology. No hashtags.",
    )

    @property
    def formatted(self) -> str:
        if not self.key_points:
            return self.topic
        points = " | ".join(self.key_points)
        return f"{self.topic} — {points}"


class DetectedHeader(BaseModel):
    """A header detected in the document text (by regex or LLM scanning)."""

    reasoning: str = Field(
        ...,
        description="Explain WHY this line is a header.",
    )
    exact_text: str = Field(
        ..., description="The EXACT string sequence found in the source text."
    )
    clean_title: str = Field(..., description="The cleaned, human-readable title.")
    level_hint: str = Field(
        ..., description="The visual cue used to determine hierarchy."
    )

    id: int | None = Field(default=None, description="Internal ID for mapping.")
    start_index: int | None = Field(
        default=None, description="Absolute character index in document."
    )
    verified: bool = Field(
        False, description="Whether this header was verified in the source text."
    )


class PageIndexBlock(BaseModel):
    """A block of merged node content for embedding and retrieval."""

    id: str = Field(..., description="Content-hash ID for this block (md5 of content).")
    seq: int = Field(
        ..., description="Sequential index for ordering within the document."
    )
    token_count: int = Field(..., description="Total tokens in this block.")
    start_index: int = Field(
        ..., description="Absolute start index of the first node in this block."
    )
    end_index: int = Field(
        ..., description="Absolute end index of the last node in this block."
    )
    titles_included: list[str] = Field(
        ..., description="List of section titles contained in this block."
    )
    content: str = Field(
        ..., description="The full, merged text content (including headers)."
    )
    summary: BlockSummary | None = Field(
        default=None,
        description="Synthesized summary of this block based on its section summaries.",
    )


class TOCNode(BaseModel):
    """A node in the hierarchical table-of-contents tree."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))

    reasoning: str = Field(
        ..., description="Explain why this node belongs at this specific level."
    )
    original_header_id: int = Field(
        ..., description="The integer ID from the input list."
    )
    title: str = Field(..., description="The clean title.")
    level: int = Field(..., description="The hierarchical level.")

    children: list["TOCNode"] = Field(
        default_factory=list, description="Nested subsections."
    )

    start_index: int | None = None
    end_index: int | None = None
    content: str | None = Field(
        default=None, description="The immediate text content (excluding children)."
    )
    token_estimate: int | None = None

    summary: SectionSummary | None = Field(
        default=None, description="The 5W summary of the content."
    )

    block_id: str | None = Field(
        default=None,
        description="The hash ID of the Block this section's content was merged into.",
    )

    @computed_field  # type: ignore[prop-decorator]
    @property
    def assets(self) -> list[dict[str, Any]]:
        """Embedded image refs parsed from this section's content.

        Derived from ``content`` so the page-index thin tree (which excludes
        ``content``) still carries per-section assets after ``model_dump``.
        """
        return extract_image_refs(self.content or "")

    @property
    def content_hash(self) -> str | None:
        if self.content is None:
            return None
        return content_hash_md5(self.content)

    def _assign_content_hash_ids(self) -> None:
        """Replace UUID ids with content-hash ids. Call after hydration when content is set."""
        if self.content is not None:
            self.id = content_hash_md5(self.content)
        for child in self.children:
            child._assign_content_hash_ids()

    def tree_without_text(self, *, min_node_tokens: int = 0) -> dict[str, Any]:
        """Return a thin-tree dict with ``content`` and ``reasoning`` stripped at every level.

        Args:
            min_node_tokens: Drop nodes whose ``token_estimate`` is at or below this
                threshold.  Children of dropped nodes are promoted to the parent level.
        """
        data = self.model_dump(
            exclude={"content", "reasoning"},
            mode="json",
        )
        # model_dump exclude only applies at the top level; recurse into children.
        children: list[dict[str, Any]] = []
        for child in self.children:
            if min_node_tokens > 0 and (child.token_estimate or 0) <= min_node_tokens:
                # Skip this node but promote its children
                for grandchild in child.children:
                    children.append(
                        grandchild.tree_without_text(min_node_tokens=min_node_tokens)
                    )
            else:
                children.append(
                    child.tree_without_text(min_node_tokens=min_node_tokens)
                )
        data["children"] = children
        return data


class StructureQuality(BaseModel):
    """Assessment of how well-structured a document is based on its headers."""

    is_well_structured: bool
    header_count: int
    has_hierarchy: bool
    coverage_ratio: float
    avg_section_tokens: float
    max_gap_chars: int
    reason: str


class PageIndexOutput(BaseModel):
    """Complete output of the PageIndex indexing process."""

    toc: list[TOCNode]
    blocks: list[PageIndexBlock]
    node_to_block_map: dict[str, str]
    coverage_ratio: float = Field(
        0.0, description="Fraction of document covered by detected sections."
    )
    path_used: str = Field(
        "unknown",
        description="Which indexing path was used: 'regex_fast', 'llm_scan', or "
        "'short_doc_bypass'.",
    )

    def json_tree(self) -> str:
        return json.dumps([n.tree_without_text() for n in self.toc], indent=2)

    def get_block(self, node_id: str) -> PageIndexBlock | None:
        block_id = self.node_to_block_map.get(node_id)
        if block_id is None:
            return None
        for block in self.blocks:
            if block.id == block_id:
                return block
        return None
