# RFID Access Control System – Multi-Gate Architecture

This project implements an **RFID-based access control system** that supports **multiple gates**, each managed by its own Raspberry Pi and RFID scanner interface.  
The system is designed for **offline-first operation**, with local databases that synchronize across all gates in real time without relying on cloud infrastructure.

---

## System Overview

- Each gate has a **Raspberry Pi** hosting a local **MariaDB** instance.  
- A **custom ESP32-S3 capture & relay device** collects UID data from RFID scanners and forwards it to the gate’s Raspberry Pi via a **receiver ESP32**.  
- The Pi checks the UID against the local database, logs the attempt, and returns a decision (PASS/FAIL).  
- The ESP32 provides **LED and buzzer feedback** for user interaction.  
- All Raspberry Pis synchronize their databases over the local network, ensuring **consistent access records** across gates.

---

## Data Flow

1. **RFID Capture**
   - RFID scanners (USB HID, RS232, UART) connect to **ESP32-S3 capture & relay modules**.  
   - Data is transmitted wirelessly to a **receiver ESP32** at the gate.

2. **Gate Node Processing**
   - The **receiver ESP32** passes data to the gate’s Raspberry Pi.  
   - The Pi logs the event in its **MariaDB** instance and checks user authorization.  
   - Access status (PASS/FAIL) is sent back to the ESP32 for **LED/audio output**.

3. **Database Synchronization**
   - Each Raspberry Pi hosts its own database to remain functional offline.  
   - Nodes are interconnected via **Ethernet** or **local WiFi**, synchronizing in real time.  
   - For 2 gates, Pis can be directly connected; for more, they connect through a **switch or routers**.

---

## Network Architecture Options

From the block diagram, three networking approaches are considered:

- **Option 1 – Ethernet Backbone (Recommended)**
  - Most robust, minimum latency  
  - Setup required on-site  
  - Range 100m (extendable with routers)  

- **Option 2 – Local WiFi Router**
  - Easier setup compared to Ethernet  
  - More vulnerable to interference  
  - Effective range ~30m indoors (100m line of sight)  

- **Option 3 – WiFi Mesh Network**
  - Simplest to scale  
  - Higher range and flexibility  
  - Increased cost, less robust than Ethernet  

---

## Key Features

- **Scalable multi-gate setup** (add new Pis + scanners easily)  
- **Modular scanner compatibility** (USB HID, RS232, UART)  
- **Offline-first resilience** (no reliance on internet/cloud)  
- **Real-time user feedback** (LED + buzzer outputs)  
- **Local DB synchronization** ensures global consistency  

---

## Technologies Used

- **Hardware**:  
  - Raspberry Pi (per gate)  
  - ESP32-S3 (capture & relay, receiver)  
  - RFID scanners (USB HID, RS232, UART)  
  - LEDs + buzzers  

- **Software**:  
  - MariaDB (local DB with sync)  
  - Custom ESP32 firmware (relay & feedback logic)  
  - Python/Node.js backend services  

---

## Block Diagram

![System Architecture](docs/block.jpg)

*Diagram: Multi-gate RFID access control system with capture devices, receivers, Raspberry Pis, and database synchronization.*

## Backend and Frontend

### Directory Structure for the app
```
rfid_access_control/
├── app/
│   ├── __init__.py
│   ├── main.py                 # FastAPI app entry point
│   ├── config.py              # Configuration management
│   ├── database.py            # Database connection and setup
│   ├── models/
│   │   ├── __init__.py
│   │   ├── schemas.py         # Pydantic models
│   │   └── enums.py          # Enums and constants
│   ├── services/
│   │   ├── __init__.py
│   │   ├── access_control.py  # Core business logic
│   │   ├── user_service.py    # User management
│   │   ├── sync_service.py    # Database synchronization
│   │   └── serial_service.py  # Serial communication
│   ├── api/
│   │   ├── __init__.py
│   │   ├── routes/
│   │   │   ├── __init__.py
│   │   │   ├── scan.py        # Scan endpoints
│   │   │   ├── users.py       # User management endpoints
│   │   │   └── sync.py        # Sync endpoints
│   │   └── dependencies.py    # FastAPI dependencies
│   ├── utils/
│   │   ├── __init__.py
│   │   ├── validators.py      # Validation helpers
│   │   └── exceptions.py      # Custom exceptions
│   └── workers/
│       ├── __init__.py
│       └── serial_worker.py   # Background serial worker
└── requirements.txt
```

### Key Architectural Decisions

1. **Separation of Concerns**: Business logic is separated from API endpoints and data access.

2. **Dependency Injection**: FastAPI's dependency system manages database connections and service instances.

3. **Error Handling**: Custom exceptions provide clear error reporting throughout the system.

4. **Configuration Management**: Centralized configuration with environment variable support.

5. **Modular Services**: Each major functionality is encapsulated in its own service class.

## Quick Start

1. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Configure Environment**:
   ```bash
   cp .env.example .env
   # Edit .env with your specific configuration
   ```

3. **Set Up Database**:
   - Create MySQL/MariaDB database using the provided schema
   - Update DB_URL in .env

4. **Run the Application**:
   ```bash
   python -m app.main
   ```

## API Endpoints

### Scan Operations
- `POST /api/scan` - Process RFID scan
- `GET /health` - Health check

### User Management
- `POST /api/users` - Create new user
- `POST /api/users/import` - Import users from CSV
- `GET /api/users/{user_id}` - Get user by ID
- `GET /api/users` - List users (paginated)

### Synchronization
- `GET /api/sync/status` - Get sync status
- `POST /api/sync/trigger` - Trigger manual sync

## Configuration

Key environment variables:

- `DB_URL`: Database connection string
- `SERIAL_PORT`: Serial port for ESP32 communication
- `NODE_ID`, `GATE_ID`, `BOOTH_ID`, `DEVICE_ID`: System topology IDs
- `API_DEBUG`: Enable debug logging

## Serial Communication

The system automatically handles serial communication with ESP32 devices:

1. **Message Format**: JSON messages over UART
2. **Request Processing**: Automatic RFID tag validation
3. **Response Generation**: Status and event information
4. **Error Handling**: Robust error recovery and logging

## Database Synchronization

The system supports multi-node synchronization:

- Real-time sync status monitoring
- Conflict resolution mechanisms  
- Manual sync triggering
- Offline operation capability

## Extending the System

### Adding New Services

1. Create service class in `app/services/`
2. Add corresponding API routes in `app/api/routes/`
3. Update `main.py` to include new routes

### Adding New Models

1. Define Pydantic schemas in `app/models/schemas.py`
2. Add enums/constants to `app/models/enums.py`

### Custom Validation

Add validation logic to `app/utils/validators.py`

## Testing

```bash
# Run tests (when implemented)
pytest

# Manual testing
curl -X POST "http://localhost:8000/api/scan" \
  -H "Content-Type: application/json" \
  -d '{"rfid_tag":"123456","gate_id":1,"booth_id":1,"device_id":1,"node_id":1}'
```

## Production Deployment

1. Set `API_DEBUG=false`
2. Configure proper CORS origins
3. Use production database credentials
4. Set up reverse proxy (nginx)
5. Configure systemd service for auto-start

## Troubleshooting

### Common Issues

1. **Serial Port Permissions**: Ensure user has access to serial device
2. **Database Connection**: Verify database is running and credentials are correct  
3. **Missing Configuration**: Check all required environment variables are set

### Logging

Enable debug logging with `API_DEBUG=true` to see detailed operation logs.
