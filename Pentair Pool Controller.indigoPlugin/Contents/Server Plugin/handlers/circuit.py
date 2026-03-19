#! /usr/bin/env python
# -*- coding: utf-8 -*-


def process_circuit_message(topic_parts, payload, logger):
    """Process circuit state messages. Returns list of (circuit_id, state_updates) tuples."""
    updates = []

    try:
        if isinstance(payload, dict):
            circuits = [payload] if "id" in payload else []
            for circuit in circuits:
                circuit_id = circuit.get("id")
                if circuit_id is None:
                    continue
                state_updates = _extract_circuit_states(circuit, logger)
                if state_updates:
                    updates.append((circuit_id, state_updates))

        elif isinstance(payload, list):
            for circuit in payload:
                if isinstance(circuit, dict):
                    circuit_id = circuit.get("id")
                    if circuit_id is not None:
                        state_updates = _extract_circuit_states(circuit, logger)
                        if state_updates:
                            updates.append((circuit_id, state_updates))
    except Exception as err:
        logger.error(f"Error parsing circuit message: {err}")

    return updates


def _extract_circuit_states(circuit, logger=None):
    states = []

    try:
        is_on = circuit.get("isOn")
        if is_on is not None:
            states.append({"key": "onOffState", "value": bool(is_on)})
    except (ValueError, TypeError) as err:
        if logger:
            logger.debug(f"Unexpected isOn value in circuit: {err}")

    try:
        circuit_type = circuit.get("type")
        if circuit_type is not None:
            type_name = circuit_type.get("desc", "") if isinstance(circuit_type, dict) else str(circuit_type)
            states.append({"key": "circuitType", "value": type_name})
    except (ValueError, TypeError, AttributeError) as err:
        if logger:
            logger.debug(f"Unexpected type value in circuit: {err}")

    try:
        circuit_func = circuit.get("function")
        if circuit_func is not None:
            func_name = circuit_func.get("desc", "") if isinstance(circuit_func, dict) else str(circuit_func)
            states.append({"key": "circuitFunction", "value": func_name})
    except (ValueError, TypeError, AttributeError) as err:
        if logger:
            logger.debug(f"Unexpected function value in circuit: {err}")

    return states


def build_circuit_state_payload(circuit_id, is_on):
    return {"id": int(circuit_id), "isOn": "on" if is_on else "off"}
