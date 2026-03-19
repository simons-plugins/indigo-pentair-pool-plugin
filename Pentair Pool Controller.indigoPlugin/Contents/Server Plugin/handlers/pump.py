#! /usr/bin/env python
# -*- coding: utf-8 -*-


def process_pump_message(topic_parts, payload, logger):
    """Process pump state messages. Returns list of (pump_id, state_updates) tuples."""
    updates = []

    if isinstance(payload, dict):
        pumps = [payload] if "id" in payload else []
        for pump in pumps:
            pump_id = pump.get("id")
            if pump_id is None:
                continue
            state_updates = _extract_pump_states(pump)
            if state_updates:
                updates.append((pump_id, state_updates))

    elif isinstance(payload, list):
        for pump in payload:
            if isinstance(pump, dict):
                pump_id = pump.get("id")
                if pump_id is not None:
                    state_updates = _extract_pump_states(pump)
                    if state_updates:
                        updates.append((pump_id, state_updates))

    return updates


def _extract_pump_states(pump):
    states = []

    rpm = pump.get("rpm")
    if rpm is not None:
        states.append({"key": "rpm", "value": int(rpm)})
        states.append({"key": "status", "value": "on" if int(rpm) > 0 else "off"})

    watts = pump.get("watts")
    if watts is not None:
        states.append({"key": "watts", "value": int(watts)})

    gpm = pump.get("gpm") or pump.get("flow")
    if gpm is not None:
        states.append({"key": "gpm", "value": float(gpm), "decimalPlaces": 1})

    pump_type = pump.get("type")
    if pump_type is not None:
        type_name = pump_type.get("desc", "") if isinstance(pump_type, dict) else str(pump_type)
        states.append({"key": "pumpType", "value": type_name})

    program = pump.get("currentProgram") or pump.get("program")
    if program is not None:
        states.append({"key": "program", "value": int(program)})

    return states


def build_set_speed_payload(pump_id, rpm):
    return {"id": int(pump_id), "speed": int(rpm)}


def build_set_program_payload(pump_id, program):
    return {"id": int(pump_id), "program": int(program)}
