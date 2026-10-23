<a id="readme-top"></a>

<div align="center">

# 🌿 Kindred

### A calm, voice-first AI companion for older adults and the people who care for them

<p>
  <img src="https://img.shields.io/badge/Python-3.10%2B-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python">
  <img src="https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white" alt="FastAPI">
  <img src="https://img.shields.io/badge/LangGraph-1C3C3C?style=for-the-badge&logo=langchain&logoColor=white" alt="LangGraph">
  <img src="https://img.shields.io/badge/scikit_learn-F7931E?style=for-the-badge&logo=scikitlearn&logoColor=white" alt="scikit-learn">
  <br>
  <img src="https://img.shields.io/badge/React-20232A?style=for-the-badge&logo=react&logoColor=61DAFB" alt="React">
  <img src="https://img.shields.io/badge/Vite-646CFF?style=for-the-badge&logo=vite&logoColor=white" alt="Vite">
  <img src="https://img.shields.io/badge/Tailwind_CSS-06B6D4?style=for-the-badge&logo=tailwindcss&logoColor=white" alt="Tailwind CSS">
  <img src="https://img.shields.io/badge/SQLite-003B57?style=for-the-badge&logo=sqlite&logoColor=white" alt="SQLite">
  <img src="https://img.shields.io/badge/Groq-F55036?style=for-the-badge&logoColor=white" alt="Groq">
</p>

<p>
  <a href="#-features"><b>Features</b></a> ·
  <a href="#-architecture"><b>Architecture</b></a> ·
  <a href="#-getting-started"><b>Getting Started</b></a> ·
  <a href="#-api-reference"><b>API</b></a> ·
  <a href="docs/ML_AND_DATASET_NOTES.md"><b>ML Notes</b></a>
</p>

</div>

<br>

