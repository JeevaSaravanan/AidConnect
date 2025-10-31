# AidConnect 🚨

[![NVIDIA Hackathon Winner](https://img.shields.io/badge/🏆_NVIDIA_Hackathon-Winner-76B900?style=for-the-badge)](https://github.com/JeevaSaravanan/AidConnect)

> AI-Powered Disaster Response & Resource Coordination Platform

AidConnect is an AI-powered disaster response platform that intelligently matches shelter resources with affected areas during emergencies. Built with NVIDIA AI technology.

![React](https://img.shields.io/badge/React-18.3-blue)
![TypeScript](https://img.shields.io/badge/TypeScript-5.8-blue)
![Python](https://img.shields.io/badge/Python-3.9+-green)

## ✨ Key Features

- 🤖 **AI-Powered Resource Matching** - NVIDIA Llama 3.3 Nemotron intelligently matches shelters with affected areas
- 🌦️ **Weather Forecasting** - NVIDIA FourCastNet for advanced weather simulation
- 🗺️ **Interactive Maps** - Real-time visualization of shelters, resources, and affected areas
- 💬 **AI Assistant** - Chat interface for disaster coordination
- 📊 **Live Dashboard** - Real-time metrics and alert feed

## 📋 Quick Links

- [Installation](#installation)
- [Running the App](#running-the-application)
- [API Docs](#api-documentation)
- [Technology Stack](#technology-stack)

## 🏗️ Architecture

```
Frontend (React + TypeScript)
    ↓
Backend APIs (Python Flask)
    ↓
NVIDIA AI Models (Llama 3.3 + FourCastNet)
```

**Components:**
- **Frontend**: React + TypeScript + Tailwind CSS
- **Resource Matching API**: Flask + NVIDIA Llama 3.3
- **Weather Simulation**: NVIDIA FourCastNet
- **MCP Hub**: Multi-service orchestration

## 🔧 Prerequisites

- Node.js 18+ and npm
- Python 3.9+
- **NVIDIA NGC API Key** ([Get it here](https://org.ngc.nvidia.com/))

## 📦 Installation

```bash
# Clone repository
git clone https://github.com/JeevaSaravanan/AidConnect.git
cd AidConnect

# Install frontend
npm install

# Install backend
python -m venv venv
source venv/bin/activate  # Windows: .\venv\Scripts\activate
cd mcp-hub && pip install -r requirements.txt
cd ../server/simulation && pip install -r requirements.txt
```

## ⚙️ Configuration

Create `.env` in `mcp-hub/`:

```bash
NV_API_KEY=your_nvidia_api_key
NGC_API_KEY=your_nvidia_ngc_api_key
NV_INVOKE_URL=https://integrate.api.nvidia.com/v1/chat/completions
NV_MODEL=nvidia/llama-3.3-nemotron-super-49b-v1.5
```

## 🚀 Running the Application

**Terminal 1 - Frontend:**
```bash
npm run dev
```

**Terminal 2 - Resource Matching API:**
```bash
cd mcp-hub
source venv/bin/activate
python flask_api.py
```

**Terminal 3 - Weather Simulation:**
```bash
cd server/simulation
source ../../venv/bin/activate
python app.py
```

Access the app at `http://localhost:8080`

## 📚 API Documentation

### Resource Matching API (Port 5002)

**POST** `/api/match-resources` - Match affected areas with shelters using AI

**GET** `/api/health` - Health check

### Weather Simulation API (Port 5001)

**POST** `/forecast` - Generate weather forecast videos

**GET** `/video/<timestamp>/<variable>` - Retrieve forecast video

For detailed API docs, see `mcp-hub/MATCH_RESOURCES_README.md`

## 📁 Project Structure

```
AidConnect/
├── src/                    # Frontend (React + TypeScript)
│   ├── components/        # UI components
│   ├── pages/            # Page routes
│   └── hooks/            # Custom hooks
├── mcp-hub/              # Backend APIs
│   ├── flask_api.py     # Resource matching API
│   ├── match_resources_api.py
│   └── llm_utils.py     # NVIDIA AI integration
├── server/simulation/    # Weather forecasting
│   └── app.py           # FourCastNet service
└── data/                # Shelter & volunteer data
```

## 🛠️ Technology Stack

**Frontend:** React 18, TypeScript, Vite, Tailwind CSS, shadcn/ui, Leaflet Maps

**Backend:** Python, Flask, FastAPI, FastMCP

**AI/ML:** NVIDIA Llama 3.3 Nemotron, NVIDIA FourCastNet, LangChain, RAG

**Data:** ArcGIS, FEMA API, OpenStreetMap

## 💻 Development

```bash
# Frontend development
npm run dev

# Linting
npm run lint

# Build for production
npm run build
```

## 🐛 Troubleshooting

**Port in use:**
```bash
lsof -ti:5001 | xargs kill -9  # Weather service
lsof -ti:5002 | xargs kill -9  # Resource API
```

**Module not found:**
```bash
source venv/bin/activate
pip install -r requirements.txt
```

**NVIDIA API errors:** Verify API key and model access

For more help, see `mcp-hub/MATCH_RESOURCES_README.md`

## 🙏 Acknowledgments

- **NVIDIA** for AI APIs and FourCastNet technology
- **shadcn/ui** for component library
- OpenStreetMap, FEMA, and ArcGIS for data

## 📞 Contact

**Jeeva Saravanan**

Repository: [github.com/JeevaSaravanan/AidConnect](https://github.com/JeevaSaravanan/AidConnect)

---

🏆 **Winner of NVIDIA Hackathon** | Built with ❤️ for disaster response
