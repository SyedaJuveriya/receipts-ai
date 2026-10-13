# RECEIPTS AI — Persistent Memory for AI Agents

**The AI agent that remembers what you said you'd do, what you decided, and what changed.**

RECEIPTS is a voice-first persistent-memory system designed to help AI agents remember decisions, commitments, and important changes beyond a single conversation. It extracts meaningful information from natural-language input, stores memories, retrieves relevant context through semantic search, and identifies potential follow-ups.

## Problem

AI conversations often contain important decisions and commitments, but these details can become difficult to retrieve when the conversation ends or context changes.

People may forget what they committed to, why they made a decision, or whether a previous plan has changed. Traditional chat history is not always an efficient way to retrieve this information.

RECEIPTS addresses this problem by treating important conversational information as persistent, searchable memory.

## Solution

RECEIPTS converts natural-language input into structured memories and makes them available for future retrieval.

The system focuses on three types of information:

- **Decisions:** Choices, plans, and conclusions.
- **Commitments:** Tasks or actions a person intends to complete.
- **Changes:** Updates that may modify or replace previous decisions.

The Memory Explorer lets users search relevant memories and inspect their stored context. A proactive follow-ups card surfaces potential pending decisions and commitments, helping users revisit what they said they would do.

## Key Features

- **Natural-language memory capture:** Submit information in ordinary language.
- **AI-powered extraction:** Uses Lyzr to extract structured memory candidates.
- **Persistent memory architecture:** Stores memory records using Qdrant for retrieval.
- **Semantic search:** Retrieves relevant memories based on meaning rather than exact keyword matching.
- **Duplicate detection:** Identifies duplicate memory candidates during processing.
- **Decision and commitment tracking:** Distinguishes different memory types and tracks memory status.
- **Proactive follow-ups:** Displays potential follow-ups associated with decisions and commitments.
- **Interactive dashboard:** Provides memory capture, Memory Explorer, system architecture, and agent activity views.
- **Omi integration:** Supports an Omi webhook input path for voice-captured transcripts.

## System Architecture

```text
        Voice / Manual Input
                 |
                 v
          Omi / React UI
                 |
                 v
          FastAPI Backend
                 |
                 v
        Lyzr Extraction Agent
                 |
                 v
       Memory Processing Layer
       - Structured extraction
       - Duplicate detection
       - Decision and commitment handling
                 |
                 v
             Qdrant
       Memory Storage and Search
                 |
                 v
        Memory Retrieval
                 |
                 v
       React Memory Explorer
       + Proactive Follow-ups
```

## Technology Stack

| Component | Technology |
|---|---|
| Frontend | React, Vite |
| Backend | Python, FastAPI |
| AI orchestration and extraction | Lyzr |
| Vector memory and semantic retrieval | Qdrant |
| Voice capture integration | Omi webhook |
| Frontend deployment | Vercel |
| Backend deployment | Render |

## How It Works

1. **Capture:** The user submits a natural-language statement through the dashboard or a supported voice-input path.
2. **Extract:** The backend sends the input to the Lyzr extraction agent.
3. **Process:** The application processes the extracted memory candidates and checks for duplicates or relevant changes.
4. **Store:** Memory records are saved in Qdrant.
5. **Retrieve:** The application uses semantic search to find relevant stored memories.
6. **Follow up:** The Memory Explorer displays potential follow-ups for supported decisions and commitments.

## Live Demo

- **Application:** https://receipts-ai-six.vercel.app
- **Backend health check:** https://receipts-ai.onrender.com/health
- **GitHub repository:** https://github.com/SyedaJuveriya/receipts-ai

## Local Setup

### Prerequisites

- Python
- Node.js and npm
- A Qdrant instance
- Lyzr API credentials
- Omi credentials or webhook configuration if testing voice capture

### 1. Clone the repository

```bash
git clone https://github.com/SyedaJuveriya/receipts-ai.git
cd receipts-ai
```

### 2. Configure the backend

Create and activate a virtual environment inside the backend directory.

```bash
cd backend
python -m venv .venv
```

On Windows PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
```

Install the backend dependencies using the dependency files provided in the repository.

Create a `.env` file using the project's environment-variable configuration. Supply your own Lyzr API key, agent ID, Qdrant configuration, and any other required settings.

**Never commit API keys, credentials, or your `.env` file.**

Start the backend using the project's configured FastAPI entry point. For the standard local setup, this may be:

```bash
uvicorn app.main:app --reload
```

### 3. Configure the frontend

Open a separate terminal:

```bash
cd frontend
npm install
```

Create a local `.env` file with the backend URL:

```env
VITE_API_URL=http://127.0.0.1:8000
```

Start the development server:

```bash
npm run dev
```

Open the local URL printed by Vite in your terminal.

*Note: Exact environment-variable names and dependency-installation commands should match the configuration files in the repository.*

## Example Use Case

Input:

> I will submit my hackathon project tonight.

RECEIPTS can extract this statement as a commitment and make it available through memory retrieval and the follow-ups interface.

Other example inputs include:

- "I decided to revise DSA on Sunday morning."
- "I decided to study Python on Friday at home."

These demonstrate how ordinary statements can be represented as searchable decisions or commitments.

## Current Limitations

- **Storage persistence:** The current deployment may lose stored memory data when the backend is redeployed, depending on the Qdrant storage configuration. Persistent storage across redeployments is not guaranteed.
- **Follow-up accuracy:** Follow-ups are generated from stored memory information and may occasionally surface an unexpected or irrelevant item.
- **Voice capture:** Voice input depends on the configured Omi integration and webhook setup.
- **Reminder delivery:** The follow-ups card displays potential pending items; it should not be interpreted as a fully implemented scheduled notification system.

## Future Improvements

- Cloud-backed persistent vector storage.
- Improved isolation of memory across users and sessions.
- More reliable follow-up relevance and evaluation.
- Scheduled reminders and deadline-aware notifications.
- Better handling of superseded decisions and completed commitments.
- Expanded automated tests and monitoring.
- Improved support for long-term conversational context.

## Why RECEIPTS?

RECEIPTS is built around a simple idea: an AI agent should not only respond to what a user says now, but also help preserve what matters from previous interactions.

By combining structured memory extraction, semantic retrieval, and proactive follow-ups, RECEIPTS aims to make conversational AI more useful beyond a single conversation.

---

**Built for:** Stop Prompting. Code Solo Agents Hackathon

**Project:** RECEIPTS AI — Persistent Memory for AI Agents

**Built with:** React · FastAPI · Lyzr · Qdrant · Omi
