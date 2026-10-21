# SupportFlow frontend

A React/Vite helpdesk dashboard. The root README covers backend/Ollama setup;
`../docs/code-guide.md` explains the source files for beginners.

| Screen | Source | URL |
|---|---|---|
| Ticket inbox | `src/pages/TicketInboxPage.jsx` | `/tickets` (also the landing page) |
| New ticket | `src/pages/NewTicketPage.jsx` | `/triage` |
| Ticket details | `src/pages/TicketDetailsPage.jsx` | `/tickets/:ticketId` |
| Insights | `src/pages/InsightsPage.jsx` | `/analytics` |

`App.jsx` connects the screens. `components/` contains visible UI pieces;
`services/api.js` handles API requests and the session credential. `styles/index.css`
loads the workspace, page and shared responsive styles in their required order.

```powershell
npm install
npm run dev
npm run build
npm run lint
```

The API defaults to `http://127.0.0.1:8000`. Override `VITE_API_URL` in a local
`.env` if needed and restart Vite. Never put credentials in frontend environment
variables; use the header's API access menu. Environment files are not committed.

`public/support-corgi.png` is the sidebar mascot and browser favicon.