> [!NOTE]
> Kindred is a **grounded conversational companion prototype** built as a capstone MVP. It is not a clinical digital twin, not a medical device, and it does not diagnose anything. See [Responsible AI](#-responsible-ai) for the full framing.

<br>

## 📖 Table of Contents

<details open>
<summary>Click to expand</summary>

1. [About the Project](#-about-the-project)
2. [Features](#-features)
3. [Architecture](#-architecture)
4. [Machine Learning](#-machine-learning)
5. [Tech Stack](#-tech-stack)
6. [Getting Started](#-getting-started)
7. [Configuration](#-configuration)
8. [Usage](#-usage)
9. [API Reference](#-api-reference)
10. [Project Structure](#-project-structure)
11. [Running Tests](#-running-tests)
12. [Responsible AI](#-responsible-ai)
13. [Roadmap](#-roadmap)
14. [Author](#-author)

</details>

<br>

## 💡 About the Project

Loneliness, memory loss and daily routines are hard for many older adults, and the relatives who support them can't always be there. **Kindred** is a gentle companion that an older person can simply *talk* to. It remembers who they are, knows about their family, helps with reminders and, most importantly, knows when to step back and get a human involved.

Every message passes through a **deterministic safety gate** and a **supervised intent router** before any language model is allowed to respond. Emergencies skip the LLM entirely. Health questions are answered conservatively and always deferred to people, not invented by a model.

The project ships as a single repository with a **FastAPI** backend and a **React + Vite** frontend. It runs fully offline in demo mode, or plugs into **Groq** for live LLM responses.

<p align="right">(<a href="#readme-top">back to top</a>)</p>

## ✨ Features

<table>
<tr>
<td width="50%" valign="top">

### 👵 For the older adult
* Calm, editorial landing page with large readable type
* Three-step journey: **Meet Kindred**, **Share a thought**, **Start talking**
* Seamless handoff from the landing message into the conversation
* Speak with the microphone, listen to spoken replies
* Choose a preferred voice and replay any answer
* Persistent conversation history

</td>
<td width="50%" valign="top">

### 👨‍👩‍👧 For relatives and doctors
* Create, edit and delete patient profiles
* Manage relative personas and care notes
* Context view grounded in the stored profile
* Real conversation analytics read from SQLite, no fake numbers
* Suggestions surfaced from conversations
* Demo role switch: elderly, relative or doctor

</td>
</tr>
<tr>
<td width="50%" valign="top">

### 🧠 Intelligence
* LangGraph `StateGraph` orchestration
* TF-IDF + Logistic Regression intent router across 9 care intents
* Policy packs per intent (emergency, fall, health, reminder, memory and more)
* Groq LLM with a local demo and fallback mode

</td>
<td width="50%" valign="top">

### 🛡️ Safety
* Deterministic emergency gate that runs before generation
* Critical risk bypasses the LLM completely
* Health-sensitive generation policy that never prescribes or diagnoses
* Identity guardrail so the AI never claims to *be* a real relative
* Response validation before anything reaches the user

</td>
</tr>
</table>

<p align="right">(<a href="#readme-top">back to top</a>)</p>

## 🏗️ Architecture

Every user turn flows through the same pipeline:

```text
                         User message (text or voice)
                                      │
                                      ▼
                       ┌──────────────────────────────┐
                       │   Deterministic safety gate  │
                       └──────────────┬───────────────┘
                     critical risk    │    otherwise
               ┌──────────────────────┴──────────────────────┐
               ▼                                             ▼
   ┌───────────────────────┐                   ┌───────────────────────────┐
   │   Emergency bypass    │                   │  Intent classifier (ML)   │
   │   (no LLM involved)   │                   └─────────────┬─────────────┘
   └───────────┬───────────┘                                 ▼
               │                               ┌───────────────────────────┐
               │                               │  Policy pack for intent   │
               │                               │  emergency · fall · health│
               │                               │  reminder · emotion · ... │
               │                               └─────────────┬─────────────┘
               │                                             ▼
               │                               ┌───────────────────────────┐
               │                               │  Build context: patient,  │
               │                               │  relatives, care notes    │
               │                               └─────────────┬─────────────┘
               │                                             ▼
               │                               ┌───────────────────────────┐
               │                               │ Generate: Groq LLM or     │
               │                               │ local demo / fallback     │
               │                               └─────────────┬─────────────┘
               │                                             ▼
               │                               ┌───────────────────────────┐
               │                               │ Validation + identity     │
               │                               │ guardrail                 │
               │                               └─────────────┬─────────────┘
               └──────────────────────┬──────────────────────┘
                                      ▼
                       ┌──────────────────────────────┐
                       │  Speech synthesis + SQLite   │
                       │  conversation history        │
                       └──────────────┬───────────────┘
                                      ▼
                          Text + spoken reply in the UI
```

<p align="right">(<a href="#readme-top">back to top</a>)</p>

## 🤖 Machine Learning

Kindred uses a deliberately **transparent, auditable** model rather than an opaque network. Short elderly utterances are sparse and lexical, so a linear model performs well and its coefficients can be inspected and defended.

| | |
| :- | :- |
| **Model** | TF-IDF (1 and 2 grams) + class-balanced Logistic Regression |
| **Classes** | `social`, `emotional_support`, `reminder`, `health`, `emergency`, `fall_safety`, `memory`, `relative_request`, `orientation` |
| **Corpus** | 867 rows unified from 7 source files, every row with provenance |
| **Validation** | 5-fold stratified cross-validation |
| **Accuracy** | 0.741 |
| **Macro F1** | 0.779 |
| **Macro Precision / Recall** | 0.802 / 0.786 |

### How the datasets were unified

The project started from seven files (conversation text, conversation audio, daily reminders, health monitoring, safety monitoring, dementia patient records and the NPHA doctor visits survey). These sources **do not share a person key**, so joining them row by row would invent relationships between people who never existed together.

Instead, Kindred uses **task-level unification**: every useful signal is mapped into one caretaker schema (`text, intent, risk_hint, policy, source, unit_of_observation, provenance_id`), while person-level tables are kept as aggregate **population priors**.

> [!IMPORTANT]
> The router chooses a **response policy**. It does not diagnose dementia, depression or any other condition. Read the full write-up in [`docs/ML_AND_DATASET_NOTES.md`](docs/ML_AND_DATASET_NOTES.md).

<p align="right">(<a href="#readme-top">back to top</a>)</p>

## 🧰 Tech Stack

| Layer | Technology |
| :- | :- |
| **Frontend** | React, Vite, Tailwind CSS, Framer Motion, Lucide icons, Web Speech API |
| **Backend** | FastAPI, Uvicorn, Pydantic |
| **Orchestration** | LangGraph |
| **LLM** | Groq (`llama-3.3-70b-versatile` by default), with local demo fallback |
| **ML** | scikit-learn, pandas, NumPy |
| **Database** | SQLite with foreign key enforcement |
| **Speech** | Browser speech recognition and synthesis, macOS `say` for server-side audio |

<p align="right">(<a href="#readme-top">back to top</a>)</p>

## 🚀 Getting Started

### Prerequisites

* **Python** 3.10 or newer
* **Node.js** 18 or newer and npm
* A **Groq API key** (optional, the app works in demo mode without one)
* A Chromium-based browser for the best microphone and speech support

### Installation

**1. Clone the repository**

```bash
git clone https://github.com/bossshhh/Kindered.git
cd Kindered
```

**2. Start the backend**

```bash
./run_backend.sh
```

The script creates a virtual environment in `backend/.venv`, installs the dependencies from `requirements.txt`, copies `.env.example` to `.env` if needed and starts the API with hot reload.

**3. Start the frontend** (in a second terminal)

```bash
./run_frontend.sh
```

**4. Open the app**

| Service | URL |
| :- | :- |
| 🖥️ App | http://localhost:5173/app/ |
| ⚙️ API | http://127.0.0.1:8000 |
| 📚 Swagger docs | http://127.0.0.1:8000/docs |
| ❤️ Health check | http://127.0.0.1:8000/api/health |
| 📊 ML metrics | http://127.0.0.1:8000/api/ml/metrics |

### Production-style build

Build the frontend once and let FastAPI serve it at `/app`:

```bash
cd frontend
npm install
npm run build
cd ..
./run_backend.sh
```

<p align="right">(<a href="#readme-top">back to top</a>)</p>

## ⚙️ Configuration

### Backend (`backend/.env`)

| Variable | Default | Description |
| :- | :- | :- |
| `GROQ_API_KEY` | *(empty)* | Your Groq API key. Leave empty to stay in demo mode. |
| `GROQ_MODEL` | `llama-3.3-70b-versatile` | The Groq model used for generation. |
| `DEMO_MODE` | `true` | Use local demo responses. Set to `false` only after adding a real key. |

To switch on live responses:

```env
GROQ_API_KEY=your_real_key
DEMO_MODE=false
GROQ_MODEL=llama-3.3-70b-versatile
```

### Frontend (`frontend/.env`)

| Variable | Default | Description |
| :- | :- | :- |
| `VITE_API_URL` | *(empty)* | Leave blank for local development. Set it, for example to `http://localhost:8000/api`, when the backend runs on another host. |

> [!WARNING]
> Never commit real keys. The `.gitignore` already excludes `.env` files, keys and local databases.

<p align="right">(<a href="#readme-top">back to top</a>)</p>

## 🎬 Usage

A suggested walkthrough for a demo or presentation:

1. Open **`/app/`** and show the calm Kindred landing experience.
2. Type a sentence into **Share a thought** and press **Begin conversation**.
3. Watch the message arrive in the companion automatically.
4. Explain the pipeline: intent, safety, context, LangGraph, Groq or demo, persistence.
5. Switch to the **relative** or **doctor** demo role.
6. Show the patient and persona configuration.
7. Show the real conversation analytics.
8. Open the **System** page to walk through guardrails and limitations.

<p align="right">(<a href="#readme-top">back to top</a>)</p>

## 🔌 API Reference

All endpoints are prefixed with `/api`. Interactive documentation is available at `/docs` while the backend runs.

<details>
<summary><b>💬 Conversation</b></summary>

| Method | Endpoint | Description |
| :- | :- | :- |
| `POST` | `/chat` | Send a message and receive a grounded reply |
| `GET` | `/patients/{patient_id}/messages` | Get the conversation history |
| `DELETE` | `/patients/{patient_id}/messages` | Clear the conversation history |
| `GET` | `/audio/{filename}` | Stream a generated audio reply |

</details>

<details>
<summary><b>👤 Patients, relatives and notes</b></summary>

| Method | Endpoint | Description |
| :- | :- | :- |
| `GET` | `/patients` | List patients |
| `POST` | `/patients` | Create a patient |
| `GET` | `/patients/{patient_id}` | Get one patient with context |
| `PUT` | `/patients/{patient_id}` | Update a patient |
| `DELETE` | `/patients/{patient_id}` | Delete a patient |
| `POST` | `/relatives` | Create a relative persona |
| `PUT` | `/relatives/{relative_id}` | Update a relative persona |
| `DELETE` | `/relatives/{relative_id}` | Delete a relative persona |
| `POST` | `/notes` | Add a care note |
| `DELETE` | `/notes/{note_id}` | Delete a care note |

</details>

<details>
<summary><b>📊 Analytics and ML</b></summary>

| Method | Endpoint | Description |
| :- | :- | :- |
| `GET` | `/patients/{patient_id}/analytics` | Observed conversation analytics |
| `GET` | `/patients/{patient_id}/suggestions` | Suggestions for a patient |
| `POST` | `/suggestions` | Create a suggestion |
| `GET` | `/ml/metrics` | Cross-validated model metrics |
| `GET` | `/ml/features` | Top features per intent |
| `GET` | `/ml/corpus` | Unified corpus summary |
| `GET` | `/health` | Service health check |

</details>

<p align="right">(<a href="#readme-top">back to top</a>)</p>

## 📁 Project Structure

```text
Kindered/
├── backend/
│   ├── app/
│   │   ├── api/            # FastAPI routes
│   │   ├── db/             # SQLite connection and repository
│   │   ├── graph/          # LangGraph workflow
│   │   ├── ml/             # Corpus builder, training and intent model
│   │   ├── models/         # Pydantic schemas
│   │   ├── services/       # LLM, safety, policy, prompting and TTS
│   │   └── main.py         # App entry point
│   ├── data/unified/       # Unified corpus and population priors
│   ├── tests/              # Unit tests
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── components/ui/  # Chat and UI components
│   │   ├── lib/            # Utilities
│   │   └── main.jsx        # App shell and pages
│   └── package.json
├── docs/
│   └── ML_AND_DATASET_NOTES.md
├── run_backend.sh
└── run_frontend.sh
```

<p align="right">(<a href="#readme-top">back to top</a>)</p>

## 🧪 Running Tests

From the `backend` folder, with the virtual environment active:

```bash
cd backend
source .venv/bin/activate
python -m unittest discover tests
```

The test suite checks that model metrics stay in the expected range, that emergencies are handled deterministically, that the identity guardrail is present in every prompt and that AI disclaimers are sanitized from replies.

<p align="right">(<a href="#readme-top">back to top</a>)</p>

## 🛡️ Responsible AI

A wrong clinical instruction can be fatal, so Kindred is designed around what it should **not** do.

* **No "zero hallucination" claim.** That is not a defensible engineering promise. Instead, Kindred reduces unsupported output with a clear source hierarchy, controlled context, deterministic safety gates, conservative generation settings and a fallback layer.
* **No impersonation.** The AI must never falsely claim to literally be a real or deceased relative.
* **No diagnosis.** The intent model is a small supervised baseline, not a medical classifier, and analytics describe app behavior, not health conditions.
* **No voice cloning.** Speech uses browser and system voices only.
* **Not production-ready.** The role switch is a demo control, not authentication. A real deployment would need authentication, authorization, consent, audit logging, encryption, stronger evaluation and clinical safety review.

<p align="right">(<a href="#readme-top">back to top</a>)</p>

## 🗺️ Roadmap

- [x] Elderly-first conversational UI with voice in and out
- [x] Deterministic safety gate and emergency bypass
- [x] LangGraph policy routing
- [x] Unified multi-source corpus with provenance
- [x] Patient, relative and care note management
- [x] Observed conversation analytics
- [ ] Real authentication and role-based access
- [ ] Encryption at rest and audit logging
- [ ] Larger, clinically reviewed evaluation set
- [ ] Speech recognition and TTS evaluation using the audio dataset
- [ ] Cloud deployment

<p align="right">(<a href="#readme-top">back to top</a>)</p>

## 👤 Author

**Bashar Soufan**

[![GitHub](https://img.shields.io/badge/GitHub-bossshhh-181717?style=for-the-badge&logo=github)](https://github.com/bossshhh)

If you found this project interesting, consider giving it a ⭐ on GitHub.

<p align="right">(<a href="#readme-top">back to top</a>)</p>

<div align="center">
  <sub>Built with care for the people who matter most. 🌿</sub>
</div>
