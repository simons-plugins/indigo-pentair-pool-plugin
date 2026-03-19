#! /usr/bin/env python
# -*- coding: utf-8 -*-


def process_pump_message(topic_parts, payload, logger):
    """Process pump state messages. Returns list of (pump_id, state_updates) tuples."""
    updates = []

    try:
        if isinstance(payload, dict):
            pumps = [payload] if "id" in payload else []
            for pump in pumps:
                pump_id = pump.get("id")
                if pump_id is None:
                    continue
                state_updates = _extract_pump_states(pump, logger)
                if state_updates:
                    updates.append((pump_id, state_updates))

        elif isinstance(payload, list):
            for pump in payload:
                if isinstance(pump, dict):
                    pump_id = pump.get("id")
                    if pump_id is not None:
                        state_updates = _extract_pump_states(pump, logger)
                        if state_updates:
                            updates.append((pump_id, state_updates))
    except Exception as err:
        logger.error(f"Error parsing pump message: {err}")

    return updates


def _extract_pump_states(pump, logger=None):
    states = []

    try:
        rpm = pump.get("rpm")
        if rpm is not None:
            states.append({"key": "rpm", "value": int(rpm)})
            states.append({"key": "status", "value": "on" if int(rpm) > 0 else "off"})
    except (ValueError, TypeError) as err:
        if logger:
            logger.debug(f"Unexpected rpm value in pump: {err}")

    try:
        watts = pump.get("watts")
        if watts is not None:
            states.append({"key": "watts", "value": int(watts)})
    except (ValueError, TypeError) as err:
        if logger:
            logger.debug(f"Unexpected watts value in pump: {err}")

    try:
        gpm = pump.get("gpm") or pump.get("flow")
        if gpm is not None:
            states.append({"key": "gpm", "value": float(gpm), "decimalPlaces": 1})
    except (ValueError, TypeError) as err:
        if logger:
            logger.debug(f"Unexpected gpm value in pump: {err}")

    try:
        pump_type = pump.get("type")
        if pump_type is not None:
            type_name = pump_type.get("desc", "") if isinstance(pump_type, dict) else str(pump_type)
            states.append({"key": "pumpType", "value": type_name})
    except (ValueError, TypeError, AttributeError) as err:
        if logger:
            logger.debug(f"Unexpected type value in pump: {err}")

    try:
        program = pump.get("currentProgram") or pump.get("program")
        if program is not None:
            states.append({"key": "program", "value": int(program)})
    except (ValueError, TypeError) as err:
        if logger:
            logger.debug(f"Unexpected program value in pump: {err}")

    return states


def build_set_speed_payload(pump_id, rpm):
    return {"id": int(pump_id), "speed": int(rpm)}


def build_set_program_payload(pump_id, program):
    return {"id": int(pump_id), "program": int(program)}
