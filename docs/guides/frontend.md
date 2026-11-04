# Synapse-CRS operator console

The React console is an investigation operating environment. It does not add API routes and it does not execute host actions.

## Commands

Frontend:

```bash
cd frontend
npm ci
npm run dev
```

Open `http://127.0.0.1:5173`. Default session is **DEMO MODE** (synthetic lab records). Connect a live bearer token at `/session`.

Production build:

```bash
cd frontend
npm run build
npm test
```

Backend (separate process, `.env` required):

```bash
make api
```

`VITE_API_BASE_URL` defaults to `http://127.0.0.1:8000`. CORS must include the Vite origin.

## Demonstration path

1. Command Centre  
2. Telemetry Operations  
3. Evidence Lab storyline  
4. Investigation Studio  
5. Threat Graph  
6. Reasoning Engine  
7. Hypothesis Arena  
8. Defence Lab (SAT ≠ real-world safety)  
9. Research Observatory (independent validation incomplete)

## Honesty rules

- Demo records are labelled. They are not enrolled telemetry.
- There is no list-telemetry HTTP endpoint; supporting events come from findings.
- Case ACTION does not run a mitigation.
- Research pages copy repository conclusions, including fail-closed dataset status.
