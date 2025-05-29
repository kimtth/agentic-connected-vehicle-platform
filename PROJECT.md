# Agentic Connected Car Platform

An intelligent vehicle management platform where specialized AI agents handle different aspects of vehicle operations and user interactions.

## Architecture Overview

The platform consists of a **FastAPI backend** with **Semantic Kernel-based agents**, a **React.js frontend**, and **Azure Cosmos DB** for data persistence. Each agent specializes in specific vehicle domains and uses **kernel functions** to execute operations.

## Core Components

### Backend Services (Python/FastAPI)
- **AgentManager** – Central orchestrator that interprets user intent and delegates to specialized agents
- **Vehicle API/Command Executor** – RESTful API for receiving commands and managing vehicle operations
- **Cosmos DB Integration** – Handles vehicle data, commands, notifications, and status persistence
- **Car Simulator** – Simulates vehicle behavior and responses for testing
- **MCP Weather Server** – Provides weather information via Model Context Protocol
- **A2A Communication Server** – Handles agent-to-agent communication

### Frontend (React.js)
- **Dashboard UI** – Displays vehicle status, commands, notifications, and real-time data
- **Command Interface** – Allows users to send commands to vehicles
- **Status Monitoring** – Real-time vehicle status updates and telemetry

### Data Management (Azure Cosmos DB)
- **Vehicle Profiles** – Vehicle metadata, specifications, and configuration
- **Commands** – Command history, status tracking, and execution logs
- **Vehicle Status** – Real-time telemetry and state information
- **Notifications** – System alerts, warnings, and user notifications
- **Services** – Maintenance records and service history
- **POIs & Charging Stations** – Location-based services data

## Specialized AI Agents

### 1. **Vehicle Feature Control Agent**
Manages in-car comfort and convenience features:
- **Climate Control** – Temperature, fan speed, A/C, heating adjustments
- **Seat Heating** – Individual seat heating level control
- **Subscription Management** – Active service subscriptions and plans
- **Vehicle Settings** – Current configuration and preferences

### 2. **Remote Access Agent** 
Controls vehicle access and remote operations:
- **Door Control** – Lock/unlock all doors or individual doors
- **Engine Control** – Remote start/stop with safety validations
- **Data Synchronization** – Personal data and preference sync

### 3. **Safety & Emergency Agent**
Handles critical safety and emergency situations:
- **Emergency Calls** – Automatic eCall initiation with location data
- **Collision Detection** – Collision alert processing and emergency response
- **Theft Protection** – Vehicle theft reporting and tracking
- **SOS Requests** – Manual emergency assistance requests

### 4. **Charging & Energy Agent**
Manages electric vehicle charging and energy optimization:
- **Charging Stations** – Find nearby stations with availability and pricing
- **Charging Control** – Start/stop charging sessions remotely
- **Energy Analytics** – Usage tracking, efficiency monitoring, regenerative braking
- **Range Estimation** – Real-time range calculation with driving conditions

### 5. **Information Services Agent**
Provides real-time contextual information:
- **Weather Services** – Current conditions and forecasts via MCP integration
- **Traffic Information** – Real-time traffic conditions and incidents
- **Points of Interest** – Nearby restaurants, services, and attractions
- **Navigation** – Route planning and turn-by-turn directions

### 6. **Diagnostics & Battery Agent**
Monitors vehicle health and maintenance needs:
- **System Diagnostics** – Comprehensive vehicle system health checks
- **Battery Monitoring** – Battery health, voltage, and replacement scheduling
- **System Health** – ECU status, error codes, and component monitoring
- **Maintenance Scheduling** – Service intervals and upcoming maintenance

### 7. **Alerts & Notifications Agent**
Manages proactive alerts and user notifications:
- **Speed Alerts** – Configurable speed limit notifications
- **Curfew Monitoring** – Time-based vehicle usage alerts
- **Battery Warnings** – Low battery and charging reminders
- **Notification Settings** – User preference management for alerts

## Tech Stack

