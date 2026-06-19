"""PageIndex orchestrator — vendored, self-contained.

Ported behaviour-preserving from Memex
``memex_core.memory.extraction.core`` (the ``AsyncMarkdownPageIndex`` module
and the ``index_document`` entry point). Two production infrastructure shims
are replaced for standalone use:

- ``run_dspy_operation`` — the production version wraps every LLM call in a
  process-wide circuit breaker + Prometheus/OTel metrics + per-call timeout.
  That breaker is shared mutable state that would leak across invocations of a
  one-shot CLI, so here it is a minimal per-call ``dspy.context`` wrapper. The
  whole-pipeline 600s wall-clock guard in ``index_document`` is preserved.
- ``_instrument`` — a metrics span in production; a no-op context here.

Everything else (the two-path router, scanning, gap-fill, refinement,
summarisation) is identical to the source.
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
from typing import Any, Coroutine, cast

import dspy
import regex as regex_lib

from .models import (
    BlockSummary,
    DetectedHeader,
    PageIndexBlock,
    PageIndexOutput,
    StructureQuality,
    TOCNode,
    content_hash_md5,
    estimate_token_count,
)
from .signatures import (
    OrganizeStructure,
    ScanChunk,
    SummarizeBlock,
    SummarizeParentSection,
    SummarizeSection,
)
from .utils import (
    assess_structure_quality,
    build_tree_from_regex_headers,
    collect_node_summaries_for_block,
    compute_coverage,
    deduplicate_and_sort,
    detect_markdown_headers_regex,
    filter_valid_nodes,
    generate_blocks_and_assign_ids,
    hydrate_tree,
    merge_header_lists,
    verify_headers,
)

logger = logging.getLogger("pageindex.indexer")


async def run_dspy_operation(
    *,
    lm: dspy.LM,
    predictor: dspy.Module,
    input_kwargs: dict[str, Any],
    operation_name: str = "dspy",
) -> Any:
    """Run a DSPy predictor under a per-call LM context.

    Standalone replacement for ``memex_core.llm.run_dspy_operation`` with the
    same keyword signature so the ported call sites are unchanged. ``lm.copy()``
    isolates per-call history.
    """
    lm_ = lm.copy()
    with dspy.context(lm=lm_):
        return await predictor.acall(**input_kwargs)


def _instrument(name: str) -> contextlib.AbstractAsyncContextManager[None]:
    """No-op metrics span (production emits Prometheus/OTel here)."""
    return contextlib.nullcontext()


class AsyncMarkdownPageIndex(dspy.Module):
    """Hierarchical document indexer producing a TOC tree with section summaries.

    Operates in two modes:
    - **Fast path** (regex): well-structured markdown with clear header hierarchy
    - **LLM path**: unstructured or poorly-structured documents requiring LLM scanning
    """

    def __init__(
        self,
        lm: dspy.LM,
        *,
        scan_max_concurrency: int = 20,
        refine_max_concurrency: int = 20,
        summarize_max_concurrency: int = 20,
        gap_rescan_threshold_tokens: int = 2000,
    ) -> None:
        super().__init__()
        self.lm = lm
        self.scanner = dspy.ChainOfThought(ScanChunk)
        self.architect = dspy.ChainOfThought(OrganizeStructure)
        self.summarizer = dspy.ChainOfThought(SummarizeSection)
        self.parent_summarizer = dspy.ChainOfThought(SummarizeParentSection)
        self.block_summarizer = dspy.ChainOfThought(SummarizeBlock)
        self.scan_max_concurrency = scan_max_concurrency
        self.refine_max_concurrency = refine_max_concurrency
        self.summarize_max_concurrency = summarize_max_concurrency
        self.gap_rescan_threshold_tokens = gap_rescan_threshold_tokens
        # The extractor is only ever instantiated from inside an async entry
        # point (index_document), so constructing the Semaphore here is safe —
        # it binds to the running loop on first acquire.
        self._scan_semaphore = asyncio.Semaphore(scan_max_concurrency)
        self._refine_semaphore = asyncio.Semaphore(refine_max_concurrency)
        self._summary_semaphore = asyncio.Semaphore(summarize_max_concurrency)
        self._logger = logging.getLogger("pageindex.page_index")

    async def aforward(
        self,
        full_text: str,
        max_scan_tokens: int = 20_000,
        max_node_length: int = 5000,
        block_size: int = 1000,
    ) -> PageIndexOutput:
        doc_length = len(full_text)
        self._logger.info(f"Document length: {doc_length} chars")

        regex_headers = detect_markdown_headers_regex(full_text)
        quality = assess_structure_quality(regex_headers, doc_length)
        self._logger.info(f"[Assessment] {quality.reason}")

        if quality.is_well_structured:
            output = await self._fast_path(
                full_text, regex_headers, quality, max_node_length, block_size
            )
        else:
            output = await self._llm_path(
                full_text,
                regex_headers,
                quality,
                max_scan_tokens,
                max_node_length,
                block_size,
            )
        return output

    async def _fast_path(
        self,
        full_text: str,
        regex_headers: list[DetectedHeader],
        quality: StructureQuality,
        max_node_length: int,
        block_size: int,
    ) -> PageIndexOutput:
        self._logger.info(
            f"[Fast Path] Using {quality.header_count} regex-detected headers directly."
        )

        toc_tree = build_tree_from_regex_headers(regex_headers)

        self._logger.info("[Fast Path] Hydrating content")
        hydrate_tree(toc_tree, regex_headers, full_text)

        for node in toc_tree:
            node._assign_content_hash_ids()

        self._logger.info("[Fast Path] Recursive refinement")
        final_tree = await self._refine_tree_recursively(
            toc_tree, full_text, max_node_length
        )

        coverage = compute_coverage(final_tree, len(full_text))
        self._logger.info(f"[Fast Path] Coverage: {coverage:.1%}")

        self._logger.info("[Fast Path] Building blocks")
        blocks_list, node_map = generate_blocks_and_assign_ids(final_tree, block_size)

        self._logger.info("[Fast Path] Generating node summaries")
        await self._generate_summaries_parallel(final_tree)

        self._logger.info("[Fast Path] Generating block summaries")
        await self._generate_block_summaries(blocks_list, final_tree, node_map)

        return PageIndexOutput(
            toc=final_tree,
            blocks=blocks_list,
            node_to_block_map=node_map,
            coverage_ratio=coverage,
            path_used="regex_fast",
        )

    async def _llm_path(
        self,
        full_text: str,
        regex_headers: list[DetectedHeader],
        quality: StructureQuality,
        max_scan_tokens: int,
        max_node_length: int,
        block_size: int,
    ) -> PageIndexOutput:
        self._logger.info(
            "[LLM Path] Document is not well-structured. Running full LLM scan."
        )

        flat_headers = await self._scan_document_parallel(full_text, max_scan_tokens)
        flat_headers = await self._detect_and_fill_gaps(
            flat_headers, full_text, max_scan_tokens=max_scan_tokens
        )

        if not flat_headers:
            if regex_headers:
                self._logger.warning(
                    "[LLM Path] LLM scan found nothing. Falling back to partial regex headers."
                )
                return await self._fast_path(
                    full_text, regex_headers, quality, max_node_length, block_size
                )
            return PageIndexOutput(
                toc=[],
                blocks=[],
                node_to_block_map={},
                coverage_ratio=0.0,
                path_used="llm_scan",
            )

        self._logger.info("[LLM Path] Verifying headers")
        flat_headers = verify_headers(flat_headers, full_text)

        verified_count = sum(1 for h in flat_headers if h.verified)
        total_count = len(flat_headers)
        accuracy = verified_count / total_count if total_count > 0 else 0
        self._logger.info(
            f"[LLM Path] Verification: {verified_count}/{total_count} ({accuracy:.0%})"
        )

        if accuracy < 0.6 and regex_headers:
            self._logger.warning(
                "[LLM Path] Low accuracy. Merging regex headers as fallback."
            )
            flat_headers = merge_header_lists(flat_headers, regex_headers)
            flat_headers = verify_headers(flat_headers, full_text)

        flat_headers = [h for h in flat_headers if h.verified]
        for i, h in enumerate(flat_headers):
            h.id = i

        if not flat_headers:
            return PageIndexOutput(
                toc=[],
                blocks=[],
                node_to_block_map={},
                coverage_ratio=0.0,
                path_used="llm_scan",
            )

        self._logger.info("[LLM Path] Building logical structure via LLM")
        toc_tree = await self._build_logical_tree(flat_headers)

        self._logger.info("[LLM Path] Hydrating content")
        hydrate_tree(toc_tree, flat_headers, full_text)

        for node in toc_tree:
            node._assign_content_hash_ids()

        self._logger.info("[LLM Path] Recursive refinement")
        final_tree = await self._refine_tree_recursively(
            toc_tree, full_text, max_node_length
        )

        coverage = compute_coverage(final_tree, len(full_text))
        self._logger.info(f"[LLM Path] Coverage: {coverage:.1%}")

        self._logger.info("[LLM Path] Building blocks")
        blocks_list, node_map = generate_blocks_and_assign_ids(final_tree, block_size)

        self._logger.info("[LLM Path] Generating node summaries")
        await self._generate_summaries_parallel(final_tree)

        self._logger.info("[LLM Path] Generating block summaries")
        await self._generate_block_summaries(blocks_list, final_tree, node_map)

        return PageIndexOutput(
            toc=final_tree,
            blocks=blocks_list,
            node_to_block_map=node_map,
            coverage_ratio=coverage,
            path_used="llm_scan",
        )

    # ---- LLM-dependent scanning ----

    def _build_scan_tasks(
        self,
        text: str,
        max_scan_tokens: int,
        *,
        offset_base: int = 0,
        context_prefix: str = "",
        overlap_chars: int = 200,
    ) -> list[Coroutine[Any, Any, list[DetectedHeader]]]:
        """Split *text* into overlapping scan chunks and return scan coroutines.

        If *text* fits in ``max_scan_tokens``, returns a single coroutine.
        Otherwise, slices *text* into overlapping chunks of ``max_scan_tokens``
        tokens and returns one coroutine per chunk. ``offset_base`` lets callers
        translate chunk-local positions back to parent-document coordinates
        (used when rescanning a gap inside a larger document).

        ``overlap_chars`` controls how many characters of the previous slice
        bleed into the next one, so a header split across a chunk boundary is
        still detected. Callers wanting tighter overlap on dense gap rescans
        (where the whole region is a single paragraph of prose) can lower it.
        """
        doc_tokens = estimate_token_count(text)

        if doc_tokens <= max_scan_tokens:
            return [self._process_single_chunk(text, context_prefix, offset_base)]

        chars_per_token = len(text) / doc_tokens if doc_tokens > 0 else 4.0
        chunk_chars = int(max_scan_tokens * chars_per_token)
        tasks: list[Coroutine[Any, Any, list[DetectedHeader]]] = []

        for start in range(0, len(text), chunk_chars - overlap_chars):
            end = min(start + chunk_chars, len(text))
            chunk = text[start:end]
            if len(chunk) < 50:
                continue
            if start == 0:
                prev_context = context_prefix
            else:
                ctx_start = max(0, start - 200)
                prev_context = text[ctx_start:start]
            tasks.append(
                self._process_single_chunk(chunk, prev_context, offset_base + start)
            )

        return tasks

    async def _scan_document_parallel(
        self, text: str, max_scan_tokens: int
    ) -> list[DetectedHeader]:
        doc_tokens = estimate_token_count(text)
        tasks = self._build_scan_tasks(text, max_scan_tokens)

        if len(tasks) <= 1:
            self._logger.info(
                f"[LLM Path] Scanning full document ({doc_tokens} tokens) in single call."
            )
        else:
            self._logger.info(
                f"[LLM Path] Scanning document ({doc_tokens} tokens) in {len(tasks)} chunks "
                f"(max_concurrency={self.scan_max_concurrency})."
            )
        results = await asyncio.gather(*tasks)
        return deduplicate_and_sort(results)

    async def _process_single_chunk(
        self, chunk: str, prev_context: str, offset: int
    ) -> list[DetectedHeader]:
        valid_headers: list[DetectedHeader] = []
        # Gate the LLM call on the per-extractor semaphore so concurrent scan
        # tasks (from document parallelism *and* gap refill) don't fan out past
        # scan_max_concurrency on memory-constrained hosts.
        async with self._scan_semaphore:
            try:
                async with _instrument("scan"):
                    pred = await run_dspy_operation(
                        lm=self.lm,
                        predictor=self.scanner,
                        input_kwargs={
                            "chunk_text": chunk,
                            "previous_context": prev_context,
                        },
                        operation_name="extraction.header_scan",
                    )

                for h in pred.detected_headers:
                    try:
                        rel_idx = chunk.index(h.exact_text)
                        h.start_index = offset + rel_idx
                        valid_headers.append(h)
                        continue
                    except ValueError:
                        pass

                    tolerance = max(2, int(len(h.exact_text) * 0.15))
                    try:
                        pattern = (
                            f"({regex_lib.escape(h.exact_text)}){{e<={tolerance}}}"
                        )
                        match = regex_lib.search(pattern, chunk)
                        if match:
                            h.exact_text = match.group(0)
                            h.start_index = offset + match.start()
                            valid_headers.append(h)
                    except (regex_lib.error, ValueError, RuntimeError) as e:
                        self._logger.debug("Fuzzy regex match failed for header: %s", e)
            except (ValueError, RuntimeError, OSError, KeyError) as e:
                self._logger.error(f"Scanner Error at offset {offset}: {e}")

        return valid_headers

    async def _detect_and_fill_gaps(
        self,
        flat_headers: list[DetectedHeader],
        full_text: str,
        *,
        max_scan_tokens: int,
    ) -> list[DetectedHeader]:
        new_headers_tasks: list[Coroutine[Any, Any, list[DetectedHeader]]] = []
        current_idx = 0

        for header in flat_headers:
            if header.start_index is None:
                continue

            gap_text = full_text[current_idx : header.start_index]
            gap_tokens = estimate_token_count(gap_text)
            if gap_tokens > self.gap_rescan_threshold_tokens:
                self._logger.debug(
                    f"   > Omission Detected: {gap_tokens} tokens "
                    f"({len(gap_text)} chars). Re-scanning."
                )
                gap_context = full_text[max(0, current_idx - 200) : current_idx]
                new_headers_tasks.extend(
                    self._build_scan_tasks(
                        gap_text,
                        max_scan_tokens,
                        offset_base=current_idx,
                        context_prefix=gap_context,
                    )
                )

            current_idx = header.start_index + len(header.exact_text)

        tail_text = full_text[current_idx:]
        tail_tokens = estimate_token_count(tail_text)
        if tail_tokens > self.gap_rescan_threshold_tokens:
            self._logger.debug(
                f"   > Tail Omission Detected: {tail_tokens} tokens "
                f"({len(tail_text)} chars). Re-scanning."
            )
            tail_context = full_text[max(0, current_idx - 200) : current_idx]
            new_headers_tasks.extend(
                self._build_scan_tasks(
                    tail_text,
                    max_scan_tokens,
                    offset_base=current_idx,
                    context_prefix=tail_context,
                )
            )

        if not new_headers_tasks:
            return flat_headers

        recovered_batches = await asyncio.gather(*new_headers_tasks)
        combined = list(flat_headers)
        for batch in recovered_batches:
            combined.extend(batch)

        return deduplicate_and_sort([combined])

    # ---- LLM-dependent tree building ----

    async def _build_logical_tree(
        self, flat_headers: list[DetectedHeader]
    ) -> list[TOCNode]:
        minified_input = [
            {
                "id": h.id,
                "title": h.clean_title,
                "hint": h.level_hint,
                "scan_reasoning": h.reasoning[:150],
            }
            for h in flat_headers
        ]
        try:
            pred = await run_dspy_operation(
                lm=self.lm,
                predictor=self.architect,
                input_kwargs={"flat_headers_json": str(minified_input)},
                operation_name="extraction.header_architect",
            )
            max_id = len(flat_headers) - 1
            return filter_valid_nodes(pred.toc_tree, max_id)
        except (ValueError, RuntimeError, OSError, KeyError) as e:
            self._logger.error(f"Architect Logic Failed: {e}")
            return [
                TOCNode(
                    original_header_id=cast(int, h.id),
                    title=h.clean_title,
                    level=1,
                    reasoning="Fallback",
                )
                for h in flat_headers
            ]

    # ---- LLM-dependent refinement ----

    async def _refine_tree_recursively(
        self, nodes: list[TOCNode], full_text: str, max_len: int
    ) -> list[TOCNode]:
        tasks = [
            self._process_single_node_refinement(node, full_text, max_len)
            for node in nodes
        ]
        refined = await asyncio.gather(*tasks)
        return list(refined)

    async def _process_single_node_refinement(
        self, node: TOCNode, full_text: str, max_len: int
    ) -> TOCNode:
        # Gate the per-node work (chunk scan + tree-build) on the refine
        # semaphore so peer refinement tasks fan out at most
        # refine_max_concurrency at a time. The recursive call into
        # _refine_tree_recursively is deliberately *outside* this `async with`
        # block — holding the semaphore through recursion would deadlock when
        # tree depth exceeds refine_max_concurrency (every parent would hold a
        # slot waiting on its children).
        async with self._refine_semaphore, _instrument("refine"):
            node_len = (node.end_index or 0) - (node.start_index or 0)

            if node_len > max_len and not node.children:
                self._logger.debug(
                    f"   > Deep Dive: Refining '{node.title}' ({node_len} chars)"
                )

                section_text = full_text[node.start_index : node.end_index]

                sub_headers = await self._process_single_chunk(
                    section_text,
                    prev_context=f"...Inside section: {node.title}...",
                    offset=cast(int, node.start_index),
                )

                if sub_headers:
                    for idx, h in enumerate(sub_headers):
                        h.id = idx
                    sub_headers = [
                        h
                        for h in sub_headers
                        if cast(int, h.start_index) > cast(int, node.start_index) + 50
                    ]

                    sub_headers = verify_headers(sub_headers, full_text)
                    sub_headers = [h for h in sub_headers if h.verified]

                    if sub_headers:
                        for idx, h in enumerate(sub_headers):
                            h.id = idx

                        sub_tree = await self._build_logical_tree(sub_headers)
                        hydrate_tree(
                            sub_tree,
                            sub_headers,
                            full_text,
                            parent_end_index=node.end_index,
                        )

                        for child in sub_tree:
                            child._assign_content_hash_ids()

                        node.children = sub_tree

                        if sub_tree:
                            new_cutoff = sub_tree[0].start_index
                            node.content = full_text[node.start_index : new_cutoff]
                            node.token_estimate = estimate_token_count(node.content)
                            node.id = content_hash_md5(node.content)

        if node.children:
            node.children = await self._refine_tree_recursively(
                node.children, full_text, max_len
            )

        return node

    # ---- Summarization ----

    async def _generate_summaries_parallel(self, nodes: list[TOCNode]) -> None:
        nodes_to_process: list[TOCNode] = []
        parent_nodes_to_process: list[TOCNode] = []

        def collect(n_list: list[TOCNode]) -> None:
            for n in n_list:
                if n.children:
                    parent_nodes_to_process.append(n)
                elif n.content and len(n.content.strip()) > 50:
                    nodes_to_process.append(n)
                collect(n.children)

        collect(nodes)

        leaf_tasks = [self._summarize_single_node(n) for n in nodes_to_process]
        await asyncio.gather(*leaf_tasks)

        parent_tasks = [self._summarize_parent_node(n) for n in parent_nodes_to_process]
        await asyncio.gather(*parent_tasks)

    async def _summarize_single_node(self, node: TOCNode) -> None:
        try:
            safe_content = node.content if node.content else ""
            # Acquire the semaphore *before* entering _instrument so the gauge
            # reflects real concurrent in-flight rather than counting tasks
            # that are still blocked waiting on the cap.
            async with self._summary_semaphore, _instrument("summarize"):
                pred = await run_dspy_operation(
                    lm=self.lm,
                    predictor=self.summarizer,
                    input_kwargs={"title": node.title, "content": safe_content},
                    operation_name="extraction.summarize",
                )
            node.summary = pred.summary
        except (ValueError, RuntimeError, OSError, KeyError) as e:
            self._logger.warning(f"Summary failed for '{node.title}': {e}")

    async def _summarize_parent_node(self, node: TOCNode) -> None:
        try:
            safe_content = node.content if node.content else ""
            children_titles = ", ".join(c.title for c in node.children)

            if node.token_estimate and node.token_estimate < 30:
                safe_content = f"[Section header only: '{node.title}']\nChild sections: {children_titles}"

            # Semaphore acquired before _instrument so the gauge reflects real
            # concurrent in-flight, not blocked-on-cap tasks.
            async with self._summary_semaphore, _instrument("summarize"):
                pred = await run_dspy_operation(
                    lm=self.lm,
                    predictor=self.parent_summarizer,
                    input_kwargs={
                        "title": node.title,
                        "content": safe_content,
                        "children_titles": children_titles,
                    },
                    operation_name="extraction.summarize_parent",
                )
            node.summary = pred.summary
        except (ValueError, RuntimeError, OSError, KeyError) as e:
            self._logger.warning(f"Parent summary failed for '{node.title}': {e}")

    async def _generate_block_summaries(
        self,
        blocks_list: list[PageIndexBlock],
        toc_tree: list[TOCNode],
        node_to_block_map: dict[str, str],
    ) -> None:
        tasks = []

        for block in blocks_list:
            section_pairs = collect_node_summaries_for_block(
                block.id, toc_tree, node_to_block_map
            )

            if not section_pairs:
                block.summary = BlockSummary(
                    topic=", ".join(block.titles_included[:3]) or "Untitled block",
                    key_points=[],
                )
                continue

            lines = [
                f"- {title}: {fmt_summary}" for title, fmt_summary in section_pairs
            ]
            section_summaries_text = "\n".join(lines)

            tasks.append(self._summarize_single_block(block, section_summaries_text))

        if tasks:
            await asyncio.gather(*tasks)

    async def _summarize_single_block(
        self, block: PageIndexBlock, section_summaries_text: str
    ) -> None:
        try:
            # Block summaries share the summary semaphore with leaf summaries —
            # same provider, same RAM profile, one capacity budget. Semaphore
            # acquired before _instrument so the gauge reflects real
            # concurrent in-flight, not blocked-on-cap tasks.
            async with self._summary_semaphore, _instrument("block_summarize"):
                pred = await run_dspy_operation(
                    lm=self.lm,
                    predictor=self.block_summarizer,
                    input_kwargs={"section_summaries": section_summaries_text},
                    operation_name="extraction.summarize_block",
                )
            summary = pred.block_summary
            summary.key_points = [kp.rstrip(".;:, ") for kp in summary.key_points]
            block.summary = summary
        except (ValueError, RuntimeError, OSError, KeyError) as e:
            self._logger.warning(f"Block summary failed for block {block.id}: {e}")
            block.summary = BlockSummary(
                topic=", ".join(block.titles_included[:3]) or "Untitled block",
                key_points=[],
            )


async def index_document(
    full_text: str,
    lm: dspy.LM,
    max_scan_tokens: int = 20_000,
    max_node_length: int = 5000,
    block_token_target: int = 1000,
    short_doc_threshold: int = 2000,
    *,
    scan_max_concurrency: int = 20,
    refine_max_concurrency: int = 20,
    summarize_max_concurrency: int = 20,
    gap_rescan_threshold_tokens: int = 2000,
) -> PageIndexOutput:
    """Top-level function to index a document using PageIndex.

    Handles short-document bypass and delegates to AsyncMarkdownPageIndex
    for longer/structured documents.

    Args:
        full_text: The full document text to index.
        lm: DSPy language model for LLM calls.
        max_scan_tokens: Max tokens per LLM scan call. Small docs go in one call.
        max_node_length: Max characters per node before refinement.
        block_token_target: Target token count per block.
        short_doc_threshold: Documents below this with no headers bypass PageIndex.
        scan_max_concurrency: Cap on concurrent LLM scan calls during page_index
            extraction. Lower this on memory-constrained hosts.
        refine_max_concurrency: Cap on concurrent _refine_tree_recursively LLM
            calls. Lower this on memory-constrained hosts.
        summarize_max_concurrency: Cap on concurrent leaf, parent, and block
            summary LLM calls (shared across the three summary fan-outs). Lower
            this on memory-constrained hosts.
        gap_rescan_threshold_tokens: Minimum gap size (tokens) between detected
            headers that triggers a secondary LLM re-scan.

    Returns:
        PageIndexOutput with TOC tree, blocks, and coverage information.
    """
    # Short-document bypass
    regex_headers = detect_markdown_headers_regex(full_text)
    if len(full_text) < short_doc_threshold and not regex_headers:
        node = TOCNode(
            original_header_id=0,
            title="Content",
            level=1,
            reasoning="Short document bypass — single node.",
            content=full_text,
            start_index=0,
            end_index=len(full_text),
            token_estimate=estimate_token_count(full_text),
        )
        node.id = content_hash_md5(full_text)

        block = PageIndexBlock(
            id=content_hash_md5(full_text),
            seq=0,
            content=full_text,
            token_count=node.token_estimate or 0,
            titles_included=["Content"],
            start_index=0,
            end_index=len(full_text),
        )

        return PageIndexOutput(
            toc=[node],
            blocks=[block],
            node_to_block_map={node.id: block.id},
            coverage_ratio=1.0,
            path_used="short_doc_bypass",
        )

    # Full PageIndex
    indexer = AsyncMarkdownPageIndex(
        lm=lm,
        scan_max_concurrency=scan_max_concurrency,
        refine_max_concurrency=refine_max_concurrency,
        summarize_max_concurrency=summarize_max_concurrency,
        gap_rescan_threshold_tokens=gap_rescan_threshold_tokens,
    )
    # Wrap in timeout — individual LLM calls have their own timeout via dspy.LM,
    # but the full page-index pipeline (multiple sequential LLM calls) can hang
    # if any single call stalls silently.
    return await asyncio.wait_for(
        indexer.aforward(
            full_text,
            max_scan_tokens=max_scan_tokens,
            max_node_length=max_node_length,
            block_size=block_token_target,
        ),
        timeout=600,  # 10 min max for full page index pipeline
    )
