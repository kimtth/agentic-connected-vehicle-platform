# Vehicle Handler

This module provides a comprehensive interface to all vehicle-related features in the Connected Car Platform, integrating with both direct API operations and the agent system.

## Overview

The Vehicle Handler serves as a bridge between the core platform functionality and the specialized agent system. It implements the business logic for all vehicle-related operations while providing a consistent interface for both direct API calls and agent-mediated natural language interactions.

## Components

### Core Handlers

- **Vehicle Profile Manager**: Manages vehicle profiles including registration, details, and configuration
- **Vehicle Service Manager**: Handles service subscriptions, maintenance records, and feature management
- **Vehicle API Executor**: Processes vehicle commands and communicates with connected vehicles
- **Vehicle Data Manager**: Manages vehicle data, logs, and analytics
- **Vehicle Notification Handler**: Handles system notifications and alerts

### VehicleHandler Class

The `VehicleHandler` class implements comprehensive functionality across all vehicle-related domains:

#### Remote Access
- Lock/unlock vehicle remotely
- Remote engine start/stop
- Sync personal data

#### Safety & Emergency
- Emergency call initiation
- Collision reporting
- Theft reporting and tracking

#### Charging & Energy
- Start/stop charging
- Charging station finder
- Energy usage management

#### Information Services
- Weather information
- Traffic updates
- Points of interest

#### Vehicle Feature Control
- Climate control
- Feature settings
- Subscription management

#### Diagnostics & Battery
- Vehicle health checks
- Diagnostic reports
- Battery status monitoring

#### Alerts & Notifications
- Alert configuration
- Notification preferences
- Critical alerts management

## Integration with Agent System

The Vehicle Handler includes a specialized method `handle_agent_request()` that processes requests from the agent system, providing a convenient interface for natural language interactions while maintaining separation of concerns.

## Usage

The Vehicle Handler can be used in two primary ways:

### Direct API Usage

```python
handler = VehicleHandler()
result = await handler.lock_vehicle("v123", {"doors": "all"})
```

### Agent-Mediated Usage

```python
handler = VehicleHandler()
result = await handler.handle_agent_request(
    agent_type="remote_access", 
    query="Lock all doors on my car", 
    context={"vehicle_id": "v123"}
)
```

## Design Principles

1. **Separation of Concerns**: Each feature area is logically separated
2. **Consistent Interface**: All methods follow consistent parameter and return patterns
3. **Comprehensive Logging**: All operations are logged for audit and analysis
4. **Integration Ready**: Built to work seamlessly with both API and agent systems