### Backend
- **Python 3.12+** with FastAPI framework
- **Semantic Kernel** for AI agent orchestration
- **Azure Cosmos DB** for data persistence
- **Azure Identity & Storage** for cloud integration
- **OpenAI** for natural language processing
- **Uvicorn** ASGI server
- **Pydantic** for data validation
- **Loguru** for structured logging

### Frontend
- **React.js** with modern hooks
- **Recharts** for data visualization
- **Real-time updates** via WebSocket/SSE

### Infrastructure
- **Azure Cloud Services**
- **Model Context Protocol (MCP)** for weather services
- **Multiprocessing** for concurrent agent services

## API Endpoints

### Core Vehicle Operations
- `GET /api/` - Platform status and health check
- `POST /api/command` - Submit vehicle commands
- `GET /api/commands` - Retrieve command history
- `GET /api/vehicle/{id}/status` - Get real-time vehicle status
- `GET /api/vehicle/{id}/status/stream` - Stream vehicle status updates

### Vehicle Management
- `POST /api/vehicle` - Add new vehicle profile
- `GET /api/vehicles` - List all vehicles
- `PUT /api/vehicle/{id}/status` - Update vehicle status
- `PATCH /api/vehicle/{id}/status` - Partial status updates

### Services & Maintenance
- `POST /api/vehicle/{id}/service` - Add service record
- `GET /api/vehicle/{id}/services` - List vehicle services

### Notifications & Alerts
- `GET /api/notifications` - Retrieve notifications
- `GET /api/simulator/vehicles` - Get simulated vehicle IDs

### Agent Communication
- `POST /api/agent/chat` - Send messages to AI agents
- `GET /api/agent/chat/stream` - Stream agent responses

## Data Models

### Vehicle Profile
```python
VehicleId, Brand, VehicleModel, Year, Country, Region
Features: {IsElectric, HasNavigation, HasAutoPilot}
LastLocation: {Latitude, Longitude}
```

### Vehicle Status
```python
Battery/BatteryLevel, Speed, Temperature, EngineStatus
Location: {latitude, longitude}
ClimateSettings: {temperature, fanSpeed, isAirConditioningOn}
DoorStatus: {driver, passenger, rearLeft, rearRight}
```

### Command Structure
```python
CommandId, VehicleId, CommandType, Parameters
Status: {pending, processing, completed, failed}
Timestamp, Priority: {Low, Normal, High, Critical}
```

## System Flow

### Asynchronous Command Processing
1. **Command Submission** → FastAPI receives command via POST /api/command
2. **Command Storage** → Stored in Cosmos DB with pending status
3. **Background Processing** → Command processed asynchronously
4. **Vehicle Communication** → Command sent to car simulator
5. **Status Updates** → Command status updated (processing → completed)
6. **Notification Creation** → Success/failure notification generated

### Agent Message Processing
1. **User Query** → Received via /api/agent/chat
2. **Intent Analysis** → AgentManager analyzes user intent
3. **Agent Delegation** → Appropriate specialized agent selected
4. **Function Execution** → Agent executes kernel functions
5. **Response Generation** → Structured response with actions taken
6. **Real-time Updates** → Status changes reflected in vehicle data

## Development Setup

### Dependencies
```toml
fastapi, uvicorn, pydantic, openai, semantic-kernel
azure-cosmos, azure-identity, azure-storage-blob
pytest, loguru, fastmcp, jwcrypto
```

### Environment Configuration
```env
API_HOST=0.0.0.0
API_PORT=8000
LOG_LEVEL=INFO
AZURE_COSMOS_DB_ENDPOINT=<cosmos-endpoint>
AZURE_COSMOS_DB_KEY=<cosmos-key>
OPENAI_API_KEY=<openai-key>
```

### Service Ports
- **Main API**: 8000
- **Weather MCP Server**: 8001  
- **A2A Communication**: 8002

## Key Features

- **Multi-Agent Architecture** with specialized domain expertise
- **Real-time Status Monitoring** with live vehicle telemetry
- **Asynchronous Command Processing** for scalable operations
- **Comprehensive Logging** with structured log management
- **Azure Cloud Integration** for enterprise-grade reliability
- **Natural Language Interface** for intuitive user interactions
- **Extensible Plugin System** via Semantic Kernel functions