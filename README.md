# FastAsk

FastAsk is a cross-platform PyQt application for fast interaction with LLMs (OpenAI API). The app allows you to instantly send text queries and receive answers, and (optionally) select a screen area and attach a screenshot to your query.

## Main Features

- **Quick launch via hotkey** — call the app from anywhere in the system with a customizable key combination
- **One-shot Q&A** — instant query to LLM and answer without extra steps
- **Screenshots** — ability to select a screen area and attach a screenshot to the query
- **Query history** — saves all queries and answers with search capability
- **Flexible settings via .env file**:
  - API URL (to support different providers)
  - Model name (gpt-4, gpt-3.5-turbo, etc.)
  - System prompt (set context for LLM)
  - API keys
  - Temperature and other generation parameters
- **Minimalistic and convenient interface** — nothing extra, just query input and answer display

## Detailed Functionality

### Interface
- Minimalistic window with query input and answer output area
- Ability to resize and reposition the window
- Support for dark/light theme depending on system settings
- Loading indicator while waiting for API response

### Screenshots
- Ability to take a screenshot of the whole screen or a selected area
- Screenshot preview before sending
- Automatic OCR (text recognition) on the image and adding it to the query (optional)

### Query History
- Local storage of query and answer history in SQLite database
- Quick access to previous queries via dropdown list
- Search capability in history
- Export/import history to/from JSON file

### LLM Interaction
- Asynchronous API requests for smooth UI experience
- Streaming response support for fast answer display as it is generated
- Context setup for different tasks via system prompt
- Ability to interrupt answer generation

### System Integration
- Autostart with the system (optional)
- Clipboard integration for quick copy of queries and answers
- Notifications on answer generation completion
- Supports Windows, macOS, and Linux

## How it works

1. Launch the app with a hotkey
2. Enter your text query
3. (Optional) select a screen area for a screenshot
4. Get the answer from LLM right in the app
5. The answer is automatically saved to history

## Technologies

- Python 3.8+
- PyQt6 (UI)
- requests/aiohttp (for OpenAI API)
- pillow (screenshot processing)
- python-dotenv (for .env file)
- sqlite3 (for query history storage)
- keyboard (for global hotkeys)

## Project Structure

```
fast-ask/
├── assets/                  # App resources (icons, etc.)
├── src/                     # Source code
│   ├── ui/                  # UI components
│   ├── models/              # Data models
│   ├── utils/               # Helper functions
│   ├── app.py               # Main app class
│   └── main.py              # Entry point
├── .env.example             # Example config file
├── requirements.txt         # Dependencies
└── README.md                # Documentation
```

## Configuration (.env)

```
# OpenAI API
OPENAI_API_KEY=your_api_key_here
OPENAI_API_URL=https://api.openai.com/v1
OPENAI_MODEL=gpt-4

# App settings
SYSTEM_PROMPT=You are a helpful assistant. Answer briefly and to the point.
TEMPERATURE=0.7
MAX_TOKENS=1000

# Hotkeys
APP_HOTKEY=ctrl+shift+space
SCREENSHOT_HOTKEY=ctrl+shift+s
```

## Development Launch

1. Clone the repository
2. Create a virtual environment: `python -m venv venv`
3. Activate it:
   - Windows: `venv\Scripts\activate`
   - macOS/Linux: `source venv/bin/activate`
4. Install dependencies: `pip install -r requirements.txt`
5. Copy `.env.example` to `.env` and configure your settings
6. Run the app: `python src/main.py`

## TODO

- [ ] Basic UI for query input and answer display
- [ ] OpenAI API integration
- [ ] Screen area selection and screenshot attachment
- [ ] Query history storage in SQLite
- [ ] Global hotkeys to call the app
- [ ] Settings management via .env file