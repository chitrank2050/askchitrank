# High-ROI Improvements

This page explains the recent retrieval, safety, and development-mode improvements, and why they were the best return on effort for this project.

---

## The Problem We Wanted to Solve

The original RAG pipeline was already simple and cost-aware, but it had four practical limits:

1. Source documents were too flat.
   Projects, testimonials, and LinkedIn records were mostly stored as broad plain-text blobs. That made retrieval work, but it reduced precision for questions like "What technologies did he use?" or "What do colleagues say about him?"

2. Vector search alone was sometimes too blunt.
   Pure cosine similarity is great for semantic matching, but narrative chunks can rank well for many unrelated questions. In a small portfolio corpus, that can crowd out the most factual evidence.

3. Local iteration still cost tokens.
   Even when testing small API or prompt changes, the app could hit Voyage and Groq unless the whole stack was mocked manually.

4. Unsupported questions still took the expensive path.
   Identity questions, salary questions, prompt-injection attempts, and explicit prompts could still travel too far through the pipeline even though they did not need retrieval or generation.

---

## Why These Changes Were High ROI

### 1. Better feature extraction before changing providers

The biggest gain did not come from swapping the embedding vendor.

It came from improving what the system embeds:

- project overview, contribution, and links are now separated into distinct evidence documents
- testimonials are labelled clearly as social proof
- LinkedIn profile summaries, links, and recommendations are represented as bounded retrieval-friendly documents
- retrieval hints like `Evidence Type`, `Keywords`, and `Useful for queries about` are embedded directly into the stored text

This is high ROI because better input structure usually improves retrieval quality more cheaply than changing models.

### 2. Cheap local reranking instead of more model calls

After vector search, the system now does a lightweight local rerank using:

- lexical overlap with the user query
- query intent like `projects`, `skills`, `experience`, or `feedback`
- source-aware caps so testimonials do not dominate factual questions

This is high ROI because it improves precision without:

- an extra LLM call
- an external reranker API
- a second embedding pass

### 3. Fictional seeded dev mode

`DEV_MODE=true` now enables:

- deterministic local embeddings
- fictional seeded responses instead of Groq
- fictional seeded content for Sanity, LinkedIn, and resume flows
- chat startup without a database for quick API iteration

This is high ROI because it cuts token spend and removes setup friction while preserving realistic local workflows.

### 4. Cheap safety routing before expensive model calls

The chat layer now adds:

- a pre-router for identity, private, explicit, prompt-injection, and clearly off-topic questions
- a retrieval confidence gate that stops weak evidence from reaching the LLM
- a fallback path so the bot still answers when generation or backing services are unavailable

This is high ROI because it improves safety and lowers spend at the same time. Unsupported questions now get deterministic answers without paying for the full RAG pipeline.

---

## Why We Did Not Start With Internal Embeddings

Running embeddings internally is possible, but it was not the first lever to pull.

For this project, retrieval quality was more constrained by:

- how the source material was represented
- how chunks were selected
- how unsupported questions were routed
- how much provider-backed testing cost during iteration

Changing the embedding provider first would have required re-embedding data and revisiting vector dimensions, but it would not automatically fix weak feature extraction or poor chunk selection.

---

## What Improved in Practice

### Project and skill questions

These benefit from:

- structured project evidence
- technology-heavy mini-documents
- source bias toward resume and project content

### Experience questions

These benefit from:

- stronger weighting for resume and LinkedIn profile evidence
- less interference from testimonial-style narrative text

### Feedback and testimonial questions

These benefit from:

- explicit testimonial and recommendation labelling
- local reranking that boosts social-proof sources when the question asks for feedback

### Local development

This benefits from:

- no accidental provider spend
- no need to keep database credentials configured for basic API work
- deterministic seeded behaviour that is easier to debug

### Unsupported and weakly grounded questions

These now benefit from:

- cheap canned responses for obvious identity, private, explicit, and off-topic requests
- a retrieval confidence gate that avoids weak-context hallucinations
- a safe fallback answer instead of a dead-end provider error

---

## Design Rule Going Forward

For this codebase, prefer improvements in this order:

1. Better source representation
2. Better chunk selection
3. Better safety routing and confidence gating
4. Better caching and cheaper local iteration
5. Provider swaps

That order usually produces the best quality-per-effort ratio for a small RAG system with strict cost limits.

---

Developed by [Chitrank Agnihotri](https://www.chitrankagnihotri.com)
