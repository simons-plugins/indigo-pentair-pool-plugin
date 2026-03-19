#! /usr/bin/env python
# -*- coding: utf-8 -*-

try:
    import indigo
except ImportError:
    pass

# nodejs-poolController heat mode values
HEAT_MODES = {
    0: indigo.kHvacMode.Off,
    1: indigo.kHvacMode.HeatOn,
    2: indigo.kHvacMode.HeatOn,
    3: indigo.kHvacMode.HeatOn,
}

HEAT_MODE_NAMES = {
    0: "Off",
    1: "Heater",
    2: "Solar Preferred",
    3: "Solar Only",
}

HEAT_STATUS_NAMES = {
    0: "Off",
    1: "Heater",
    2: "Solar",
    3: "Cooling",
}


def process_body_message(topic_parts, payload, logger):
    """Process a body state message from nodejs-poolController.
    Returns list of (body_id, state_updates) tuples.
    Special case: ("air_temp", value) for air temperature.
    """
    updates = []

    if isinstance(payload, dict):
        bodies = None
        if "bodies" in payload:
            bodies = payload["bodies"]
        elif "body" in payload:
            bodies = [payload["body"]] if isinstance(payload["body"], dict) else payload["body"]

        if bodies:
            for body in bodies:
                body_id = body.get("id")
                if body_id is None:
                    continue
                state_updates = _extract_body_states(body)
                if state_updates:
                    updates.append((body_id, state_updates))

        if "air" in payload:
            air_temp = payload["air"] if isinstance(payload["air"], (int, float)) else payload["air"].get("temp")
            if air_temp is not None:
                updates.append(("air_temp", air_temp))

    return updates


def _extract_body_states(body):
    states = []

    temp = body.get("temp")
    if temp is not None:
        states.append({"key": "temperatureInput1", "value": float(temp), "decimalPlaces": 1})

    setpoint = body.get("setPoint") or body.get("heatSetpoint")
    if setpoint is not None:
        states.append({"key": "setpointHeat", "value": float(setpoint), "decimalPlaces": 1})

    heat_mode = body.get("heatMode")
    if heat_mode is not None:
        mode_val = heat_mode.get("val") if isinstance(heat_mode, dict) else heat_mode
        if mode_val is not None:
            indigo_mode = HEAT_MODES.get(int(mode_val), indigo.kHvacMode.Off)
            states.append({"key": "hvacOperationMode", "value": indigo_mode})

    heat_status = body.get("heatStatus")
    if heat_status is not None:
        status_val = heat_status.get("val") if isinstance(heat_status, dict) else heat_status
        if status_val is not None:
            is_heating = int(status_val) > 0
            states.append({"key": "hvacHeaterIsOn", "value": is_heating})
            status_name = HEAT_STATUS_NAMES.get(int(status_val), "Off")
            states.append({"key": "heatStatus", "value": status_name})

    body_name = body.get("name", "")
    if body_name:
        body_type = "spa" if "spa" in body_name.lower() else "pool"
        states.append({"key": "bodyType", "value": body_type})

    return states


def build_set_setpoint_payload(body_id, temperature):
    return {"id": int(body_id), "setPoint": int(temperature)}


def build_set_heat_mode_payload(body_id, mode):
    return {"id": int(body_id), "mode": int(mode)}
