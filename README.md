# DocCentric - AI-Powered Patient Management System

An AI-powered healthcare documentation system that processes audio recordings of Bangla doctor-patient conversations, automatically extracts patient information, and maintains structured medical records with voice-based patient identification.

## Overview

**Purpose:** Parse audio files containing Bangla conversations between doctors and patients. The system:
- Transcribes and analyzes the conversation
- Extracts patient demographics (name, age, gender, phone)
- Identifies medical information (symptoms, diagnosis, prescription, tests)
- Saves patient's voice for future identification
- Stores all data in PostgreSQL database

## Architecture

```
Audio File (Bangla conversation)
         │
         ▼
┌─────────────────────┐
│  Audio Processor    │
│  - Diarization      │◄── pyannote/speaker-diarization-3.1
│  - Transcription    │◄── whisper (base model)
│  - Voice Embeddings │◄── speechbrain/spkrec-ecapa-voxceleb
└─────────────────────┘
         │
         ▼
┌─────────────────────┐
│   LLM Service       │◄── phi4-mini (Ollama)
│  - Extract patient  │
│  - Summarize visit  │
└─────────────────────┘
         │
         ▼
┌─────────────────────┐
│  Voice Matching      │
│  - Compare embeddings│
│  - Identify patient │
└─────────────────────┘
         │
         ▼
┌─────────────────────┐
│   PostgreSQL DB      │
│  - patients         │
│  - visits           │
│  - voice_embeddings │
│  - audio_records    │
└─────────────────────┘
```

## Technology Stack

| Component | Technology |
|-----------|------------|
| API Framework | FastAPI |
| Database | PostgreSQL |
| ORM | SQLAlchemy |
| Audio Diarization | pyannote.audio 3.1 |
| Transcription | OpenAI Whisper |
| Speaker Embedding | SpeechBrain ECAPA-VoxCeleb |
| LLM | Ollama (phi4-mini) |
| Language | Bengali (Bangla) + English |

## Database Schema

### patients
| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER | Primary key |
| name | VARCHAR(255) | Patient name |
| age | INTEGER | Patient age |
| gender | VARCHAR(20) | Gender |
| phone | VARCHAR(20) | Unique phone number |
| email | VARCHAR(255) | Email address |
| address | TEXT | Home address |
| blood_type | VARCHAR(5) | Blood type |
| allergies | TEXT | Known allergies |
| emergency_contact | VARCHAR(255) | Emergency contact |
| created_at | TIMESTAMP | Record creation time |

### visits
| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER | Primary key |
| patient_id | INTEGER | FK to patients |
| doctor_id | VARCHAR(100) | Doctor identifier |
| chief_complaint | TEXT | Main health issue |
| symptoms | TEXT | Symptoms described |
| diagnosis | TEXT | Diagnosis given |
| tests | TEXT | Tests ordered |
| prescription | TEXT | Medications prescribed |
| suggestions | TEXT | Medical advice |
| notes | TEXT | Additional notes |
| visit_type | VARCHAR(50) | "initial" or "follow-up" |
| transcript | TEXT | Full conversation transcript |
| summary | TEXT | AI-generated visit summary |

### voice_embeddings
| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER | Primary key |
| patient_id | INTEGER | FK to patients |
| embedding_vector | TEXT | JSON-serialized voice embedding |
| embedding_version | VARCHAR(20) | Model version |
| created_at | TIMESTAMP | Record creation time |

### audio_records
| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER | Primary key |
| visit_id | INTEGER | FK to visits |
| file_path | VARCHAR(500) | Path to audio file |
| file_name | VARCHAR(255) | Original filename |
| duration | FLOAT | Audio duration in seconds |
| uploaded_at | TIMESTAMP | Upload timestamp |

## API Endpoints

### Health
- `GET /` - Root endpoint
- `GET /health` - Health check

### Patients
- `POST /api/patients` - Create patient
- `GET /api/patients` - List all patients
- `GET /api/patients/{id}` - Get patient by ID
- `PUT /api/patients/{id}` - Update patient
- `DELETE /api/patients/{id}` - Delete patient

### Visits
- `POST /api/visits` - Create visit
- `GET /api/visits/{id}` - Get visit by ID
- `GET /api/patients/{id}/visits` - Get patient's visits

### Audio Processing
- `POST /api/upload-audio` - Upload and process audio conversation

## Usage

### 1. Setup Environment

```bash
# Activate virtual environment
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure Environment

Edit `.env` file:
```env
DATABASE_URL=postgresql://postgres:postgres@localhost:5433/doccentric
HUGGING_FACE_TOKEN=your_huggingface_token
OLLAMA_MODEL=phi4-mini
```

### 3. Start Services

```bash
# Start PostgreSQL (if using local)
pg_ctl -D /var/lib/postgresql/16/main start

# Start Ollama (in background)
ollama serve

# Start API server
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### 4. Test the API

```bash
# Health check
curl http://localhost:8000/health

# Upload audio file
curl -X POST "http://localhost:8000/api/upload-audio" \
  -F "doctor_id=DR001" \
  -F "audio_file=@conversation.wav"
```

### 5. Run Tests

```bash
python -m pytest tests/ -v
```

## Audio Processing Flow

1. **Audio Upload**: Doctor uploads audio file with `doctor_id`
2. **Diarization**: pyannote identifies different speakers (patient vs doctor)
3. **Transcription**: Whisper transcribes the Bangla audio to text
4. **Voice Embedding**: SpeechBrain extracts voice embeddings from patient's segments
5. **Patient Matching**: System checks if patient's voice matches an existing patient
   - If match found → existing patient record
   - If no match → create new patient
6. **Info Extraction**: LLM extracts structured data from transcript
7. **Visit Creation**: Create visit record with transcript and summary
8. **Audio Storage**: Save audio file reference

## Testing Strategy

| Test Type | Location | Purpose |
|-----------|----------|---------|
| API Tests | `tests/test_api.py` | Verify endpoints work correctly |
| Service Tests | `tests/test_services.py` | Test LLM and voice matching logic |
| Audio Flow Tests | `tests/test_audio_flow.py` | Test audio upload pipeline |
| HTTP Client | `test_main.http` | Manual API testing with examples |

## Project Structure

```
doccentric/
├── app/
│   ├── api/
│   │   ├── patients.py      # Patient CRUD endpoints
│   │   └── audio.py        # Audio upload endpoint
│   ├── core/
│   │   └── database.py     # SQLAlchemy setup
│   ├── models/
│   │   ├── models.py       # SQLAlchemy models
│   │   └── schemas.py      # Pydantic schemas
│   └── services/
│       ├── audio_processor.py  # Audio processing (diarization, transcription)
│       ├── llm_service.py      # Ollama LLM integration
│       └── voice_matching.py  # Voice embedding matching
├── tests/
│   ├── conftest.py         # Test fixtures
│   ├── test_api.py         # API tests
│   ├── test_services.py    # Service tests
│   └── test_audio_flow.py  # Audio flow tests
├── audio_files/            # Uploaded audio storage
├── main.py                 # FastAPI application entry
├── .env                    # Environment variables
└── requirements.txt        # Python dependencies
```

## Requirements

- Python 3.10+
- PostgreSQL 12+
- Ollama (for phi4-mini model)
- HuggingFace account (for pyannote access)
- ffmpeg (for audio processing)
