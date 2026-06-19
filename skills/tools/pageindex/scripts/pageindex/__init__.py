"""Standalone, model-agnostic PageIndex generator (vendored from Memex).

Public entry point: ``index_document(full_text, lm, ...) -> PageIndexOutput``.
"""

from .indexer import AsyncMarkdownPageIndex, index_document
from .models import PageIndexBlock, PageIndexOutput, TOCNode

__all__ = [
    "AsyncMarkdownPageIndex",
    "index_document",
    "PageIndexOutput",
    "PageIndexBlock",
    "TOCNode",
]
