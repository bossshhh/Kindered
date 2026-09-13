# Kindred Frontend

React + Vite frontend for the Behavioral Digital Twin capstone.

## UX

The elderly experience prioritizes a calm editorial interface:

- Meet Kindred
- Share a thought
- Start talking
- Large readable composer
- Browser microphone input
- Browser speech synthesis
- Voice selection when supported by the browser
- Context tab with role-appropriate information

Relative and doctor demo roles expose additional management and analysis surfaces.

## API

The frontend defaults to:

`http://localhost:8000/api`

Override with:

```env
VITE_API_URL=http://localhost:8000/api
```

## Development

```bash
npm install
npm run dev
```

Production build:

```bash
npm run build
```
