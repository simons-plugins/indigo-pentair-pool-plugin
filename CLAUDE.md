# CLAUDE.md

## Plugin Overview

**Pentair Pool Controller** - Indigo plugin for Pentair pool/spa automation

- **Version**: 2026.0.0
- **Bundle ID**: `com.simons-plugins.pentair-pool`
- **Transport**: MQTT via paho-mqtt 2.x (bundled)
- **Middleware**: nodejs-poolController with MQTT binding

Integrates Pentair pool controllers (EasyTouch, IntelliTouch, IntelliCenter) with Indigo via nodejs-poolController's MQTT output.

## Architecture

### Coordinator Pattern

Each `poolController` device owns an MQTT connection via `ThreadMqttHandler`. Multiple coordinators supported for multi-controller setups.

### Message Flow

MQTT broker → paho callback → queue.Queue (per coordinator) → plugin.py runConcurrentThread drains queues → routes to handlers → updateStatesOnServer

### Device Types

| Type ID | Indigo Type | Purpose |
|---------|-------------|---------|
| `poolController` | custom | MQTT coordinator — connection status, air temp |
| `poolBody` | thermostat | Pool/spa heating — temp, setpoint, heat mode |
| `poolCircuit` | relay | Equipment circuits — on/off |
| `poolPump` | custom | IntelliFlo pumps — RPM, watts, GPM |
| `poolChlorinator` | custom | IntelliChlor — salt PPM, output %, super chlorinate |
| `poolChemistry` | sensor | IntelliChem — pH, ORP, saturation index |

### Handler Modules

| Module | Purpose |
|--------|---------|
| `mqtt_handler.py` | ThreadMqttHandler — per-coordinator MQTT thread |
| `discovery.py` | Equipment discovery from MQTT topics |
| `handlers/body.py` | Pool/spa body thermostat state mapping |
| `handlers/circuit.py` | Circuit relay state mapping |
| `handlers/pump.py` | Pump custom device state mapping |
| `handlers/chlorinator.py` | Chlorinator custom device state mapping |
| `handlers/chemistry.py` | Chemistry sensor state mapping |

## Prerequisites

1. **nodejs-poolController** running with MQTT binding enabled
2. **MQTT broker** (Mosquitto, Indigo MQTT Broker plugin, etc.)
3. nodejs-poolController configured with root topic (default: "pool")

## Testing

Copy to Indigo server:
```bash
cp -r "Pentair Pool Controller.indigoPlugin" "/Volumes/Macintosh HD-1/Library/Application Support/Perceptive Automation/Indigo 2025.1/Plugins/"
```

## Actions

| Action | Device Type | Description |
|--------|-------------|-------------|
| Set Heat Setpoint | poolBody | Native thermostat setpoint control |
| Set Heat Mode | poolBody | Off / Heater / Solar Preferred / Solar Only |
| Turn On/Off | poolCircuit | Native relay control |
| Set Pump Speed | poolPump | Set RPM |
| Set Pump Program | poolPump | Select speed program 1-4 |
| Set Chlorinator Output | poolChlorinator | Set output percentage |
| Super Chlorinate | poolChlorinator | Enable/disable super chlorination |

## Dependencies (bundled)

- `paho-mqtt` 2.1.0 — MQTT client
