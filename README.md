# AgriMind AI

A professional agricultural advisor powered by **Groq AI** with RAG (Retrieval-Augmented Generation) and live weather integration.

![version](https://img.shields.io/badge/version-2.0.0-green)
![python](https://img.shields.io/badge/python-3.10%2B-blue)
![groq](https://img.shields.io/badge/groq-API-yellow)

## ✨ Features

- **Professional Agricultural Advice**: Get expert guidance on crops, soil, irrigation, pest control, and sustainable farming
- **Groq API Integration**: Fast, efficient AI responses powered by Groq's models
- **🌍 Real-time Weather Integration**: Live weather automatically fetched from your location
  - Auto-detects your location when you open the app (with permission)
  - Weather data automatically included in all AI responses
  - Updates every 10 minutes in the background
  - AI provides weather-aware farming recommendations
- **RAG System**: Accuracy grounded in agricultural knowledge base
- **Clean, Modern UI**: Professional interface designed for farmers
- **Real-time Chat**: Instant responses to agricultural questions

## 🚀 Getting Started (Step-by-Step)

### Prerequisites
- **Docker Desktop** (download from [docker.com](https://docker.com/products/docker-desktop))
  - This includes both Docker and Docker Compose
  - Available for Mac, Windows, and Linux
- **Groq API Key** (free - takes 2 minutes)
  - Sign up at [console.groq.com](https://console.groq.com/)
  - Create a new API key

### Step 1: Install Docker

1. Download **Docker Desktop** from [docker.com](https://docker.com/products/docker-desktop)
2. Install and open Docker Desktop
3. Verify installation by running:
   ```bash
   docker --version
   docker-compose --version
   ```

### Step 2: Get Your Groq API Key

1. Go to [console.groq.com](https://console.groq.com/)
2. Sign up or log in
3. Create a new API key
4. **Copy your key** (starts with `gsk_`)

### Step 3: Set Up Configuration

1. Open a terminal in the project folder
2. Create a `.env` file with your API key:
   ```bash
   echo "GROQ_API_KEY=your_actual_key_here" > .env
   ```
   *(Replace `your_actual_key_here` with the actual key from Step 2)*

### Step 4: Start the App

Run one of these commands:

source venv/bin/activate 

**Option A (Easiest):**
```bash
./docker-start
```

**Option B (Direct):**
```bash
docker-compose up --build
```

Both commands will:
- Download required images (first time only)
- Build the Docker container
- Start the server
- Load 33 agricultural knowledge base entries
- Show a ✅ confirmation when ready

### Step 5: Open in Browser

Once you see the startup confirmation:
```
http://localhost:8000
```

✅ **That's it!** The app is running and ready to use.

### First Time Using the App

When you open the browser:
1. You'll be asked to **share your location** (click "Allow")
2. Weather for your location loads automatically
3. Start chatting with the agricultural advisor
4. The AI will automatically use your live weather in recommendations

## 📋 Common Tasks

### Start the App
```bash
./docker-start
```
or
```bash
docker-compose up --build
```

### Stop the App
```bash
docker-compose down
```
(Stops all containers — app will be offline until you run start command again)

### View Live Logs
```bash
docker-compose logs -f
```
(Use `Ctrl+C` to exit logs)

### Restart the App
```bash
docker-compose restart
```

### Check if App is Running
Open http://localhost:8000 in browser, or run:
```bash
curl http://localhost:8000/api/health
```

### Clean Up (Remove Images, Start Fresh)
```bash
docker-compose down -v
docker system prune -a
```
Then run `./docker-start` to rebuild from scratch.

## 🏗️ Project Structure

```
├── backend/
│   ├── main.py          # FastAPI application
│   ├── chat.py          # Groq AI integration
│   ├── rag.py           # Knowledge retrieval system
│   ├── weather.py       # OpenMeteo weather API
│   └── requirements.txt  # Python dependencies
├── frontend/
│   ├── index.html       # Web interface
│   ├── app.js          # Frontend logic
│   └── style.css       # Professional styling
├── start               # Quick start script
├── start.sh           # Full startup script
├── Makefile           # Build commands
└── .env              # Configuration (create this)
```

## 🔧 Technology Stack

- **Backend**: FastAPI, Python 3.11
- **AI Model**: Groq API (Llama 3.1 70B - Versatile)
- **Deployment**: Docker & Docker Compose
- **RAG**: scikit-learn TF-IDF vectorizer
- **Weather**: OpenMeteo API
- **Frontend**: Vanilla JS, HTML5, CSS3
- **Server**: Uvicorn

## 📖 API Documentation

Once the server is running, access:

- **Interactive API docs**: http://localhost:8000/docs
- **Alternative docs**: http://localhost:8000/redoc

### Main Endpoints

- `GET /api/health` - Server status and knowledge base info
- `POST /api/chat` - Send message and get agricultural advice
- `POST /api/weather` - Fetch weather for a location (manual)
- `POST /api/weather/by-coords` - Fetch weather by coordinates (auto-detection)

## 🌍 Real-Time Weather Features

AgriMind AI automatically detects your location and fetches live weather data to enhance recommendations:

### How It Works

1. **Auto-Detection**: When you open the app, it requests permission to detect your location (using browser Geolocation API)
2. **Automatic Fetch**: If you grant permission, weather is fetched immediately for your coordinates
3. **Smart Integration**: All chat responses include your current weather conditions
4. **Continuous Updates**: Weather refreshes every 10 minutes in the background
5. **Location Display**: The weather panel shows your detected location at the top

### What Weather Data Is Included

The AI receives real-time access to:
- **Current conditions**: Temperature, humidity, wind speed, precipitation, weather description
- **7-day forecast**: Temperature range, total rainfall, rain probability
- **Farming alerts**: High humidity (fungal disease risk), heavy rain, extreme heat, frost, high winds

### Example AI Response with Weather

Without weather, the AI gives general advice. With weather context, it provides:

> "Given your current 15°C conditions with 70% humidity, **avoid applying fungicides today** due to high disease risk. Wait for drier conditions (humidity < 65%) before spraying. Meanwhile, prepare fields for the 25mm rain forecast this week by improving drainage."

### Manual Weather Entry

If you prefer to manually set a location:
1. Open the "Live Weather" panel (click the weather icon)
2. Enter a city name or region
3. Click "Fetch Weather"

The entered location becomes permanent until you change it again.

### Privacy Note

- Location is detected entirely in your browser (no tracking)
- Weather data is fetched from OpenMeteo (free, no API key required)
- No personal data is stored or transmitted

The AI is configured for:
- **Accuracy**: Structured responses with specific quantities and timing
- **Professionalism**: Clear, actionable advice backed by agriculture databases
- **Farmer-Friendly**: Accessible language while maintaining scientific accuracy
- **Safety**: Non-agricultural questions are politely redirected

Response format includes:
- 🔍 **Analysis** - Assessment of the situation
- 📋 **Action Plan** - Specific steps with quantities and timing
- ⚠️ **Risks** - 1–3 specific threats to watch
- 💡 **Pro Insight** - Practical tip farmers often miss

## 🎨 UI/UX Improvements

- Modern, professional color scheme (avoiding AI-generated look)
- Clean typography with DM Sans and DM Serif Display
- Responsive grid layout
- Smooth animations and transitions
- Professional badge indicators
- Dark theme optimized for readability

## 🐛 Bug Fixes & Improvements

- ✓ Fixed relative import issues in FastAPI
- ✓ Updated AI model from deprecated Mixtral to **Llama 3.1 70B**
- ✓ Fixed Groq API system message handling
- ✓ Suppressed HuggingFace dataset warnings
- ✓ Fixed branding references throughout
- ✓ Improved error handling in chat endpoints
- ✓ Fixed weather data integration
- ✓ Professional UI styling
- ✓ Dockerized for smooth deployment

## ⚠️ Troubleshooting

### "Connection refused" at http://localhost:8000
- Wait 5-10 seconds after running `./docker-start`
- Check Docker Desktop is open and running
- Run `docker-compose logs` to see if there are startup errors

### "GROQ_API_KEY not found" Error
- Verify `.env` file exists in the project root
- Check that your API key starts with `gsk_`
- Make sure there are no extra spaces: `GROQ_API_KEY=gsk_...` (no spaces around `=`)

### Weather Not Loading
- Click "Allow" when browser asks for location permission
- Check browser console (F12) for errors
- Try manually entering a location in the weather panel

### Docker Commands Not Found
- Restart Docker Desktop
- Verify installation: `docker --version`
- On Mac/Linux, may need to add `/usr/local/bin` to PATH

### Container Won't Start
Run this to see detailed logs:
```bash
docker-compose logs --tail=50
```

Still stuck? Try a clean rebuild:
```bash
docker-compose down -v
docker-compose up --build
```

## 📝 Environment Variables

Create a `.env` file in the project root:

```bash
GROQ_API_KEY=your_groq_api_key_here
GROQ_MODEL=llama-3.1-8b-instant
GROQ_MODEL_FALLBACKS=llama-3.1-70b-versatile,llama-3.1-8b-instant
```

## 🔒 Security

- API keys are server-side only (never exposed in browser)
- CORS enabled for safe cross-origin requests
- Input validation on all endpoints

## 📧 Support

For issues or questions:
1. Check the API documentation at `/docs`
2. Verify your Groq API key is valid
3. Ensure `.env` file exists with proper permissions

## Link to Website:

http://localhost:8000

## 📄 License


---

**AgriMind AI v2.0.0** - Bringing intelligence to small and commercial farms worldwide.
