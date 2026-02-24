# Resume & Cover Letter Generator

An automated system that generates tailored resumes and cover letters using Google's Gemini 3 Pro API. Features a modern React frontend with real-time progress tracking via WebSocket.

## Features

- **AI-Powered Generation**: Uses Gemini 3 Pro to create tailored LaTeX resumes and professional cover letters
- **Configurable AI Parameters**: Temperature, Top-K, Top-P, thinking level, and more - all editable from the UI
- **Page Length Validation**: Automatically ensures resume and cover letter fit on exactly 1 page
- **Editable Prompts**: 4 customizable prompt templates with live editing in the UI
- **Template Substitution**: Automatic replacement of `{{user_information}}` and `{{latex_template}}` placeholders
- **Google Search Grounding**: Optional web search for real-time company research
- **Resume-Only Mode**: Generate just resume or both resume and cover letter
- **Multi-Task Support**: Run multiple generation tasks simultaneously
- **Real-Time Progress**: WebSocket-based live updates showing each step's progress
- **Smart Retry Logic**: LaTeX compilation retries with error feedback to fix issues automatically
- **Company Name Extraction**: Output files automatically named with company name
- **Comprehensive Logging**: File-based logging with separate logs for app, errors, and tasks
- **Response Archiving**: All Gemini API responses saved to timestamped text files
- **Modern UI**: Clean React interface with task management sidebar

## Quick Start (Windows)

### One-Click Installation

1. **Run the installer:**
   ```
   Double-click install.bat
   ```

2. **Configure your API key:**
   - Open `backend\.env` in a text editor
   - Replace `your_gemini_api_key_here` with your actual API key
   - Get your key from: https://aistudio.google.com/

3. **Start the application:**
   ```
   Double-click start.bat
   ```

The application will open automatically in your browser at http://localhost:5173

## Architecture

```
┌─────────────────────┐     WebSocket      ┌─────────────────────┐
│    React Frontend   │◄──────────────────►│   FastAPI Backend   │
│  (Task Management)  │     REST API       │  (Task Processing)  │
└─────────────────────┘                    └──────────┬──────────┘
                                                      │
                                           ┌──────────▼──────────┐
                                           │     Gemini API      │
                                           │   LaTeX Compiler    │
                                           │   PDF Generation    │
                                           └─────────────────────┘
```

## Prerequisites

