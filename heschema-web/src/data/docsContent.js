import { ASSERT_EXPRESSION_PAGES } from './assertExpressionDocs';

/**
 * Comprehensive HESchema Documentation Content
 * Complete technical reference, research data, architecture, examples, and vocabulary guides.
 * Formatted with clear semantic headings for dynamic Table of Contents generation.
 */

export const DOCS_SECTIONS = [
  {
    id: 'getting-started',
    title: 'Getting Started',
    pages: [
      { id: 'overview', title: 'What is HESchema?' },
      { id: 'quickstart', title: 'Quick Start & CLI' },
      { id: 'architecture', title: 'System Architecture' },
      { id: 'why-heschema', title: 'Why HESchema? (Core Motivation)' }
    ]
  },
  {
    id: 'concepts',
    title: 'Concepts & Problem Statement',
    pages: [
      { id: 'problem-statement', title: 'The Problem Ordinary Schemas Cannot Fix' },
      { id: 'statestore-locking', title: 'StateStore & Optimistic Locking (HTTP 409)' },
      { id: 'tool-envelopes', title: 'Tool Envelopes vs Raw Documents' },
      { id: 'execution-boundary', title: 'Execution Boundary (executionAuthorized: false)' },
      { id: 'repair-coordinator', title: 'RFC 6901 Repair Feedback Loop' }
    ]
  },
  {
    id: 'vocabularies',
    title: 'Custom Vocabularies (Draft 2020-12)',
    pages: [
      { id: 'vocab-overview', title: 'Vocabularies & Dialect Meta-Schemas' },
      { id: 'vocab-field-comparison', title: 'Field Comparison v1 Dialect' },
      { id: 'vocab-keyed-uniqueness', title: 'Keyed Uniqueness v1 Dialect' },
      { id: 'vocab-relationships-v2', title: 'Relationships v2 (Aggregates & References)' },
      { id: 'vocab-relationships-v3', title: 'Relationships v3 (Order & Intervals)' },
      { id: 'vocab-relationships-v4', title: 'Relationships v4 (Decimal Arithmetic)' },
      { id: 'vocab-assert-expression-v1', title: 'JSON Assertion Expressions v1' },
      { id: 'vocab-ml-v1', title: 'ML v1 (Dense Tensor Shapes)' }
    ]
  },
  {
    id: 'keywords',
    title: 'Assertion Keywords Reference',
    pages: [
      { id: 'kw-compareFields', title: 'compareFields', keywordId: 'compareFields' },
      { id: 'kw-uniqueKeys', title: 'uniqueKeys', keywordId: 'uniqueKeys' },
      { id: 'kw-aggregateCompare', title: 'aggregateCompare', keywordId: 'aggregateCompare' },
      { id: 'kw-localReferences', title: 'localReferences', keywordId: 'localReferences' },
      { id: 'kw-sortedBy', title: 'sortedBy', keywordId: 'sortedBy' },
      { id: 'kw-nonOverlapping', title: 'nonOverlapping', keywordId: 'nonOverlapping' },
      { id: 'kw-arithmeticEquals', title: 'arithmeticEquals', keywordId: 'arithmeticEquals' },
      { id: 'kw-tensorShapes', title: 'tensorShapes', keywordId: 'tensorShapes' },
      { id: 'kw-assertExpression', title: 'assertExpression' },
      { id: 'kw-contract-assertions', title: 'Contract Assertions (bindings & rules)' }
    ]
  },
  {
    id: 'research',
    title: 'Empirical Research & Experiments',
    pages: [
      { id: 'controlled-eval', title: '65-Case Controlled Evaluation Study' },
      { id: 'h60-latency-study', title: 'H60 Latency Replication (2,160 slots)' },
      { id: 'offline-rescore', title: 'Independent Offline Rescoring Report' },
      { id: 'honest-audits', title: 'Negative Results & Honest Scientific Audit' }
    ]
  },
  {
    id: 'examples',
    title: 'Real World Examples & Contracts',
    pages: [
      { id: 'flight-booking-example', title: 'Flight Booking Tool & State Mismatch' },
      { id: 'peppol-invoice-example', title: 'Peppol Invoice & Minor Units' },
      { id: 'custom-trip-example', title: 'Custom Trip with Context Bindings' },
      { id: 'ml-embedding-example', title: 'ML Tensor Alignment Pipeline' },
      { id: 'sdk-langchain-workflow', title: 'Python SDK & LangChain Integration' }
    ]
  }
];

