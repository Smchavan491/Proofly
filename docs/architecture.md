# Resolve: architecture
Resolve helps small PayPal sellers prevent and respond to disputes.

Flow:
1. A paid order opens a case file. A plain-code readiness score flags missing proof, such as no tracking number.
2. When a dispute arrives, the Classifier agent labels the claim and the Strategy agent recommends fight, refund or partial offer.
3. The Writer agent drafts a reply that cites evidence IDs. The Reviewer agent rejects unsupported claims, with at most 2 rewrite loops.
4. The seller approves, edits or refunds in the dashboard.
5. The Action service sends the result to PayPal after approval. No LLM writes to PayPal directly.

Parts:
- backend/ : FastAPI app, database models, agents, PayPal client, Action service
- web/ : React dashboard
- fixtures/llm/ : recorded AI responses for demo mode
- docs/ : architecture and demo script

Database tables: cases, evidence_items, agent_runs, recommendations, drafts, actions, outcomes.