- **Python 3.10+**
- **Node.js 18+**
- **LaTeX** (MiKTeX on Windows, texlive on Linux/Mac)
- **Gemini API Key** from [Google AI Studio](https://aistudio.google.com/)

## Manual Installation

### 1. Install System Dependencies

**Windows:**
Download and install [MiKTeX](https://miktex.org/)
- During setup, set "Install missing packages on-the-fly" to **Always**

**Ubuntu/Debian:**
```bash
sudo apt-get update
sudo apt-get install texlive-latex-base texlive-fonts-recommended texlive-latex-extra
```

**macOS:**
```bash
brew install --cask mactex
```

### 2. Backend Setup

```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or: venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env and add your GEMINI_API_KEY
```

### 3. Frontend Setup

```bash
cd frontend
npm install
```

## Running the Application

### Development Mode

**Terminal 1 - Backend:**
```bash
cd backend
source venv/bin/activate
python main.py
```

**Terminal 2 - Frontend:**
```bash
cd frontend
npm run dev
```

Access the application at: **http://localhost:5173**

## Usage

1. **Create a Task**: Click "Add Task" in the sidebar
2. **Paste Job Description**: Copy and paste the job description into the text area
3. **Toggle Cover Letter**: Switch ON for Resume + Cover Letter, OFF for Resume only
4. **Start Generation**: Click "Start Task" to begin
5. **Monitor Progress**: Watch real-time progress updates for each step
6. **Download Files**: Once complete, download the generated files

## UI Features

### Settings Panel (⚙️ Settings button)

All settings are configurable from the UI and persisted automatically:

**API Configuration:**
- Gemini API Key
- Model selection (Gemini 3 Pro recommended)
- Thinking Level (Low/High)
- Enable Google Search Grounding

**Generation Settings:**
- Temperature (0.0 - 2.0)
- Max Output Tokens
- Max LaTeX Retries
- Generate Cover Letter by Default

**Page Length Validation:**
- ✅ Enforce Resume is 1 Page
- ✅ Enforce Cover Letter is 1 Page
- Max Page Retry Attempts (how many times to regenerate if too long)

### Prompts Editor (📄 Prompts button)

Edit 4 customizable prompt templates directly in the UI:

| Prompt | Description |
|--------|-------------|
| **User Information** | Your personal info (education, experience, projects, skills) |
| **Resume Format** | LaTeX template for resume structure |
| **Resume Prompt** | Main prompt for resume generation |
| **Cover Letter Prompt** | Prompt for cover letter generation |

**Template Placeholders:**
- `{{user_information}}` in Resume Prompt → automatically replaced with User Information content
- `{{latex_template}}` in Resume Prompt → automatically replaced with Resume Format content
- `{{JOB_DESCRIPTION}}` → replaced with the job description you provide

## Gemini 3 Pro Configuration

This application is optimized for **Gemini 3 Pro**. All parameters are configurable in the Settings UI or via `backend/.env`:

### Generation Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| Model | `gemini-3-pro-preview` | Gemini model to use |
| Temperature | `1.0` (recommended) | Creativity (0.0-2.0) |
| Top-K | `64` (fixed for Gemini 3) | Token vocabulary limit |
| Max Tokens | Model default | Maximum response length |
| Thinking Level | `high` | Reasoning depth (`low` or `high`) |
| Web Search | `false` | Google Search grounding |

### Thinking Levels (Gemini 3 Pro)

| Level | Description | Use Case |
|-------|-------------|----------|
| `low` | Faster processing | Simple tasks, high throughput |
| `high` | Deep reasoning | Complex formatting, better quality (default) |

**Note:** Gemini 3 Pro always uses thinking - it cannot be turned off.

### Google Search Grounding

When enabled, Gemini can search the web for:
- Current company information
- Recent news about the company
- Industry trends

**Note:** Search grounding costs $35 per 1,000 grounded queries.

## Page Length Validation

The system automatically validates that generated documents fit on exactly one page:

1. **Resume**: After LaTeX compilation, checks page count
2. **Cover Letter**: After PDF generation, checks page count

If a document exceeds 1 page:
1. System sends feedback to Gemini requesting a shorter version
2. Regenerates with specific instructions to condense content
3. Retries up to the configured maximum attempts
4. If still too long, accepts the result with a warning

## Task Processing Steps

### Resume + Cover Letter Mode (default)
1. **Generate Resume**: Gemini creates a tailored LaTeX resume using your prompts
2. **Compile LaTeX**: Convert LaTeX to PDF (with smart retry on errors)
3. **Validate Page Count**: Regenerate if resume exceeds 1 page
4. **Extract Text**: Read resume content for cover letter context
5. **Generate Cover Letter**: Create personalized cover letter
6. **Validate Page Count**: Regenerate if cover letter exceeds 1 page
7. **Create PDF**: Format cover letter as PDF

### Resume-Only Mode
1. **Generate Resume**: Gemini creates a tailored LaTeX resume
2. **Compile LaTeX**: Convert LaTeX to PDF (with smart retry on errors)
3. **Validate Page Count**: Regenerate if resume exceeds 1 page

## Output Files

Generated files are automatically named with the company name:

```
backend/output/
├── resume_Google.pdf
├── cover_letter_Google.pdf
├── resume_Microsoft.pdf
├── cover_letter_Microsoft.pdf
└── ...
```

## Project Structure

```
backend/
├── output/                    # Generated PDFs
├── logs/                      # Application logs
│   ├── app.log               # Main application log
│   ├── error.log             # Error-only log
│   ├── tasks.log             # Task processing log
│   └── debug_*.tex           # Debug LaTeX files
├── responses/                 # Gemini API responses
│   ├── task_1_resume_*.txt
│   └── task_1_cover_letter_*.txt
├── prompts/                   # Prompt templates (editable via UI)
│   ├── Resume_prompts.txt     # Main resume generation prompt
│   ├── Cover_letter_prompt.txt
│   ├── User_information_prompts.txt  # Your personal info
│   └── Resume_format_prompts.txt     # LaTeX template
├── services/                  # Core services
│   ├── gemini_client.py      # Gemini API client
│   ├── prompt_manager.py     # Prompt loading & substitution
│   ├── settings_manager.py   # Settings persistence
│   ├── pdf_page_counter.py   # Page validation
│   ├── latex_compiler.py     # LaTeX to PDF
│   └── task_manager.py       # Task orchestration
├── settings.json              # Persisted settings
├── config.py                  # Configuration
├── main.py                    # FastAPI application
└── .env                       # Environment variables

frontend/
├── src/
│   ├── components/           # React components
│   │   ├── TaskPanel.tsx     # Main task interface
│   │   ├── SettingsPanel.tsx # Settings modal
│   │   └── PromptsPanel.tsx  # Prompts editor modal
│   ├── store/                # Zustand state management
│   ├── hooks/                # Custom hooks
│   └── types/                # TypeScript types
└── ...
```

## API Endpoints

### Tasks

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/tasks` | Create new task |
| GET | `/api/tasks` | List all tasks |
| GET | `/api/tasks/{id}` | Get task details |
| PUT | `/api/tasks/{id}/settings` | Update task settings |
| POST | `/api/tasks/{id}/start` | Start processing |
| GET | `/api/tasks/{id}/resume` | Download resume |
| GET | `/api/tasks/{id}/cover-letter` | Download cover letter |
| WS | `/ws` | WebSocket for real-time updates |

### Settings

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/settings` | Get all settings |
| PUT | `/api/settings` | Update settings |
| POST | `/api/settings/reset` | Reset to defaults |

### Prompts

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/prompts` | Get all prompts |
| GET | `/api/prompts/{key}` | Get specific prompt |
| PUT | `/api/prompts/{key}` | Update prompt |
| POST | `/api/prompts/reload` | Reload from files |

## Logging

### Log Files

| Log File | Description |
|----------|-------------|
| `logs/app.log` | Main application log with all events |
| `logs/error.log` | Errors only for quick debugging |
| `logs/tasks.log` | Detailed task processing logs |

### Log Configuration

```env
LOG_LEVEL=INFO          # DEBUG, INFO, WARNING, ERROR
LOG_MAX_BYTES=10485760  # 10MB per file
LOG_BACKUP_COUNT=5      # Keep 5 backup files
```

## Troubleshooting

### "pdflatex not found"
Install LaTeX distribution:
- **Windows**: Install MiKTeX and set "Install missing packages on-the-fly" to "Always"
- **Linux**: `sudo apt-get install texlive-latex-base texlive-fonts-recommended`
- **macOS**: `brew install --cask mactex`

### "pdflatex timed out"
MiKTeX is probably showing a popup asking to install packages. Open MiKTeX Console and set "Install missing packages on-the-fly" to "Always".

### WebSocket connection failed
Ensure backend is running on port 8000

### API rate limits
Gemini has rate limits; wait and retry if exceeded

### "400 INVALID_ARGUMENT - Thinking level is not supported"
This error occurs with non-Gemini 3 models. Use `gemini-3-pro-preview` as the model.

## Customizing Prompts

### Via UI (Recommended)
1. Click the **Prompts** button in the top bar
2. Select the prompt tab to edit
3. Make your changes
4. Click **Save**

### Via Files
Edit files in `backend/prompts/`:
- `User_information_prompts.txt` - Your personal info
- `Resume_format_prompts.txt` - LaTeX template
- `Resume_prompts.txt` - Resume generation prompt
- `Cover_letter_prompt.txt` - Cover letter prompt

## License

MIT License
