# StockPilot Chatbot Architecture

This document illustrates the chatbot system architecture and request flows based on the current repository design (legacy BI chat and hybrid chat) and the intended unified patterns.

## Component overview

```mermaid
flowchart LR
  subgraph FE[Next.js Frontend]
    UI[Chat UI + React Query hook\n`use-chat.ts`]
  end

  subgraph BE[FastAPI Backend]
    direction TB
    A1[/api/v1/chat/query\nLegacy BI Chat/]
    A2[/api/v1/chat2/query\nHybrid Chat (Unified)/]

    subgraph Core[Core Services]
      R[Router\nRules + Embeddings + LLM tiebreaker]
      P[Params Extractor\n`core/params.py`]
      C[Composer\n`core/composer.py`]
      V[Contracts Validator\n`core/contracts.py`]
    end

    subgraph Tools[Tools]
      DBT[DatabaseTools (BI)]
      RAG[Retriever (RAG)]
    end
  end

  subgraph LLM[LM Studio]
    LMChat[Chat Completions]
    LMEmb[Embeddings]
  end

  subgraph DATA[Data Layer]
    direction TB
    PG[(Postgres)]
    Marts[[dbt marts\n`backend/dbt/models/marts`]]
    Raw[(raw tables)]
    VS[(Vector Store\nChroma/pgvector)]
    Redis[(Redis cache):::opt]
  end

  classDef opt fill:#f8f9fa,stroke:#bbb,color:#666,stroke-dasharray: 3 3;

  UI -->|HTTP JSON| A1
  UI -->|HTTP JSON| A2

  %% Legacy BI endpoint
  A1 -->|intent rules + optional LLM fallback| C
  A1 -->|if prompt fallback| LMChat

  %% Hybrid endpoint orchestration
  A2 --> R
  R -->|BI decision| P
  R -->|RAG decision| RAG
  R -->|OPEN decision| LMChat
  R -->|Tie-breaker| LMChat

  %% BI path
  P --> DBT
  DBT -->|mart-first| Marts
  DBT -->|fallback| Raw
  Marts --> PG
  Raw --> PG
  DBT -. cache .-> Redis

  %% RAG path
  RAG --> VS
  RAG -->|answer compose or LLM assist| LMChat
  RAG -. embeddings .-> LMEmb
  R -. embeddings .-> LMEmb

  %% Composition + validation
  DBT --> C
  RAG --> C
  LMChat --> C
  C --> V

  %% Responses
  C --> A1
  C --> A2
```

Notes:

- Legacy endpoint focuses on BI intents with resilient LLM fallback for general chat.
- Hybrid endpoint routes between BI, RAG, MIXED (BI+RAG), and OPEN via Router, then composes and validates a unified response.
- BI is mart-first with explicit fallback to raw tables; no on-hand mutation anywhere (event-sourced inventory).
- LM Studio is the sole LLM provider for chat and embeddings.

## BI route – sequence

```mermaid
sequenceDiagram
  autonumber
  participant U as User (Web)
  participant FE as Next.js UI
  participant API as FastAPI /chat2/query
  participant R as Router
  participant P as Params
  participant BI as DatabaseTools
  participant DB as Postgres + dbt marts
  participant CMP as Composer
  participant VAL as Contracts

  U->>FE: Type BI-style query
  FE->>API: POST /api/v1/chat2/query { message }
  API->>R: route(message)
  R-->>API: { route: "BI", intent, confidence }
  API->>P: extract(message, org)
  P-->>API: { time_start, time_end, skus, options }
  API->>BI: run(intent, params, org)
  BI->>DB: query marts (fallback to raw)
  DB-->>BI: rows + provenance + freshness
  BI-->>API: { columns, rows, sql, definition }
  API->>CMP: compose_bi(result, confidence)
  CMP->>VAL: validate_output(unified JSON)
  VAL-->>CMP: ok
  CMP-->>API: unified response
  API-->>FE: 200 OK
  FE-->>U: Render table + metadata
```

## RAG route – sequence

```mermaid
sequenceDiagram
  autonumber
  participant U as User (Web)
  participant FE as Next.js UI
  participant API as FastAPI /chat2/query
  participant R as Router
  participant RET as RAG Retriever
  participant VS as Vector Store (org-scoped)
  participant LLM as LM Studio (chat/emb)
  participant CMP as Composer
  participant VAL as Contracts

  U->>FE: Ask policy/doc question
  FE->>API: POST /api/v1/chat2/query { message }
  API->>R: route(message)
  R-->>API: { route: "RAG", confidence }
  API->>RET: search(message, org, top_k=6)
  RET->>VS: similarity search (filters by org)
  VS-->>RET: snippets + metadata
  API->>RET: generate_answer(message, snippets)
  RET->>LLM: compose draft answer
  LLM-->>RET: answer
  RET-->>API: answer + citations
  API->>CMP: compose_rag(snippets, answer, confidence)
  CMP->>VAL: validate_output(unified JSON)
  VAL-->>CMP: ok
  CMP-->>API: unified response
  API-->>FE: 200 OK
  FE-->>U: Render answer + citations
```

## MIXED route – sequence (BI + RAG in parallel)

```mermaid
sequenceDiagram
  autonumber
  participant FE as Next.js UI
  participant API as FastAPI /chat2/query
  participant R as Router
  par BI lane
    participant P as Params
    participant BI as DatabaseTools
    participant DB as Postgres/dbt
  and RAG lane
    participant RET as RAG Retriever
    participant VS as Vector Store
    participant LLM as LM Studio
  end
  participant CMP as Composer
  participant VAL as Contracts

  FE->>API: POST { message }
  API->>R: route(message)
  R-->>API: { route: "MIXED", intent, confidence }
  par Run BI
    API->>P: extract(message, org)
    P-->>API: params
    API->>BI: run(intent, params, org)
    BI->>DB: query marts/fallback
    DB-->>BI: results
  and Run RAG
    API->>RET: search(message, org)
    RET->>VS: similarity search
    VS-->>RET: snippets
    API->>RET: generate_answer
    RET->>LLM: assist composition
    LLM-->>RET: answer
  end
  API->>CMP: compose_mixed(bi_result, rag_snippets, confidence)
  CMP->>VAL: validate_output
  VAL-->>CMP: ok
  CMP-->>API: unified response
  API-->>FE: 200 OK
```

## Multi-tenancy and guardrails

- Tenant boundary
  - Every request uses `Depends(get_current_claims)`; all DB queries filter by `org_id == claims['org']`.
  - RAG index must be partitioned or filtered by `org_id`; enforce at retrieval time to prevent cross-tenant leakage.
- Event-sourced analytics
  - Inventory on-hand is derived from movements; BI marts aggregate, never mutate stock.
- Mart-first analytics
  - Attempt dbt marts first; fallback to raw tables on failure; never rename existing response keys.
- Schema and provenance
  - All responses composed via `composer` and validated by `contracts.validate_output`.
  - BI responses include SQL/provenance/freshness; RAG responses require ≥1 citation.
- LLM constraints
  - LM Studio only (local); guardrails avoid fabricated numbers without SQL backing; OPEN route degrades gracefully.

## Performance and observability (recommended)

- Caching: BI result cache keyed by (intent, params, snapshot) with TTL; semantic cache for recent prompts.
- Parallelization: MIXED route runs BI and RAG in parallel; short-circuit on tool failures with helpful NO_ANSWER.
- Health and metrics: LM Studio health check; route distribution metrics; request/response logging and error tracking.
