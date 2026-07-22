---
name: mes-connector
description: "MES/SCADA data ingestion. Adapters for Ignition/Inductive Automation (MQTT + REST). Modbus TCP for direct PLC reads. Reads machine states, counts, downtime events."
version: 1.0.0
tags: [manufacturing, mes, scada, ignition, modbus, plc, iot]
triggers:
  - "connect mes"
  - "scada data"
  - "ignition connector"
  - "modbus read"
  - "machine state"
  - "plc data"
  - "production count"
---

# MES Connector

Ingests data from Manufacturing Execution Systems (MES) and SCADA platforms. Provides adapters for Ignition by Inductive Automation (MQTT + REST) and Modbus TCP for direct PLC reads. Captures machine states, production counts, and downtime events.

## Supported Adapters

| Adapter | Protocol | Use Case | Data Rate |
|---------|----------|----------|-----------|
| Ignition MQTT | MQTT (Sparkplug B) | Real-time machine state, production counts | High |
| Ignition REST | HTTP REST | Historical data, tag definitions, batch data | Medium |
| Modbus TCP | Modbus TCP | Direct PLC reads, legacy equipment | Medium |

## Usage

### Connect to MES

```
mes connect --adapter ignition-mqtt --host 192.168.1.100 --port 1883
```

### Read Machine State

```
mes state --equipment EQ-001
```

### Read Production Count

```
mes count --equipment EQ-001 [--shift morning]
```

### Get Recent Events

```
mes events --equipment EQ-001 --since "2024-01-15 08:00" [--limit 100]
```

### List Available Tags

```
mes tags --equipment EQ-001 [--pattern "*temperature*"]
```

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `MES_ADAPTER` | MES adapter name (ignition-mqtt, ignition-rest, modbus) | `ignition-mqtt` |
| `MES_HOST` | MES/SCADA server hostname | `localhost` |
| `MES_PORT` | MES/SCADA server port | `1883` |
| `MES_MQTT_TOPIC_PREFIX` | MQTT topic prefix (Sparkplug B group ID) | `spBv1.0/Plant1` |
| `MES_MQTT_CLIENT_ID` | MQTT client identifier | `hermes-mes-connector` |
| `MES_REST_BASE_URL` | Ignition REST API base URL | `http://localhost:8088/api/v1` |
| `MES_REST_API_KEY` | Ignition REST API key | — |
| `MES_MODBUS_HOST` | Modbus TCP device hostname | `192.168.1.1` |
| `MES_MODBUS_PORT` | Modbus TCP port | `502` |
| `MES_MODBUS_TIMEOUT` | Modbus read timeout in seconds | `5` |
| `MES_POLL_INTERVAL` | Data poll interval in seconds | `5` |
| `MES_TAG_CACHE_TTL` | Tag cache TTL in seconds | `60` |

### Adapter-Specific Configuration

#### Ignition MQTT (Sparkplug B)

```env
MES_ADAPTER=ignition-mqtt
MES_HOST=192.168.1.100
MES_PORT=1883
MES_MQTT_TOPIC_PREFIX=spBv1.0/Plant1
MES_MQTT_CLIENT_ID=hermes-mes-connector-01
```

#### Ignition REST

```env
MES_ADAPTER=ignition-rest
MES_REST_BASE_URL=http://192.168.1.100:8088/api/v1
MES_REST_API_KEY=ignition_rest_api_key
```

#### Modbus TCP

```env
MES_ADAPTER=modbus
MES_MODBUS_HOST=192.168.1.50
MES_MODBUS_PORT=502
MES_MODBUS_TIMEOUT=5
```

## Tag Mapping

Tag mapping configuration maps MES/SCADA tags to standard manufacturing data fields.

```yaml
tag_mappings:
  - tag: "Line1/Machine1/State"
    field: "machine_state"
    type: "string"
    values:
      0: "stopped"
      1: "running"
      2: "idle"
      3: "faulted"
  - tag: "Line1/Machine1/TotalCount"
    field: "production_count"
    type: "integer"
  - tag: "Line1/Machine1/Speed"
    field: "actual_speed"
    type: "float"
    unit: "units_per_minute"
  - tag: "Line1/Machine1/FaultCode"
    field: "current_fault"
    type: "string"
```

## Scripts

### `scripts/mes-adapter-base.py`

Base adapter with connection lifecycle, error handling, and reconnection logic.

### `scripts/mes-adapter-ignition-mqtt.py`

Ignition MQTT adapter using Sparkplug B payloads with real-time subscription.

### `scripts/mes-adapter-ignition-rest.py`

Ignition REST adapter for historical data and tag definitions.

### `scripts/mes-adapter-modbus.py`

Modbus TCP adapter for direct PLC register reads with configurable register map.

### `scripts/mes-tag-poller.py`

Periodic tag poller that writes tag values to local storage or database.

## Related Skills

- [production-oee](../production-oee/SKILL.md) — Real-time production data from MES
- [maintenance-downtime](../maintenance-downtime/SKILL.md) — Automated downtime event capture
- [maintenance-pm](../maintenance-pm/SKILL.md) — Meter readings for meter-based PMs
- [erp-connector](../erp-connector/SKILL.md) — Production data cross-referenced with ERP orders

## Pitfalls

- **Network reliability**: MES systems are on the production network, which may have different reliability than the office network. Implement reconnection with exponential backoff.
- **Data volume**: High-frequency polling generates large data volumes. Use polling intervals appropriate for the data type (e.g., 1s for state changes, 60s for temperature).
- **Sparkplug B sequencing**: MQTT messages may arrive out of order. Check sequence numbers and discard stale messages.
- **Modbus register types**: Modbus has multiple register types (coils, discrete inputs, holding registers, input registers). Ensure the correct type is configured for each read.
- **Tag naming conventions**: Different engineers use different tag naming schemes. Document and standardize tag naming conventions.
- **Security**: MES/SCADA systems are on OT networks. Avoid exposing MES adapters to the internet. Use VPN or dedicated network links.
- **Time synchronization**: MES timestamps may differ from the connector's clock. Use NTP synchronization or record both source and local timestamps.