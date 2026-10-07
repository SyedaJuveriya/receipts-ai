# RECEIPTS AI - Development Instructions

## Project

Receipts is a voice-first persistent-memory AI agent for commitments,
decisions, and changes.

Required technologies:

- Omi
- Qdrant
- Lyzr
- FastAPI
- React

## Core principle

Reliability > Features

Working MVP > Complexity

Demo Quality > Extra Features

Understandable Code > Clever Code

## Development Rules

1. Never generate the entire application at once.
2. Work one verified milestone at a time.
3. Inspect the existing project before modifying files.
4. Never rewrite working code unnecessarily.
5. Keep dependencies minimal.
6. Never invent APIs, SDK methods, endpoints, or environment variables.
7. Verify current official documentation before integrating Omi, Qdrant, or Lyzr.
8. After every implementation, run the relevant tests.
9. Never mark a feature WORKING unless it has actually been tested.
10. If something fails, diagnose the actual error before changing code.
11. Do not make unrelated changes.
12. Do not add features outside the current milestone.
13. Prefer the simplest reliable implementation.

## Error Handling

If an error occurs:

1. Stop.
2. Read the complete error.
3. Identify the failing component.
4. Determine the likely category:
   - syntax
   - dependency
   - environment
   - configuration
   - API
   - authentication
   - network
   - application logic
5. Make the smallest appropriate fix.
6. Test again.

Do not randomly modify multiple files.

Do not reinstall everything without evidence.

Do not rewrite the project to fix a localized error.

## Frontend

The frontend must NOT be a generic CRUD dashboard.

It should communicate:

- persistent memory
- agent activity
- memory evolution
- contradictions
- commitments
- decisions
- autonomous follow-up

Required UI features:

- polished modern interface
- live agent activity
- memory explorer
- memory timeline
- follow-up section
- interactive system architecture diagram

The architecture diagram must be implemented in code,
not as a static image.

Architecture nodes must support:

- hover
- node highlighting
- connection highlighting
- tooltip/popover explanations

The diagram must reflect the actual implementation.

## Agent Architecture

Target agents:

1. Chief of Staff / Manager
2. Extractor Agent
3. Memory Judge Agent
4. Follow-up Agent

Do not add more agents unless there is a clear reason.

## Memory

Qdrant is the persistent memory layer.

Important memory relationships:

- NEW
- DUPLICATE
- UPDATE
- SUPERSEDES
- CONTRADICTS
- UNRELATED

Important memory states:

- ACTIVE
- COMPLETED
- SUPERSEDED
- CONTRADICTED
- REVIEW_REQUIRED

Persistent memory mistakes are worse than missing memories.

Use confidence thresholds where appropriate.

## Git

Use Git checkpoints after stable milestones.

Never commit secrets.

Never commit `.env`.

## Scope Control

Do NOT add these unless genuinely required:

- Redis
- Kafka
- Kubernetes
- unnecessary microservices
- unnecessary databases
- graph databases
- Gmail integration
- Slack integration
- WhatsApp integration
- Calendar OAuth
- Notion integration
- mobile application

Do not allow optional features to delay the core MVP.

## Coding Workflow

Before each implementation step:

1. State the goal.
2. Identify the files involved.
3. Explain the change briefly.
4. Implement only that step.
5. Run the relevant test.
6. Report the result.
7. Wait before moving to the next milestone.

Never implement multiple major milestones without verification.