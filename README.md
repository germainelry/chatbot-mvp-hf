# AI Customer Support Assistant MVP

A full-stack AI-powered customer support system with **Human-in-the-Loop (HITL)** capabilities, designed to demonstrate modern agentic AI systems, prompt engineering, and product metrics for AI applications.

## 🎯 Project Goals

Built as a portfolio piece for **Product Manager – AI Agent & Chatbot Intelligence** role, this MVP demonstrates:

- ✅ Agentic AI systems with LLM integration
- ✅ Human-in-the-Loop workflows (pre-send & post-send)
- ✅ Product metrics for AI systems (deflection rate, resolution rate, feedback sentiment)
- ✅ Feedback collection architecture for model improvement (RLHF)
- ✅ Knowledge base integration (simple RAG)
- ✅ Agent supervision dashboard
- ✅ Real-time analytics

## 🏗️ Architecture

```
Backend (FastAPI + SQLite)
├── LLM Service (Ollama + Fallback)
├── Knowledge Base (Simple RAG)
├── Confidence Scoring
└── Feedback Collection

Frontend (React + TypeScript + Tailwind)
├── Customer Chat Interface
├── Agent Supervision Dashboard
├── Analytics Dashboard
└── Knowledge Base Management
```

## 🚀 Quick Start

### Prerequisites
- Python 3.9+
- Node.js 18+
- (Optional) Ollama with Llama 3.2

### Backend Setup

```bash
cd backend

# Install dependencies
pip install -r requirements.txt

# Seed database
python seed_data.py

# Run server
uvicorn app.main:app --reload
```

Backend runs at: http://localhost:8000
API docs: http://localhost:8000/docs

### Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Run dev server
npm run dev
```

Frontend runs at: http://localhost:5173

### (Optional) Ollama Setup

```bash
# Install Ollama from https://ollama.ai

# Start Ollama
ollama serve

# Pull model
ollama pull llama3.2
```

**Note:** The system works without Ollama using intelligent fallback responses based on keyword matching and knowledge base articles.

## 📊 Key Features

### 1. Human-in-the-Loop Workflows

**Pre-Send Review (Primary Workflow):**
- AI generates draft response with confidence score
- Low confidence (<70%) → Auto-queue for agent review
- Agent can: Approve, Edit, or Escalate
- Edits tracked as corrections for model improvement

**Post-Send Feedback:**
- Agent rates AI responses (Helpful/Not Helpful/Needs Improvement)
- Collects corrections and notes
- Builds training dataset for RLHF

### 2. Confidence Scoring

- **High (>80%)**: Green indicator, can auto-send
- **Medium (50-80%)**: Yellow, queue for review
- **Low (<50%)**: Red, requires intervention

Based on knowledge base match quality and keyword relevance.

### 3. Product Metrics Dashboard

Critical metrics for AI system evaluation:

- **Deflection Rate**: % conversations handled without escalation
- **Resolution Rate**: % successfully resolved
- **Escalation Rate**: % requiring human-only intervention
- **Avg Confidence Score**: Model quality indicator
- **Feedback Sentiment**: Agent satisfaction (% helpful)

### 4. Knowledge Base Management

- CRUD interface for articles
- Category-based organization
- Simple keyword matching (production would use vector embeddings)
- Powers AI context generation

## 🎬 Demo Flow

1. **Customer Chat** (`/customer`):
   - Send a question (e.g., "What's your return policy?")
   - Watch AI respond with confidence score
   - Try low-confidence query to see queueing

2. **Agent Dashboard** (`/agent`):
   - View conversation queue
   - Review AI draft response
   - See confidence indicator
   - Edit response if needed
   - Send and provide feedback

3. **Analytics** (`/analytics`):
   - View key metrics
   - Review feedback history
   - See deflection and resolution rates

4. **Knowledge Base** (`/knowledge-base`):
   - Browse seeded articles
   - Add new article
   - See how it improves AI responses

## 🎯 Interview Talking Points

### Product Strategy
- **HITL Paradigm**: Balances automation efficiency with quality control
- **Confidence Thresholds**: Business-configurable based on risk tolerance
- **Feedback Loops**: Critical for RLHF and continuous improvement
- **Metrics Selection**: Focused on operational impact and AI quality

### Technical Architecture
- **Scalability**: Comment notes about async queues, vector DBs, caching
- **Fallback Strategy**: Ensures demo reliability without Ollama
- **Type Safety**: TypeScript + Pydantic for contract enforcement
- **Modular Design**: Easy to swap LLMs, databases, or add features

### AI/ML Considerations
- **Prompt Engineering**: System prompts with knowledge base context
- **Confidence Calibration**: Match-based scoring (would use model logits in production)
- **RAG Implementation**: Simple keyword search (would use embeddings + vector DB)
- **Training Data Collection**: Structured feedback for fine-tuning

### Operational Insights
- **Agent Experience**: Clear indicators, edit capabilities, minimal friction
- **Customer Experience**: Fast responses for high-confidence, quality for low
- **Monitoring**: Real-time metrics for operational decision-making
- **Iteration**: Feedback directly informs knowledge base improvements

## 📁 Project Structure

```
mvp-chatbot/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI app
│   │   ├── database.py          # SQLAlchemy setup
│   │   ├── models.py            # Database models
│   │   ├── routers/             # API endpoints
│   │   │   ├── conversations.py
│   │   │   ├── messages.py
│   │   │   ├── ai.py
│   │   │   ├── feedback.py
│   │   │   ├── knowledge_base.py
│   │   │   └── analytics.py
│   │   └── services/
│   │       └── llm_service.py   # LLM integration
│   ├── seed_data.py             # Database seeding
│   └── requirements.txt
│
├── frontend/
│   ├── src/
│   │   ├── App.tsx
│   │   ├── pages/
│   │   │   ├── CustomerChat.tsx
│   │   │   ├── AgentDashboard.tsx
│   │   │   ├── Analytics.tsx
│   │   │   └── KnowledgeBase.tsx
│   │   └── services/
│   │       └── api.ts           # API client
│   └── package.json
│
└── README.md
```

## 🔑 Key Differentiators

1. ✅ **Dual HITL Workflows**: Both pre-send and post-send paradigms
2. ✅ **Product Metrics**: Aligned with AI product management best practices
3. ✅ **Confidence Scoring**: Data-driven intervention decisions
4. ✅ **Feedback Architecture**: Structured collection for model improvement
5. ✅ **Operational Focus**: Tools for agents, metrics for ops teams
6. ✅ **Scalability Considerations**: Documented throughout codebase

## 🚧 Production Considerations

**To scale this to production:**

1. **Authentication & Authorization**: Add user management, role-based access
2. **Real-time Communication**: WebSockets for live updates
3. **Vector Database**: Pinecone/Weaviate for semantic search
4. **Model Fine-tuning**: Use collected feedback for RLHF
5. **Async Queue**: Celery/RabbitMQ for background processing
6. **Monitoring**: DataDog/Sentry for observability
7. **Database**: PostgreSQL for production scale
8. **Caching**: Redis for response caching
9. **LLM Router**: Multiple model support with cost optimization
10. **A/B Testing**: Experiment framework for model versions

## 📝 License

Built for interview/portfolio purposes. Feel free to reference or adapt.

## 🎓 Learning Outcomes

This project demonstrates proficiency in:
- Full-stack development (FastAPI + React)
- AI/ML integration and prompt engineering
- Product metrics design for AI systems
- Human-in-the-Loop workflow design
- System architecture and scalability planning
- User experience for operational tools

---

**© 2025 Germaine Luah. All rights reserved.**