export const DOCS_PAGES = {
  ...ASSERT_EXPRESSION_PAGES,
  // --- GETTING STARTED ---
  'overview': {
    title: 'What is HESchema?',
    category: 'Getting Started',
    breadcrumbs: ['Documentation', 'Getting Started', 'What is HESchema?'],
    summary: 'A runnable schema-effect experiment harness and state-aware tool-argument validator.',
    isHomeHub: true,
    content: `
HESchema is an open-source evaluation harness and state-aware validation engine built for Large Language Model (LLM) tool arguments, structured document outputs, and JSON Schema Draft 2020-12 extensions.

## The Dual Mission of HESchema

HESchema specifically answers two separate, fundamental questions:
1. **“Is this specific LLM-generated argument safe and correct?”**
   Check strict JSON syntax, the tool contract, a user-confirmed state snapshot, and declared application policies. Return \`PASS\` or \`FAIL\`, with actionable diagnostic reasons.
2. **“How much does this JSON Schema improve or harm this model on this task domain?”**
   Run identical benchmark tasks through no-schema (\`prompt_only\`), minimal-schema, and candidate-schema arms. Compare first-pass correct-and-valid success with paired statistics, retries, token usage, cost, and latency.

## The Critical Safety Principle
> [!IMPORTANT]
> **Important Safety Principle:** \`PASS\` means the implemented checks passed. It is **not** a universal safety certification, proof that an extracted state is true, or permission to book/pay. This project never executes flight bookings, payments, calendar writes, or inventory changes without a separate authorized human boundary. Every output strictly maintains \`executionAuthorized: false\`.

## Documentation Overview & Primary Hubs

Explore the primary sections of HESchema documentation:
- **Concepts & Architecture:** Understand how StateStore, optimistic concurrency, and tool envelopes work.
- **Custom Vocabularies:** Learn how Draft 2020-12 meta-schemas add cross-field, uniqueness, and temporal checks.
- **Assertion Keywords:** Full technical references and embedded interactive playgrounds for the eight dedicated keywords, plus a JSON-only assertExpression reference.
- **Empirical Research & Evaluations:** Rigorous data from our 65-case and 2,160-slot controlled experiments.
- **Real-World Examples:** Ready-to-use contracts for flights, invoices, travel, and machine learning.

## Key Capabilities Included
- **480 distinct, reproducible synthetic benchmark cases**: 6 domains × 80 tasks, with hidden evaluation oracles.
- **36 schema fixtures**: reference, minimal, rich, weak, contradictory, and complex-but-equivalent variants.
- **Strict Draft 2020-12 schema checking**, date-format assertions, bounded evaluator caches, and compiled immutable state bindings.
- **SQLite-backed confirmed/versioned state**: optimistic locking with stale-state rejection (HTTP 409).
- **8 Custom Vocabulary Keywords**: \`compareFields\`, \`uniqueKeys\`, \`aggregateCompare\`, \`localReferences\`, \`sortedBy\`, \`nonOverlapping\`, \`arithmeticEquals\`, and \`tensorShapes\`.
- **Category-v1 Actionable Repair Feedback**: structured RFC 6901 JSON pointer diffs fed back to models on failure.
- **Multi-provider adapters**: Ollama, Groq, Mistral, Gemini, OpenRouter, Hugging Face, OpenAI, Anthropic, and offline mock stubs.

## Next Steps
- Continue to [Quick Start & CLI](quickstart) to install and run HESchema locally.
- Review [System Architecture](architecture) for the pipelined provider transport and validation engine.
- Or jump directly into the [Interactive Playground](#) in the top navigation bar.
`
  },

  'quickstart': {
    title: 'Quick Start & CLI',
    category: 'Getting Started',
    breadcrumbs: ['Documentation', 'Getting Started', 'Quick Start'],
    summary: 'How to install, configure, and run HESchema locally.',
    content: `
## Prerequisites
- Python 3.11+
- Node.js 18+ (for UI and optional Blaze worker)

## Installation from Git
Clone the official repository and set up a Python virtual environment:

\`\`\`bash
git clone https://github.com/HarshPopat23/HESchema-.git
cd HESchema-
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\\Scripts\\activate
pip install -e '.[dev]'
cp .env.example .env
\`\`\`

## Verify Installation & Offline Benchmarks
Run the test suite and verify the offline mock pipeline:

\`\`\`bash
heschema dataset
pytest -q
heschema benchmark --provider mock --repeats 1 --repairs 0 --out results/offline
\`\`\`

## Launch the Local Service
Start the local FastAPI server with OpenAPI documentation:

\`\`\`bash
python -m heschema.cli serve --port 8000
\`\`\`

The interactive API documentation is available at **http://127.0.0.1:8000/docs**, and the machine-readable OpenAPI schema is at **/openapi.json**.

## Testing the REST API via cURL

### 1. Create Proposed State
\`\`\`bash
curl -s http://127.0.0.1:8000/states -H 'Content-Type: application/json' -d '{
  "prompt": "Find flights from Jaipur to Goa on 2027-01-01 for one traveller",
  "state": {"origin": "Jaipur", "destination": "Goa", "departureDate": "2027-01-01", "travellers": 1}
}'
\`\`\`

### 2. Confirm State Snapshot
\`\`\`bash
curl -s http://127.0.0.1:8000/states/STATE_ID/confirm \\
  -H 'Content-Type: application/json' -d '{"version": 1}'
\`\`\`

### 3. Validate Generated Tool Arguments
\`\`\`bash
curl -s http://127.0.0.1:8000/validate -H 'Content-Type: application/json' -d '{
  "stateId": "STATE_ID",
  "stateVersion": 1,
  "domain": "flights",
  "output": {
    "action": "call_tool",
    "tool": "search_flights",
    "arguments": {
      "origin": "Jaipur",
      "destination": "Goa",
      "departureDate": "2027-01-01",
      "travellers": 1
    },
    "missingFields": [],
    "reason": "Flight search"
  }
}'
\`\`\`
`
  },

  'architecture': {
    title: 'System Architecture',
    category: 'Getting Started',
    breadcrumbs: ['Documentation', 'Getting Started', 'Architecture'],
    summary: 'The pipelined components connecting clients, state stores, LLM providers, and validation engines.',
    content: `
HESchema separates concerns into isolated layers: client transport, versioned state store, immutable contract registry, provider transport, schema engine, and repair coordinator.

## System Architecture Flow

\`\`\`
Client / Web UI / Agent
         │ (REST / SSE Stream)
         ▼
JHSchema Proxy & API (CORS, Request-ID, Single-Operator Bearer Auth)
         │
    ┌────┴──────────────────────────┐
    ▼                               ▼
StateStore                     ContractRegistry
(SQLite WAL / Versioning)      (Draft 2020-12 Schemas, Bindings, Rules)
    │                               │
    └────┬──────────────────────────┘
         ▼
Pipelined Provider Transport (Pacing lock, backoff)
         │
         ▼
Remote LLM Provider (Ollama / Groq / Anthropic / Gemini / etc.)
         │ (Raw Model Generation)
         ▼
SchemaEngine & Relational Rule Validator
(JSON Schema 2020-12 + Custom Dialects + Arithmetic Epsilon Engine)
         │
         ├──────────────────────────────┐
         ▼ (PASS)                       ▼ (FAIL)
Accepted Output / Stream        Repair Coordinator (RFC 6901 Diffs)
                                        │ (Targeted Feedback Prompt)
                                        └──────> Re-query LLM
\`\`\`

## Architectural Subsystems

### 1. StateStore (SQLite in WAL Mode)
Persists snapshots of user-confirmed facts. It assigns monotonically increasing integer versions. When an operator or LLM extracts candidate state, it remains *unconfirmed* until an explicit confirmation action. Any modification increments the version and invalidates existing confirmations.

### 2. ContractRegistry
Holds immutable schemas, tool specifications, context bindings, and relational rules. A contract ID and version pair is strictly immutable; updating a contract requires publishing a new version.

### 3. Pipelined Provider Transport
Manages LLM API concurrency. To prevent rate limit storms and ensure reproducible timing, it employs an internal reservation lock with configurable intervals, distinct from provider-level network retries.

### 4. SchemaEngine & Rule Evaluator
Evaluates three distinct layers:
- *Layer 1: Structural JSON Schema Draft 2020-12* (types, bounds, regex, enums).
- *Layer 2: Custom Vocabulary Dialects* (\`compareFields\`, \`uniqueKeys\`, etc.).
- *Layer 3: State-Aware Bindings & Relational Rules* (checking whether generated fields match user-confirmed context).

### 5. Repair Coordinator
When an evaluation fails, rather than discarding output or sending generic error text, the coordinator computes RFC 6901 JSON pointer diffs and generates concise, category-specific prompts (Category-v1: \`invalid_json\`, \`source_value\`, \`relationship\`, \`schema\`).
`
  },

  'why-heschema': {
    title: 'Why HESchema? (Core Motivation)',
    category: 'Getting Started',
    breadcrumbs: ['Documentation', 'Getting Started', 'Why HESchema?'],
    summary: 'The rationale behind building state-aware validation instead of relying solely on JSON Schema.',
    content: `
In recent years, LLM providers introduced *Structured Outputs* (OpenAI JSON Mode, Ollama GBNF grammars, Anthropic tool use). While this was a major milestone, industry practitioners encountered a dangerous misconception:

> **The Fallacy:** "If the LLM's output conforms to my JSON Schema, it is valid and safe to execute."

This belief is fundamentally broken. Standard JSON Schema only checks **syntactic structure and primitive constraints**. It is completely blind to **semantic ground truth** and **multi-field relational rules**.

## Real-World Failure Scenarios

### 1. The Hallucinated Destination (Flight Booking)
- **User Prompt:** "Book a flight from Jaipur to Goa for 1 passenger on 2027-01-01."
- **User Confirmed State:** \`origin: "Jaipur"\`, \`destination: "Goa"\`.
- **LLM Generated Output:**
\`\`\`json
{
  "tool": "search_flights",
  "arguments": {
    "origin": "Jaipur",
    "destination": "Pune",
    "departureDate": "2027-01-01",
    "travellers": 1
  }
}
\`\`\`
- **Standard JSON Schema Result:** \`VALID\` (Because \`"Pune"\` is a valid string, \`1\` is an integer, and the date matches the regex).
- **HESchema Result:** \`FAIL: STATE_MISMATCH\` at \`/arguments/destination\`. Confirmed state \`"Goa"\` does not match generated \`"Pune"\`.

### 2. Arithmetic Drift in Invoicing
Standard JSON Schema cannot express:
\`totalAmount == quantity * unitPrice\`
A model can output \`quantity: 5\`, \`unitPrice: 10\`, \`totalAmount: 999\`. Standard JSON Schema accepts all three integers without batting an eye.

### 3. Temporal Inversions in Booking Dates
Standard JSON Schema cannot express:
\`startDate < endDate\`
A model can output \`startDate: "2027-05-10"\` and \`endDate: "2027-05-01"\`. Standard JSON Schema accepts both strings because both match the \`date\` format.

HESchema was designed specifically to close these critical gaps.
`
  },

  // --- CONCEPTS ---
  'problem-statement': {
    title: 'The Problem Ordinary Schemas Cannot Fix',
    category: 'Concepts',
    breadcrumbs: ['Documentation', 'Concepts', 'Problem Statement'],
    summary: 'Why type-level schemas cannot solve semantic correctness and relational constraints.',
    content: `
## Pod Scheduling & State Gates
Like Kubernetes pods that enter a \`SchedulingGated\` state before placement, LLM tool arguments must pass through state-bound gates before execution authorization.

## Ordinary Schema vs Semantic Ground Truth

A standard JSON Schema Draft 2020-12 schema operates in a vacuum. It evaluates an isolated JSON document against static structural rules:

| Constraint Type | Can Ordinary JSON Schema Enforce? | How HESchema Solves It |
|---|:---:|---|
| Field data types (string, integer, boolean) | Yes | Standard Draft 2020-12 |
| String lengths and regex patterns | Yes | Standard Draft 2020-12 |
| Numeric bounds (minimum, maximum) | Yes | Standard Draft 2020-12 |
| Allowed enumerations | Yes | Standard Draft 2020-12 |
| **Cross-field comparison (\`minReplicas <= maxReplicas\`)** | **No** | Vocabulary keyword: \`compareFields\` |
| **Ordered chronological dates (\`checkIn < checkOut\`)** | **No** | Vocabulary keyword: \`compareFields\` (\`mode: "date"\`) |
| **Array uniqueness on composite keys (\`[datasetId, sampleId]\`)** | **No** | Vocabulary keyword: \`uniqueKeys\` |
| **Aggregate consistency (\`itemCount == len(items)\`)** | **No** | Vocabulary keyword: \`aggregateCompare\` |
| **Exact sum validation (\`total == sum(items.price)\`)** | **No** | Vocabulary keyword: \`aggregateCompare\` |
| **Document-internal foreign keys (\`predictions -> samples\`)** | **No** | Vocabulary keyword: \`localReferences\` |
| **Monotonic sorting (\`sortedBy: /timestamp\`)** | **No** | Vocabulary keyword: \`sortedBy\` |
| **Interval collision detection (\`nonOverlapping: [start, end)\`)** | **No** | Vocabulary keyword: \`nonOverlapping\` |
| **Exact decimal arithmetic without float drift** | **No** | Vocabulary keyword: \`arithmeticEquals\` |
| **Tensor shape & rank alignment (\`["batch", 768]\`)** | **No** | Vocabulary keyword: \`tensorShapes\` |
| **Matching user-approved context facts (e.g. Goa)** | **No** | StateStore Bindings & Optimistic Concurrency |

## Application-Level Consequences
Without declarative cross-field rules, engineers are forced to write brittle, ad-hoc post-processing scripts in application code, losing the benefits of structured declarative schemas and uniform error reporting.
`
  },

  'statestore-locking': {
    title: 'StateStore & Optimistic Locking (HTTP 409)',
    category: 'Concepts',
    breadcrumbs: ['Documentation', 'Concepts', 'StateStore & Locking'],
    summary: 'Handling concurrency, unconfirmed proposals, and stale state detection.',
    content: `
## State Lifecycle & Trust States

In an AI agent workflow, information evolves dynamically:
1. **Unconfirmed Extraction**: The system or LLM proposes state facts from a conversation or document (e.g., \`{origin: "Jaipur", destination: "Goa"}\`). **Extraction is never ground truth.**
2. **Operator/Agent Confirmation**: An explicit confirmation event pins these facts to a specific integer \`version: 1\` in SQLite.
3. **Generation & Evaluation**: When the model generates tool arguments, the validator verifies them against the pinned context version.
4. **Stale Modification (HTTP 409)**: If any field in the context is updated, the version increments to \`version: 2\` and existing confirmation is removed. Any in-flight validation against \`version: 1\` is immediately rejected with **HTTP 409 Conflict**.

## Concurrency Sequence & HTTP 409

\`\`\`
Client / UI                HESchema API                SQLite StateStore
     │                           │                            │
     │── 1. POST /states ───────>│                            │
     │   (propose facts)         │── Insert unconfirmed ─────>│
     │<── Returns stateId, v1 ───│                            │
     │                           │                            │
     │── 2. POST /confirm ──────>│                            │
     │   (confirm version 1)     │── Set confirmed=true ─────>│
     │<── HTTP 200 Confirmed ────│                            │
     │                           │                            │
     │── 3. (User edits origin) ─>│                            │
     │   POST /states/{id}       │── Increment version to 2 ─>│
     │                           │   Remove confirmed flag    │
     │                           │                            │
     │── 4. In-flight LLM calls ─>│                            │
     │   POST /validate (with v1)│── Check state version ────>│
     │                           │   (v1 != v2: STALE!)       │
     │<── HTTP 409 Conflict ─────│                            │
\`\`\`

## Immutability & Pinned Versions
This guarantees that an LLM agent cannot act on outdated or superseded information.
`
  },

  'tool-envelopes': {
    title: 'Tool Envelopes vs Raw Documents',
    category: 'Concepts',
    breadcrumbs: ['Documentation', 'Concepts', 'Tool Envelopes'],
    summary: 'Distinguishing standalone documents from tool invocation action wrappers.',
    content: `
## Document vs Tool Envelope Distinction

HESchema contracts support two distinct output kinds:
- \`outputKind: "document"\`: The model generates a standalone business document (e.g., an invoice, a patient record, a configuration YAML).
- \`outputKind: "tool_envelope"\`: The model generates an action payload designed to invoke a specific tool or function.

## Tool Envelope Schema Specification
\`\`\`json
{
  "action": "call_tool",
  "tool": "search_flights",
  "arguments": {
    "origin": "Jaipur",
    "destination": "Goa",
    "departureDate": "2027-01-01",
    "travellers": 1
  },
  "missingFields": [],
  "reason": "Customer requested flight search"
}
\`\`\`

## Pointer Scoping under Arguments
When evaluating a \`tool_envelope\`, all contract bindings and keyword pointers evaluate relative to the \`/arguments\` object rather than the envelope root.
`
  },

  'execution-boundary': {
    title: 'Execution Boundary (executionAuthorized: false)',
    category: 'Concepts',
    breadcrumbs: ['Documentation', 'Concepts', 'Execution Boundary'],
    summary: 'Why validation pass is not an authorization to execute real side-effects.',
    content: `
## Why Validation Pass Is Not Execution Permit

A core architectural tenet of HESchema is the separation of **validation** from **authorization**.

\`\`\`json
{
  "benchmarkSuccess": true,
  "result": "PASS",
  "referenceSchemaValid": true,
  "semanticValid": true,
  "executionAuthorized": false,
  "reasons": []
}
\`\`\`

## The executionAuthorized Flag
- Passing all declared checks means the generated argument satisfies the schema and matches the confirmed context.
- It **does not prove** that the user holds sufficient bank funds, that airline seats are available, or that the user has provided real-time multi-factor biometric consent.

## Downstream Human-in-the-Loop Integration
Real side effects (financial transactions, database mutations, calendar writes) must be handled by an independent downstream authorization gate with authentication, idempotency keys, and explicit user consent.
`
  },

  'repair-coordinator': {
    title: 'RFC 6901 Repair Feedback Loop',
    category: 'Concepts',
    breadcrumbs: ['Documentation', 'Concepts', 'Repair Coordinator'],
    summary: 'Generating targeted, structured diagnostic feedback for failed model outputs.',
    content: `
## Limitations of Generic Re-Prompting
When an LLM generates invalid JSON or fails contract checks, common naive implementations simply re-prompt the model with: *"Your output was invalid, try again."*
Research shows this generic feedback fails to repair complex errors.

## Category-v1 Feedback Directives
HESchema implements **Category-v1 Actionable Repair Feedback**:
1. **\`invalid_json\`**: Reports exact parser byte offsets and line/column numbers.
2. **\`source_value\`**: Reports the exact RFC 6901 pointer where the generated value deviated from the confirmed context.
3. **\`relationship\`**: Pinpoints failing cross-field rules (e.g. \`total != quantity * unitPrice\`), instructing the model to adjust calculated targets without mutating protected context values.
4. **\`schema\`**: Identifies failing JSON Schema keywords, paths, and branch diagnostics for \`oneOf\` / \`anyOf\` unions.

## RFC 6901 Diff Generation
\`\`\`
[HESchema Repair Directive (category-v1: source_value)]
Validation failed at pointer: /arguments/destination
Expected value bound to confirmed context: "Goa"
Received generated value: "Pune"
Directive: Correct the destination property to match confirmed context "Goa". Do not alter other fields.
\`\`\`
`
  },

  // --- CUSTOM VOCABULARIES ---
  'vocab-overview': {
    title: 'Vocabularies & Dialect Meta-Schemas',
    category: 'Custom Vocabularies',
    breadcrumbs: ['Documentation', 'Vocabularies', 'Overview'],
    summary: 'How HESchema extends JSON Schema Draft 2020-12 using standard $vocabulary definitions.',
    content: `
## The Draft 2020-12 Vocabulary Mechanism
JSON Schema Draft 2020-12 introduced the \`$vocabulary\` keyword, allowing dialect authors to declare custom vocabularies and specify whether an implementation must support them (\`true\`) or may ignore them (\`false\`).

## Dialect Meta-Schemas Inventory
HESchema implements custom vocabularies as first-class Draft 2020-12 extensions. Each vocabulary has its own versioned dialect meta-schema hosted in the repository:

| Dialect Name | Root Meta-Schema $id | Keywords Included |
|---|---|---|
| **Field Comparison v1** | \`.../src/heschema/field-comparison-v1.json\` | \`compareFields\` |
| **Keyed Uniqueness v1** | \`.../src/heschema/relationships-v1.json\` | \`uniqueKeys\`, \`compareFields\` |
| **Relationships v2** | \`.../src/heschema/relationships-v2.json\` | \`aggregateCompare\`, \`localReferences\`, plus v1 keywords |
| **Relationships v3** | \`.../src/heschema/relationships-v3.json\` | \`sortedBy\`, \`nonOverlapping\`, plus v2 keywords |
| **Relationships v4** | \`.../src/heschema/relationships-v4.json\` | \`arithmeticEquals\`, plus v3 keywords |
| **ML v1** | \`.../src/heschema/ml-v1.json\` | \`tensorShapes\` |

## Opt-In via $schema
To use any HESchema custom vocabulary, simply declare the dialect's URI in the root \`$schema\` of your JSON document:

\`\`\`json
{
  "$schema": "https://raw.githubusercontent.com/HarshPopat23/HESchema-/main/src/heschema/relationships-v2.json",
  "type": "object",
  "properties": {
    "itemCount": { "type": "integer" },
    "items": { "type": "array" }
  },
  "aggregateCompare": [
    { "left": "/itemCount", "operator": "eq", "right": { "count": "/items" } }
  ]
}
\`\`\`
`
  },

  'vocab-field-comparison': {
    title: 'Field Comparison v1 Dialect',
    category: 'Custom Vocabularies',
    breadcrumbs: ['Documentation', 'Vocabularies', 'Field Comparison v1'],
    summary: 'The field-comparison dialect introduces compareFields for intra-document pointer comparisons.',
    content: `
## Meta-Schema Declaration
The Field Comparison v1 dialect adds relational comparison assertions to Draft 2020-12.

\`\`\`json
{
  "$id": "https://raw.githubusercontent.com/HarshPopat23/HESchema-/main/src/heschema/field-comparison-v1.json",
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$vocabulary": {
    "https://raw.githubusercontent.com/HarshPopat23/HESchema-/main/vocabulary/field-comparison/v1/": true
  }
}
\`\`\`

## Primary Assertion
- \`compareFields\`: Array of comparison objects. Evaluates \`left\` RFC 6901 pointer against \`right\` RFC 6901 pointer using operators \`eq\`, \`ne\`, \`lt\`, \`lte\`, \`gt\`, or \`gte\` under modes \`json\`, \`number\`, or \`date\`.
`
  },

  'vocab-keyed-uniqueness': {
    title: 'Keyed Uniqueness v1 Dialect',
    category: 'Custom Vocabularies',
    breadcrumbs: ['Documentation', 'Vocabularies', 'Keyed Uniqueness v1'],
    summary: 'Unique single and composite keys across array elements.',
    content: `
## Limitations of uniqueItems
Standard JSON Schema \`uniqueItems: true\` only checks whether entire items are structurally identical. In real business applications, two records might have different timestamps or notes, but duplicate primary keys (e.g. \`sku\` or \`[datasetId, sampleId]\`).

## The uniqueKeys Assertion
\`uniqueKeys\` checks whether the tuples resolved by pointer from each item are distinct across array elements.
`
  },

  'vocab-relationships-v2': {
    title: 'Relationships v2 (Aggregates & References)',
    category: 'Custom Vocabularies',
    breadcrumbs: ['Documentation', 'Vocabularies', 'Relationships v2'],
    summary: 'Mathematical counts, sums, and relational foreign-key references.',
    content: `
## Overview of Relationships v2
Relationships v2 builds upon v1, introducing:

## The aggregateCompare Keyword
Validates scalar numbers, array counts, and integer item sums.

## The localReferences Keyword
Validates intra-document foreign-key relationships between source arrays and target arrays.
`
  },

  'vocab-relationships-v3': {
    title: 'Relationships v3 (Order & Intervals)',
    category: 'Custom Vocabularies',
    breadcrumbs: ['Documentation', 'Vocabularies', 'Relationships v3'],
    summary: 'Monotonic ordering and interval collision assertions.',
    content: `
## Overview of Relationships v3
Relationships v3 adds temporal and geometric assertions to the v2 dialect:

## The sortedBy Keyword
Enforces monotonic ascending or descending ordering over numbers, calendar dates, or ISO 8601 timestamps.

## The nonOverlapping Keyword
Detects collisions across intervals in half-open \`[start, end)\` or closed \`[start, end]\` coordinate spaces.
`
  },

  'vocab-relationships-v4': {
    title: 'Relationships v4 (Decimal Arithmetic)',
    category: 'Custom Vocabularies',
    breadcrumbs: ['Documentation', 'Vocabularies', 'Relationships v4'],
    summary: 'Arbitrary precision decimal arithmetic with configurable rounding modes.',
    content: `
## Floating-Point Inaccuracy in Financial Data
IEEE 754 floating-point numbers often suffer from binary rounding errors (e.g. \`0.1 + 0.2 = 0.30000000000000004\`). In invoices, financial ledger systems, and scientific reporting, this drift leads to false rejections.

## The arithmeticEquals Keyword
\`arithmeticEquals\` operates strictly on **decimal strings** up to 38 digits, supporting rational arithmetic and standard rounding modes (\`half-even\`, \`half-up\`, \`toward-zero\`).
`
  },

  'vocab-ml-v1': {
    title: 'ML v1 (Dense Tensor Shapes)',
    category: 'Custom Vocabularies',
    breadcrumbs: ['Documentation', 'Vocabularies', 'ML v1'],
    summary: 'Validating shapes, ranks, and batch dimensions of multidimensional tensors.',
    content: `
## The Machine Learning Tensor Profile
The ML v1 dialect provides \`tensorShapes\` for AI and data science applications where multidimensional embeddings, matrices, or label vectors are passed through JSON.

## Supported Dimension Types
- Fixed integer dimension lengths (e.g. \`768\` for BERT embeddings).
- Symbolic dimensions (e.g. \`"batch"\`) scoped across multiple tensors to guarantee cardinality alignment.
- Anonymous dimensions (\`null\`) ensuring rectangular structure without fixing size.
`
  },

  // --- KEYWORDS ---
  'kw-contract-assertions': {
    title: 'Contract Assertions (bindings & rules)',
    category: 'Assertion Keywords',
    breadcrumbs: ['Documentation', 'Keywords', 'Contract Assertions'],
    summary: 'Application-level contract rules: bindings, contextSchema, and relational operations.',
    content: `
## Overview of Application Assertions
In addition to JSON Schema custom vocabularies, HESchema contracts provide first-class application assertions:

## The bindings Mechanism
Maps fields in the generated instance directly to user-confirmed context pointers:
\`\`\`json
{
  "bindings": [
    { "instanceLocation": "/destination", "contextLocation": "/destination" },
    { "instanceLocation": "/travellers", "contextLocation": "/travellers" }
  ]
}
\`\`\`
If the model generates a value that deviates from the confirmed context pointer, evaluation fails with \`STATE_MISMATCH\`.

## Pre-Defined Relational Rules
Deterministic arithmetic and integrity rules:
- \`product_equals\`: \`operands: ["/qty", "/price"], target: "/total"\`
- \`sum_equals\`: \`operands: ["/subtotal", "/tax"], target: "/grandTotal"\`
- \`date_before\`: \`operands: ["/departDate", "/returnDate"]\`
- \`equals\`: Structural value equality.
- \`reference_member\`: Validates that a value exists within an approved context list.
`
  },

  // --- RESEARCH & EXPERIMENTS ---
  'controlled-eval': {
    title: '65-Case Controlled Evaluation Study',
    category: 'Empirical Research',
    breadcrumbs: ['Documentation', 'Research', 'Controlled Evaluation Report'],
    summary: 'Evaluating native grammar decoding, provider projection, and repair feedback across 13 constraint families.',
    content: `
## Study Overview & Provenance
- **Repository Commit**: \`3329b864c8bda90807a30d029b1d8d4dc603a5ea\`
- **Evaluated Model**: \`qwen3:4b-instruct\` (4.0B parameters, Q4_K_M quantization)
- **Local Engine**: Ollama 0.32.0 on AMD64 workstation (16 GB RAM)
- **Dataset**: 65 synthetic cases across 13 constraint families + 77 offline validator probes.
- **Sampling Settings**: \`temperature = 0.0\`, \`seed = 42\`, \`max_tokens = 1024\`, \`thinking = false\`.

## Primary Decoding Mode Metrics (Table 1)

| Metric | Prompt-Only (\`prompt_only\`) | Native Original (\`native_original\`) | Native Projected (\`native_projected\`) |
|:---|:---:|:---:|:---:|
| **Submitted Requests** | 65 | 65 | 65 |
| **Request Acceptance** | 100.0% (65/65) | 100.0% (65/65) | 100.0% (65/65) |
| **Valid JSON** | 0.0% (0/65) | **96.92%** (63/65) | **96.92%** (63/65) |
| **Original Schema Valid** | 0.0% (0/65) | **93.85%** (61/65) | 86.15% (56/65) |
| **Context Valid** | 0.0% (0/35) | **100.0%** (35/35) | **100.0%** (35/35) |
| **Relationships Valid** | 0.0% (0/25) | **84.0%** (21/25) | **84.0%** (21/25) |
| **Overall Task Success** | **0.0%** (0/65) | **86.15%** (56/65) | **78.46%** (51/65) |
| **Median Latency** | 24,449 ms (~24.4s) | **1,238 ms (~1.2s)** | 1,312 ms (~1.3s) |
| **Median Generated Tokens** | 460.0 tokens | **14.0 tokens** | 14.0 tokens |

## Negative Result on Provider Projection
- **Did projection improve model success?** **No.**
- Transforming \`if/then/else\` into \`oneOf\` unions increased GBNF grammar complexity for Ollama, degrading output on cases J051–J055 (**-7.75 percentage points uplift**).

## Repair Feedback Recovery Limits
- Across 88 initially unsuccessful instances, single-turn repair prompts achieved **0.0% recovery (0/88)** on the 4B parameter model.
- In 6 attempts, the model altered fields that were originally correct into incorrect values (\`correctFieldsMadeWrong = 6\`).

## Key Empirical Findings
1. Prompt-only generation without grammars failed strict JSON formatting 100% of the time at temperature 0.0.
2. Native constrained decoding was **~20x faster** in median latency and saved **~96% output tokens**.
`
  },

  'h60-latency-study': {
    title: 'H60 Latency Replication (2,160 slots)',
    category: 'Empirical Research',
    breadcrumbs: ['Documentation', 'Research', 'H60 Latency Replication'],
    summary: '2,160 completed results across 3 models, 4 arms, and 60 public-record tasks.',
    content: `
## Study Overview (2,160 Slots)
- **Completed Results**: 2,160 total slots (532 complete matched groups; 2,128 primary results after strict exclusions).
- **Tasks**: 60 public-record adaptations across 10 project domains.
- **Models**: 3 remote models evaluated with 3 repeats each across 4 operational arms.

## Latency & Acceptance Summary (Table 2)

| Approach Arm | Final Correct | Wrong Accepted | Mean Total Tokens | Median HTTP Total | Median Service Total |
|---|:---:|:---:|:---:|:---:|:---:|
| **A: Ordinary Schema** | 485/532 (91.17%) | **42** | 636.1 | 5.283s | 14.979s |
| **B: FULL Contract** | 481/532 (90.41%) | **0** | 1146.0 | 5.907s | 15.157s |
| **C: COMPACT Contract** | 475/532 (89.29%) | **0** | **946.4** | 6.064s | 15.189s |
| **D: Selective Calculations** | 479/532 (90.04%) | **0** | 988.5 | 6.017s | 15.243s |

## Primary Findings: 42 vs 0 Wrong Accepted
- **Zero Observed Wrong Acceptance**: Ordinary schema validation accepted **42 wrong answers** that were factually incorrect or relationally broken. Contracts with state bindings accepted **0 wrong answers**.

## COMPACT Contract Token Reductions
- COMPACT contracts used **17.42% to 19.53% fewer total tokens** than FULL contracts without sacrificing validation rigor.

## Latency Measurement Scopes
- Contract approaches did not improve raw inference latency over ordinary schema (median 6.06s vs 5.28s). The value of HESchema is in preventing false acceptances and enforcing correctness.
`
  },

  'offline-rescore': {
    title: 'Independent Offline Rescoring Report',
    category: 'Empirical Research',
    breadcrumbs: ['Documentation', 'Research', 'Independent Rescore'],
    summary: 'Correcting a membership-scoring defect and verifying 2,156 matched primary slots.',
    content: `
## Correction of Membership Scoring Defect
In earlier evaluations, an implementation defect in the scoring oracle treated membership-only contracts as incorrect if \`success\` returned false, despite valid relationships.

An independent offline rescoring harness was constructed to re-evaluate the raw response receipts:
- The independent checker shares the standard JSON Schema parser but implements task semantics separately.
- It pins the SHA-256 of all raw outputs in \`independent-rescore.json\`.

## Offline Rescored Results (540 Slots)

| Arm | Slots | First Correct | Final Correct | Wrong Accepted | Correct Rejected |
|---|---:|---:|---:|---:|---:|
| **Arm A (Ordinary)** | 540 | 494 | 507 | **27** | 0 |
| **Arm B (FULL)** | 540 | 436 | 489 | **0** | 0 |
| **Arm C (COMPACT)** | 540 | 446 | 485 | **0** | 0 |
| **Arm D (Calc)** | 540 | 409 | 463 | **0** | 0 |

## Conventional Application Checks Replay
Conventional application checks confirmed that HESchema's relational assertions accurately caught every invalid output that slipped through standard schema validation.
`
  },

  'honest-audits': {
    title: 'Negative Results & Honest Scientific Audit',
    category: 'Empirical Research',
    breadcrumbs: ['Documentation', 'Research', 'Negative Findings'],
    summary: 'Transparent documentation of negative results, limitations, and boundaries.',
    content: `
## Commitment to Honest Scientific Reporting
Unlike many AI marketing claims, HESchema places high emphasis on **reproducible, negative, and honest findings**:

## Negative Finding 1: Provider-Facing Projection
- **Hypothesis**: Transforming complex \`if/then/else\` schemas into explicit \`oneOf\` unions before sending to the model would improve generation success.
- **Result**: **Failed (-7.75 percentage points uplift)**.
- **Root Cause**: While offline equivalence was 100% (2,200 synthetic instances passed with 0 mismatches), expanding conditionals into \`oneOf\` unions increased GBNF grammar complexity in Ollama, causing token generation degradation on cases J051–J055.
- **Scientific Conclusion**: Do not project \`if/then/else\` into \`oneOf\` for Ollama.

## Negative Finding 2: Single-Turn Repair Limits
- **Hypothesis**: Providing actionable RFC 6901 pointer feedback on failed outputs would allow the model to repair its mistakes in a second turn.
- **Result**: **0.0% recovery (0/88)** on \`qwen3:4b-instruct\` across generic, raw, and actionable feedback styles.
- **Regression**: In 6 attempts, the model altered fields that were originally correct into wrong values (\`correctFieldsMadeWrong = 6\`).
- **Scientific Conclusion**: Smaller quantized models without chain-of-thought scratchpads cannot reliably execute single-turn targeted structural repairs.

## Boundaries and Limitations
> [!WARNING]
> There is **no measured 10x speed or LLM accuracy improvement** claim in this repository. HESchema is an evaluation and safety harness, not an optimizing compiler.
`
  },

  // --- EXAMPLES & CONTRACTS ---
  'flight-booking-example': {
    title: 'Flight Booking Tool & State Mismatch',
    category: 'Examples & Contracts',
    breadcrumbs: ['Documentation', 'Examples', 'Flight Booking Tool'],
    summary: 'A complete tool envelope contract demonstrating confirmed state binding and mismatch detection.',
    content: `
## Flight Booking Contract Definition
\`\`\`json
{
  "contract": {
    "id": "trip-demo",
    "version": "1",
    "outputKind": "tool_envelope",
    "tool": "prepare_custom_trip",
    "schema": {
      "type": "object",
      "required": ["destination", "travellers"],
      "properties": {
        "destination": { "type": "string", "minLength": 1 },
        "travellers": { "type": "integer", "minimum": 1, "maximum": 8 }
      },
      "additionalProperties": false
    },
    "bindings": [
      { "instanceLocation": "/destination", "contextLocation": "/destination" }
    ]
  }
}
\`\`\`

## Confirmed Context Snapshot (Version 1)
\`\`\`json
{
  "destination": "Goa",
  "approvedPointers": ["/destination"]
}
\`\`\`

## Counterexample State Mismatch
\`\`\`json
{
  "action": "call_tool",
  "tool": "prepare_custom_trip",
  "arguments": {
    "destination": "Pune",
    "travellers": 2
  }
}
\`\`\`

## Validator Output & Diagnostic
\`\`\`
Status: FAIL (422 Unprocessable Entity)
Reason: STATE_MISMATCH at /arguments/destination
Expected: "Goa" (Confirmed Context)
Received: "Pune" (Generated by LLM)
referenceSchemaValid: true
semanticValid: false
executionAuthorized: false
\`\`\`
`
  },

  'peppol-invoice-example': {
    title: 'Peppol Invoice & Minor Units',
    category: 'Examples & Contracts',
    breadcrumbs: ['Documentation', 'Examples', 'Peppol Invoice Calculation'],
    summary: 'Validating invoice line totals with exact arithmetic and rounding.',
    content: `
## Invoice Demo Contract Definition
\`\`\`json
{
  "contract": {
    "id": "invoice-demo",
    "version": "1",
    "outputKind": "document",
    "schema": {
      "type": "object",
      "required": ["quantity", "unitPriceMinor", "totalMinor"],
      "properties": {
        "quantity": { "type": "integer", "minimum": 1 },
        "unitPriceMinor": { "type": "integer", "minimum": 0 },
        "totalMinor": { "type": "integer", "minimum": 0 }
      },
      "additionalProperties": false
    },
    "relationships": [
      {
        "id": "invoice-total",
        "kind": "product_equals",
        "operands": ["/quantity", "/unitPriceMinor"],
        "target": "/totalMinor"
      }
    ]
  }
}
\`\`\`

## Integer Minor Unit Representation
By using integer cents/minor units (e.g. 1250 instead of 12.5), calculations avoid IEEE 754 floating-point rounding errors.

## Exact Product Equality Assertion
- \`quantity\`: 2
- \`unitPriceMinor\`: 1250 ($12.50)
- \`totalMinor\`: 2500 ($25.00)
- **Result:** \`PASS\`
`
  },

  'custom-trip-example': {
    title: 'Custom Trip with Context Bindings',
    category: 'Examples & Contracts',
    breadcrumbs: ['Documentation', 'Examples', 'Custom Trip'],
    summary: 'Handling partial approval and selective parameter authorization.',
    content: `
## Partial Context Approval Workflow
In complex workflows, a user may approve some fields (such as departure airport and travel dates), while leaving others (such as hotel preferences or meal options) open for LLM recommendation.

## Declarative Approved Pointers
HESchema's \`approvedPointers\` mechanism allows selective partial binding:
\`\`\`json
{
  "context": {
    "origin": "London",
    "destination": "Tokyo",
    "maxBudget": 3000,
    "hotelTier": "4-star"
  },
  "approvedPointers": [
    "/origin",
    "/destination"
  ]
}
\`\`\`

## Evaluation Boundaries
Here, only \`/origin\` and \`/destination\` are strictly bound to ground truth. The model is free to propose hotel options within the schema bounds without triggering \`STATE_MISMATCH\`.
`
  },

  'ml-embedding-example': {
    title: 'ML Tensor Alignment Pipeline',
    category: 'Examples & Contracts',
    breadcrumbs: ['Documentation', 'Examples', 'ML Tensor Pipeline'],
    summary: 'Validating batch sizes and embedding dimensions in ML service payloads.',
    content: `
## ML Tensor Pipeline Contract
\`\`\`json
{
  "$schema": "https://raw.githubusercontent.com/HarshPopat23/HESchema-/main/src/heschema/ml-v1.json",
  "type": "object",
  "required": ["batchId", "embeddings", "labels"],
  "properties": {
    "batchId": { "type": "string" },
    "embeddings": { "type": "array" },
    "labels": { "type": "array" }
  },
  "tensorShapes": [
    { "path": "/embeddings", "shape": ["batch", 768] },
    { "path": "/labels", "shape": ["batch"] }
  ]
}
\`\`\`

## Fixed Dimension Width Enforcement
Every vector in \`embeddings\` must have width exactly 768.

## Symbolic Batch Cardinality Alignment
The number of embedding rows matches the number of scalar labels in \`labels\` (both bind to symbol \`"batch"\`).
`
  },

  'sdk-langchain-workflow': {
    title: 'Python SDK & LangChain Integration',
    category: 'Examples & Contracts',
    breadcrumbs: ['Documentation', 'Examples', 'Python SDK & LangChain'],
    summary: 'Integrating HESchema contracts into Python agents and LangChain pipelines.',
    content: `
## Python SDK Dry-Run Pattern

\`\`\`python
from heschema import ContractRegistry, SchemaEngine, StateStore

# 1. Initialize store and registry
store = StateStore("state.sqlite")
registry = ContractRegistry(store)

# 2. Register custom contract
registry.register("examples/contracts/invoice.json")

# 3. Create confirmed state snapshot
state_id = store.create_context(
    prompt="Generate invoice for 2 widgets at $12.50",
    data={"quantity": 2, "unitPriceMinor": 1250}
)
store.confirm_context(state_id, version=1)

# 4. Dry-run validation
engine = SchemaEngine()
result = engine.validate_contract(
    contract_id="invoice-demo",
    context_id=state_id,
    output={"quantity": 2, "unitPriceMinor": 1250, "totalMinor": 2500}
)

if result.is_valid:
    print("Contract validated successfully! (Execution authorized remains false)")
else:
    print(f"Validation failed: {result.errors}")
\`\`\`

## LangChain Integration Boundary
When using HESchema inside a LangChain agent, wrap the tool invocation with HESchema's contract validator before passing arguments to the actual tool function.
`
  }
};
