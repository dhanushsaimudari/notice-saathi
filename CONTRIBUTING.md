# Contributing to NoticeSaathi

Thank you for contributing to NoticeSaathi.

NoticeSaathi is an evidence-first, voice-enabled notice understanding assistant designed for older adults and citizens with accessibility needs. Our core promise is **Proof Before Explanation: Never invent what the evidence does not support.**

---

## 1. Development Principles

1. **Proof Before Explanation**: Never invent legal instructions, deadlines, amounts, or waiver statuses. Every statement presented to the user must be grounded in verified text blocks.
2. **Accessible by Default**: Maintain WCAG 2.2 AA compliance: minimum 48px touch targets, high-contrast support, responsive scaling up to 200%, screen-reader compatibility.
3. **Privacy First**: Respect user consent. Document processing is private and tenant-isolated. Never send unredacted document images or sensitive personal records to third-party general LLMs.
4. **Defensive Against Hallucinations**: Abstain when information is missing, ambiguous, or contradictory.

---

## 2. Environment Setup

### Prerequisites
- Python 3.12+
- Node.js 20+ and npm

### Local Setup
```bash
# Clone repository
git clone https://github.com/dhanushsaimudari/notice-saathi.git
cd "notice saathi"

# Python environment
python -m venv venv
# Windows:
.\venv\Scripts\activate
# Linux/macOS:
source venv/bin/activate

pip install -r requirements.txt

# Frontend dependencies
cd apps/web
npm install
cd ../..
```

---

## 3. Branching & Git Workflow

- Main branch is `main`.
- Feature and bugfix branches should branch off `main` with descriptive names: `fix/upload-session-sync`, `feat/audio-player-enhancement`.
- Never commit credentials, `.env` files, or binary SQLite databases.
- Always check `git diff --check` and `git status` prior to submitting pull requests.

---

## 4. Running Tests & Linters

All contributions must pass automated tests and static analysis before review:

```bash
# Run backend pytest suite
pytest tests -v

# Run frontend production build
npm --prefix apps/web run build

# Run frontend ESLint
npm --prefix apps/web run lint

# Security audit
npm --prefix apps/web audit
pip check
```

---

## 5. Coding Standards

### Python (Backend)
- Follow PEP 8 and standard FastAPI conventions.
- Explicit type hints on all route handlers and services.
- Always validate statutory rules through `backend/modules/answers/service.py` and `backend/modules/citations/validator.py`.
- Handle external services (STT, TTS, translation) defensively with bounded timeouts and clear fallback metadata.

### TypeScript / Next.js (Frontend)
- Next.js 15 App Router architecture.
- Explicit TypeScript interfaces matching API models in `apps/web/lib/api.ts`.
- Ensure buttons and interactive controls provide visible keyboard focus rings (`focus:ring-4 focus:ring-yellow-400`).
- Maintain accessibility support using `useAccessibility()` hook from `@/lib/accessibility`.

---

## 6. Security & Vulnerability Reporting

If you discover a security vulnerability, do not open a public issue. Please report it privately to the maintainers at `dhanushsai.mudari@gmail.com`.

