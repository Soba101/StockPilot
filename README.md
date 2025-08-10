# StockPilot

Inventory + sales analytics with a trustworthy chat interface that turns data into decisions.

## Quick Start

1. **Prerequisites**
   - Node.js 18+
   - Python 3.11+
   - Docker and Docker Compose

2. **Development Setup**
   ```bash
   # Start all services
   docker-compose up -d
   
   # Backend (in separate terminal)
   cd backend
   python -m venv venv
   source venv/bin/activate  # or `venv\Scripts\activate` on Windows
   pip install -r requirements.txt
   uvicorn app.main:app --reload --port 8000
   
   # Frontend (in separate terminal)
   cd frontend
   npm install
   npm run dev
   ```

3. **Access the app**
   - Frontend: http://localhost:3000
   - Backend API: http://localhost:8000
   - API docs: http://localhost:8000/docs

## Architecture

- **Backend**: FastAPI (Python) + PostgreSQL + dbt
- **Frontend**: Next.js (TypeScript) + Tailwind CSS
- **Chat**: OpenAI GPT-4 integration with guardrails
- **Infrastructure**: Docker for local dev, Railway for production

## Project Structure

```
├── backend/           # FastAPI application
│   ├── app/          # Main application code
│   ├── dbt/          # Data transformation models
│   └── requirements.txt
├── frontend/         # Next.js application
│   ├── src/          # React components and pages
│   └── package.json
├── docker-compose.yml # Local development environment
└── README.md
```