# AI Customer Support Backend

FastAPI backend for AI Customer Support Assistant with Human-in-the-Loop capabilities.

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Initialize and seed the database:
```bash
python seed_data.py
```

3. (Optional) Install and run Ollama:
```bash
# Install Ollama from https://ollama.ai
ollama serve
ollama pull llama3.2
```

4. Run the server:
```bash
uvicorn app.main:app --reload
```

Server will run at: http://localhost:8000
API docs available at: http://localhost:8000/docs

## Architecture

### Database Schema
- **conversations**: Customer chat sessions with status tracking
- **messages**: All messages with type classification for HITL workflows
- **knowledge_base**: Articles for RAG implementation
- **feedback**: Agent corrections and ratings for model improvement
- **metrics**: Pre-computed analytics

### Key Endpoints
- `POST /api/conversations` - Create new conversation
- `POST /api/ai/generate` - Generate AI response with confidence score
- `POST /api/messages` - Send message (customer or agent)
- `POST /api/feedback` - Submit agent feedback
- `GET /api/analytics/metrics` - Dashboard metrics

### HITL Workflow
1. Customer sends message
2. AI generates response with confidence score
3. If confidence < 70%, queued for agent review
4. Agent can approve, edit, or escalate
5. Feedback collected for model improvement

## Key Features for Interview Discussion

- **Confidence Scoring**: Based on knowledge base match quality
- **Dual Workflow Support**: Pre-send review and post-send feedback
- **Product Metrics**: Resolution rate, escalation rate, feedback sentiment
- **Feedback Loop**: Structured data collection for RLHF
- **Scalability Notes**: See inline comments about async queues, vector DB migration

