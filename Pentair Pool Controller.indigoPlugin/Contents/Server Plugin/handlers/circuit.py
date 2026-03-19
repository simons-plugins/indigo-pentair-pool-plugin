#! /usr/bin/env python
# -*- coding: utf-8 -*-


def process_circuit_message(topic_parts, payload, logger):
    """Process circuit state messages. Returns list of (circuit_id, state_updates) tuples."""
    updates = []

    if isinstance(payload, dict):
        circuits = [payload] if "id" in payload else []
        for circuit in circuits:
            circuit_id = circuit.get("id")
            if circuit_id is None:
                continue
            state_updates = _extract_circuit_states(circuit)
            if state_updates:
                updates.append((circuit_id, state_updates))

    elif isinstance(payload, list):
        for circuit in payload:
            if isinstance(circuit, dict):
                circuit_id = circuit.get("id")
                if circuit_id is not None:
                    state_updates = _extract_circuit_states(circuit)
                    if state_updates:
                        updates.append((circuit_id, state_updates))

    return updates


def _extract_circuit_states(circuit):
    states = []

    is_on = circuit.get("isOn")
    if is_on is not None:
        states.append({"key": "onOffState", "value": bool(is_on)})

    circuit_type = circuit.get("type")
    if circuit_type is not None:
        type_name = circuit_type.get("desc", "") if isinstance(circuit_type, dict) else str(circuit_type)
        states.append({"key": "circuitType", "value": type_name})

    circuit_func = circuit.get("function")
    if circuit_func is not None:
        func_name = circuit_func.get("desc", "") if isinstance(circuit_func, dict) else str(circuit_func)
        states.append({"key": "circuitFunction", "value": func_name})

    return states


def build_circuit_state_payload(circuit_id, is_on):
    return {"id": int(circuit_id), "isOn": "on" if is_on else "off"}
