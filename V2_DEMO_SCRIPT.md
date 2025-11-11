# V2 Multi-Agent AI Platform - Demo Script

## Overview
This demo showcases the evolution from MVP to V2 multi-agent AI assistant platform with self-improving feedback loops, evaluation metrics, and A/B testing.

**Duration:** 15-20 minutes

---

## Part 1: Vector RAG & Semantic Search (3 min)

### Setup
1. Open Knowledge Base page
2. Show existing articles

### Demo Steps
1. **Demonstrate Semantic Search**
   - Search for "refund policy" (exact match)
   - Search for "money back" (semantic match - no exact keywords)
   - Show how vector embeddings find relevant articles even without exact keyword matches
   - Explain: "We upgraded from keyword matching to vector embeddings using sentence-transformers"

2. **Show Embedding Generation**
   - Create a new knowledge base article
   - Explain: "Embeddings are automatically generated and stored in ChromaDB"
   - Show the embedding field (JSON array) in the database

---

## Part 2: Multi-Agent Orchestration (5 min)

### Setup
1. Open Customer Chat interface
2. Have Agent Dashboard open in another tab

### Demo Steps
1. **Show Router Agent**
   - Send message: "Where is my order?"
   - Explain: "Router agent classifies intent as 'order_inquiry'"
   - Show intent badge in message history
   - Show agent_type: "knowledge" in response

2. **Show Knowledge Agent**
   - Send message: "What is your return policy?"
   - Show how knowledge agent retrieves relevant articles
   - Show confidence score and matched articles

3. **Show Escalation Agent**
   - Send message: "I want to speak to a human agent"
   - Explain: "Router detects explicit escalation request"
   - Show conversation status changes to "escalated"
   - Show agent_type: "escalation" in response

4. **Show Intent Classification**
   - Send various messages:
     - "The website is broken" → technical_support
     - "I'm unhappy with my purchase" → complaint (auto-escalates)
     - "Hello" → general
   - Show intent badges for each message

**Key Talking Points:**
- "Multi-agent architecture enables specialization and better routing"
- "Router → Knowledge/Escalation flow is similar to enterprise chatbot platforms"
- "Intent classification uses few-shot learning with embeddings"

---

## Part 3: Evaluation Metrics (3 min)

### Setup
1. Open Analytics dashboard
2. Show evaluation metrics section

### Demo Steps
1. **Show CSAT Collection**
   - Resolve a conversation
   - Show CSAT survey modal
   - Submit CSAT score (e.g., 4/5)
   - Show CSAT appears in analytics

2. **Show BLEU & Semantic Similarity**
   - Go to Agent Dashboard
   - Provide feedback on an AI response with correction
   - Explain: "System calculates BLEU score and semantic similarity"
   - Show evaluation metrics endpoint: `/api/analytics/evaluation`
   - Display metrics: avg_bleu_score, avg_semantic_similarity, avg_csat

3. **Show Deflection Trend**
   - Show deflection rate chart
   - Explain: "Deflection rate = % of conversations resolved without escalation"
   - Show trend over time

**Key Talking Points:**
- "BLEU measures response quality, semantic similarity measures retrieval accuracy"
- "CSAT measures customer satisfaction - all three together give complete picture"
- "Deflection trend shows automation effectiveness over time"

---

## Part 4: Self-Improving Feedback Loops (3 min)

### Setup
1. Open Agent Dashboard
2. Have some feedback with corrections ready

### Demo Steps
1. **Show Feedback Collection**
   - Show feedback entries with agent corrections
   - Explain: "Every correction becomes training data"

2. **Show Training Data**
   - Navigate to `/api/feedback/training-data/export`
   - Show JSONL export format
   - Explain: "Ready for model fine-tuning"

3. **Trigger Retraining**
   - Click "Retrain Model" button (or call `/api/feedback/retrain`)
   - Show retraining results:
     - Training data collected
     - Knowledge articles updated
     - Few-shot examples generated
   - Explain: "System automatically re-embeds knowledge articles and updates examples"

4. **Show Improvement**
   - Compare BLEU scores before/after retraining
   - Show: "After retraining with 50 feedback items, BLEU improved from 0.65 to 0.72"

**Key Talking Points:**
- "Closed feedback loop: corrections → retraining → improvement"
- "System learns from every agent interaction"
- "This is how the system self-improves over time"

---

## Part 5: A/B Testing (3 min)

### Setup
1. Open Experiments page (or API endpoint)
2. Have model versions created

### Demo Steps
1. **Create Experiment**
   - Show model versions (e.g., "v1 - old embeddings", "v2 - new embeddings")
   - Create experiment: "Test new embedding model"
   - Set traffic split: 50/50
   - Explain: "50% of conversations use variant A, 50% use variant B"

2. **Show Experiment Comparison**
   - Navigate to experiment comparison endpoint
   - Show metrics comparison:
     - Variant A: CSAT 3.8, Deflection 65%, Confidence 0.72
     - Variant B: CSAT 4.2, Deflection 72%, Confidence 0.78
   - Show winner: "Variant B is significantly better"

3. **Promote Winner**
   - Explain: "Based on statistical significance, we promote variant B to production"
   - Show how to update active model version

**Key Talking Points:**
- "A/B testing allows objective measurement of improvements"
- "We test embedding models, prompts, confidence thresholds"
- "Statistical significance ensures we're making data-driven decisions"

---

## Part 6: System Architecture Overview (2 min)

### Setup
1. Show system architecture diagram (if available)
2. Or walk through code structure

### Demo Steps
1. **Show Agent Flow**
   - User message → Router Agent → Intent classification
   - Router → Knowledge Agent (for FAQ/orders)
   - Router → Escalation Agent (for complaints/low confidence)

2. **Show Data Flow**
   - Conversation → Messages → Feedback → Training Data
   - Training Data → Retraining → Model Updates
   - Model Updates → Better Responses → Higher Metrics

3. **Show Key Components**
   - `rag_service.py` - Vector embeddings
   - `agent_orchestrator.py` - Multi-agent coordination
   - `evaluation_service.py` - Metrics calculation
   - `retraining_service.py` - Feedback processing
   - `experiment_service.py` - A/B testing

**Key Talking Points:**
- "Modular architecture enables easy extension"
- "Each agent is specialized for its task"
- "Feedback loops create continuous improvement"

---

## Closing Summary (1 min)

### Key Highlights
1. **Vector RAG** - Production-grade semantic search
2. **Multi-Agent System** - Router, Knowledge, Escalation agents
3. **Evaluation Framework** - BLEU, semantic similarity, CSAT
4. **Self-Improving Loops** - Automatic retraining from feedback
5. **A/B Testing** - Data-driven model improvement

### Scalability Path
- Current: SQLite + ChromaDB (fast for demo)
- Production: PostgreSQL + pgvector, Redis caching, Celery async jobs
- Vector DB: Pinecone or Weaviate for scale

---

## Troubleshooting

**If embeddings don't work:**
- Explain: "System falls back to keyword search if embeddings unavailable"
- Show fallback logic in `rag_service.py`

**If agents don't route correctly:**
- Show intent classification examples in `router_agent.py`
- Explain: "Few-shot classification uses embedding similarity"

**If metrics are empty:**
- Generate some feedback with corrections
- Trigger retraining to populate metrics

---

## Success Criteria

✅ Can demonstrate semantic search finding articles without exact keywords
✅ Can show multi-agent routing (router → knowledge/escalation)
✅ Can display evaluation metrics (BLEU, CSAT, deflection)
✅ Can trigger retraining and show improvement
✅ Can create and compare A/B test experiments
✅ Can explain architecture and scalability path

