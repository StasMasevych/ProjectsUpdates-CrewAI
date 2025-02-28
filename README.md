# My CrewAI Project

This project uses CrewAI to create and manage AI agents for automated tasks.

## Setup

1. Create a virtual environment:

   ```bash
   # For backend (Python)
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

2. Install dependencies:

   ```bash
   # Backend dependencies
   cd backend
   pip install -r requirements.txt
   # Or using Poetry
   poetry install

   # Frontend dependencies
   cd frontend
   npm install
   ```

3. Set up environment variables:
   Create a `.env` file in the backend directory with:
   ```
   SERPER_API_KEY=your_serper_api_key
   OPENAI_API_KEY=your_openai_api_key
   ```

## Running the Application

### Backend

1. Navigate to backend directory:

   ```bash
   cd backend
   ```

2. Run with Python:

   ```bash
   python -m src.main
   ```

   Or run with uvicorn directly:

   ```bash
   uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload
   ```

### Frontend

1. Navigate to frontend directory:

   ```bash
   cd frontend
   ```

2. Start the development server:
   ```bash
   npm run dev
   ```

## API Endpoints

- `GET /api/health` - Health check endpoint
- `GET /api/projects?region=REGION&technology=TECHNOLOGY` - Get projects for a specific region and technology
- `GET /api/progress` - Server-sent events for progress updates

## Project Structure

- `backend/` - FastAPI backend application
- `frontend/` - Next.js frontend application
