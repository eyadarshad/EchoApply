<div align="center">

<br/>

<img src="./logo/logo.png" alt="Echo Apply Logo" width="120" style="border-radius: 20px; box-shadow: 0 8px 30px rgba(16, 185, 129, 0.25);" />

# Echo Apply
### *The Autonomous AI Career Copilot & Job Application Operating System*

<p align="center">
  <b>Transform your job search with deep-context resume tailoring, dynamic cover letters, AI mock interviews, and zero-reflow layout physics.</b>
</p>

[![Next.js](https://img.shields.io/badge/Next.js_14-black?style=for-the-badge&logo=next.js&logoColor=white)](https://nextjs.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![Python](https://img.shields.io/badge/Python_3.13-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org/)
[![TypeScript](https://img.shields.io/badge/TypeScript-3178C6?style=for-the-badge&logo=typescript&logoColor=white)](https://www.typescriptlang.org/)
[![TailwindCSS](https://img.shields.io/badge/Tailwind_CSS-38B2AC?style=for-the-badge&logo=tailwind-css&logoColor=white)](https://tailwindcss.com/)
[![Supabase](https://img.shields.io/badge/Supabase-3ECF8E?style=for-the-badge&logo=supabase&logoColor=white)](https://supabase.com/)
[![Google Gemini](https://img.shields.io/badge/Gemini_2.5_Flash-4285F4?style=for-the-badge&logo=google&logoColor=white)](https://deepmind.google/technologies/gemini/)

<br/>

[Explore Live Demo](https://echo-apply.vercel.app) • [System Architecture](#system-architecture) • [Features](#key-capabilities) • [Quickstart](#getting-started) • [Deployment](#production-deployment)

<br/>

---

</div>

<br/>

## Showcase

<div align="center">

### Interactive Landing Page & Pretext Serpent
<img src="https://github.com/user-attachments/assets/96fb008c-0e98-4a38-a78e-d32dafb1a3fd" alt="Echo Apply Hero Preview" width="880" style="border-radius: 12px; border: 1px solid #1e293b;" />

<p align="center"><i>Sub-pixel kinetic typography and real-time cursor physics powered by the <code>@chenglou/pretext</code> engine.</i></p>

</div>

<br/>

<div align="center">

| Truthfulness-Gated Resume Tailoring | Dynamic Cover Letter Studio |
| :---: | :---: |
| <img src="https://github.com/user-attachments/assets/6784ea57-87b9-46ff-a4d9-25d6056910c8" width="430" style="border-radius: 10px; border: 1px solid #1e293b;" /> | <img src="https://github.com/user-attachments/assets/fd064a81-1281-49ba-94f4-d34aacd7015a" width="430" style="border-radius: 10px; border: 1px solid #1e293b;" /> |
| *Multi-stage pipeline rewriting with strict zero-hallucination verification.* | *Instant role-targeted cover letters with automatic fallback resilience.* |

<br/>

| AI Mock Interview Coach (STAR Method) | Comprehensive CV & Profile Audit |
| :---: | :---: |
| <img src="https://github.com/user-attachments/assets/77936983-560c-4b1a-b416-ebcf03e3fc21" width="430" style="border-radius: 10px; border: 1px solid #1e293b;" /> | <img src="https://github.com/user-attachments/assets/26e79db6-5a8e-40e5-a6a2-44caab7a01d3" width="430" style="border-radius: 10px; border: 1px solid #1e293b;" /> |
| *Role-specific technical questions with dynamic STAR compliance scoring.* | *Detailed rubric scoring evaluating impact, keywords, and structural clarity.* |

</div>

<br/>

---

## Key Capabilities

### 1. Truthfulness-Gated Resume Tailoring
- **4-Stage LLM Pipeline**: Gap Analysis &rarr; Strategic Impact Scoring &rarr; Metric-Dense STAR Rewriting &rarr; Strict Truthfulness Gate.
- **Zero-Fabrication Guarantee**: Automatically rejects claims or technologies not grounded in the candidate's verified profile.
- **ATS Compliant Export**: Generates clean, ATS-parsed PDFs and formatted DOCX files.

### 2. Resilient Cover Letter Studio
- Produces customized 4-paragraph cover letters tailored to target job descriptions in seconds.
- **Multi-Tier Model Fallback**: Google Gemini 2.5 Flash &rarr; Groq LLaMA 3.3 70B &rarr; OpenRouter &rarr; Smart Heuristic Generator (100% uptime guarantee).
- Quick role presets (*Full-Stack*, *Frontend*, *Backend*) with live PDF resume intake.

### 3. AI Mock Interview Practice & STAR Coach
- Generates 5 challenging behavioral and system design questions mapped to the candidate's resume and target JD.
- **Dynamic 0–100 Scoring**: Evaluates Situation, Task, Action, Result completeness, technical depth, and communication clarity.
- 1-click sample answer auto-fillers for immediate testing.

### 4. Comprehensive Profile & Resume Audit Engine
- Evaluates resumes across 5 critical dimensions: Impact Metrics, ATS Keyword Density, Structural Format, Brevity, and Role Alignment.
- Provides actionable, line-by-line recommendations and roadmap milestones.

### 5. Multi-Board Job Crawler & Semantic Matcher
- Aggregates live listings from **RemoteOK**, **Himalayas**, **Jobicy**, **Reed**, and **Adzuna**.
- Computes 0–100% semantic alignment scores based on skills overlap and experience hierarchy.

### 6. Pretext Arithmetic Layout Engine
- Sub-pixel kinetic typography animation powered by Cheng Lou's `@chenglou/pretext`.
- Eliminates browser layout thrashing (`getBoundingClientRect`) by caching document spatial coordinates for fluid 60–120 FPS performance.

---

## System Architecture

```
                               ┌────────────────────────────────┐
                               │       Next.js 14 Frontend      │
                               │   (TypeScript, TailwindCSS,    │
                               │    Pretext Kinematics Engine)  │
                               └───────────────┬────────────────┘
                                               │ HTTPS / REST
                               ┌───────────────▼────────────────┐
                               │       FastAPI Backend API      │
                               │  (Python 3.13, Async Workers,  │
                               │   Rate Limiters, Auth Shields) │
                               └───────┬───────────────┬────────┘
                                       │               │
                     ┌─────────────────▼─────┐   ┌─────▼──────────────────┐
                     │ Multi-LLM Orchestrator│   │   Supabase Postgres    │
                     │  - Gemini 2.5 Flash   │   │  - Auth & JWT Security │
                     │  - Groq LLaMA 3.3 70B │   │  - Row-Level Security  │
                     │  - OpenRouter Fallback│   │  - Profile Store       │
                     └───────────────────────┘   └────────────────────────┘
```

<br/>

| Layer | Technologies |
| :--- | :--- |
| **Frontend** | Next.js 14 (App Router), React 18, TypeScript, TailwindCSS, Lucide Icons, Canvas API |
| **Backend** | FastAPI, Python 3.13, Pydantic v2, Uvicorn, Asyncio, Pytest |
| **Database & Auth** | Supabase (PostgreSQL), Row-Level Security (RLS), Supabase Auth JWT |
| **AI & Inference** | Google Gemini 2.5 Flash, Groq (LLaMA 3.3 70B), OpenRouter |
| **Automation** | Playwright Chromium Headless Agent, BeautifulSoup4, WeasyPrint |
| **Performance** | `@chenglou/pretext` Arithmetic Engine, Spatial Cache Optimizer |

---

## Getting Started

### Prerequisites
- **Node.js**: `v18.17+` or `v20+`
- **Python**: `3.11+` (Python 3.13 recommended)
- **Supabase Account** & **Google AI Studio API Key**

---

### 1. Clone the Repository
```bash
git clone https://github.com/eyadarshad/EchoApply.git
cd EchoApply
```

---

### 2. Backend Setup
```bash
cd backend

# Create virtual environment
python -m venv .venv

# Activate environment
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Configure environment variables
cp ../.env.example .env
# Open .env and add your SUPABASE_URL, GEMINI_API_KEY, and DATABASE_URL

# Start FastAPI server
uvicorn app.main:app --reload --port 8000
```

---

### 3. Frontend Setup
```bash
cd ../frontend

# Install dependencies
npm install

# Start Next.js development server
npm run dev
```

Open [http://localhost:3000](http://localhost:3000) in your browser.

---

## Testing & Quality Assurance

```bash
# Run Backend Pytest Suite
cd backend
pytest tests/test_production_upgrade.py

# Run Frontend Vitest & TypeScript Verification
cd ../frontend
npx vitest run
npx tsc --noEmit
```

---

## Production Deployment

<details>
<summary><b>Deploying Backend (Render / Railway)</b></summary>
<br/>

1. Connect your GitHub repository to [Render](https://render.com).
2. Set **Root Directory** to `backend`.
3. Set **Build Command** to `pip install -r requirements.txt`.
4. Set **Start Command** to `uvicorn app.main:app --host 0.0.0.0 --port $PORT`.
5. Add your environment variables from `backend/.env`.
</details>

<details>
<summary><b>Deploying Frontend (Vercel)</b></summary>
<br/>

1. Import your GitHub repository into [Vercel](https://vercel.com).
2. Set **Root Directory** to `frontend`.
3. Add the following environment variables:
   - `NEXT_PUBLIC_BACKEND_URL`: Your live Render backend URL
   - `NEXT_PUBLIC_SUPABASE_URL`: Your Supabase Project URL
   - `NEXT_PUBLIC_SUPABASE_ANON_KEY`: Your Supabase Anon Key
4. Click **Deploy**.
</details>

---

## Security & Privacy
- **Row-Level Security (RLS)**: Enforced database-level multi-tenancy ensures users can only access their own records.
- **Zero-Storage Secrets**: Sensitive API keys and credentials reside strictly in backend memory.
- **Client Sanitization**: Production builds contain zero private master keys.

---

## License
Distributed under the **MIT License**. See [LICENSE](LICENSE) for more information.

<br/>

<div align="center">

Crafted with care by <a href="https://github.com/eyadarshad"><b>Eyad Arshad</b></a>

</div>
