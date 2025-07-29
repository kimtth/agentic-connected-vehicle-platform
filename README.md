# 🚗 Agentic Connected Vehicle Platform

An AI-driven car management system: control, diagnostics, and insights via agents.

## ✨ Features
- 🗣️ Natural-language agent interface  
- 🔒 Remote access: lock/unlock, engine start/stop  
- ⚡ EV charging & energy optimization  
- 📍 Weather, traffic, and POI info  
- 🎛️ In-car controls: climate, lights, windows  
- 🔧 Diagnostics & predictive maintenance  
- 🔔 Alerts & customized notifications  

## 🛠️ Tech Stack
- Backend: Python 3.12+, FastAPI, Semantic Kernel  
- DB: Azure Cosmos DB (AAD auth)  
- AI: Azure OpenAI
- Frontend: React, Material-UI  

## 🚀 Quick Start
1. 🔑 Azure login & resource group  
   ```bash
   az login
   az group create -n rg-car -l eastus
   ```
2. 🐍 Backend  
   ```bash
   cd vehicle
   poetry install
   cp .env.sample .env   # add your Azure keys
   python main.py
   ```
3. 🌐 Frontend  
   ```bash
   cd web
   yarn install
   yarn start
   ```
4. 🎉 Open  
   - Backend: http://localhost:8000  
   - Frontend: http://localhost:3000  

## 📖 Documentation
For full API reference, architecture, and examples, see the project documentation.

### Dashboard Overview
![Platform Dashboard](./doc/dashboard.png)

### Natural Language Agent Interface
![Agent Chat Interface](./doc/agent_chat.png)

### Vehicle Simulation & Control
![Car Simulator](./doc/car_simulator.png)

## 📜 License
MIT © kimtth
