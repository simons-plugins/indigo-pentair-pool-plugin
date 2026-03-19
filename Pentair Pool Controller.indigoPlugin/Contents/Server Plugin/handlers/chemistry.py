#! /usr/bin/env python
# -*- coding: utf-8 -*-


def process_chemistry_message(topic_parts, payload, logger):
    """Process chemistry controller state messages. Returns list of (chem_id, state_updates) tuples."""
    updates = []

    if isinstance(payload, dict):
        controllers = [payload] if "id" in payload else []
        for chem in controllers:
            chem_id = chem.get("id")
            if chem_id is None:
                continue
            state_updates = _extract_chemistry_states(chem)
            if state_updates:
                updates.append((chem_id, state_updates))

    elif isinstance(payload, list):
        for chem in payload:
            if isinstance(chem, dict):
                chem_id = chem.get("id")
                if chem_id is not None:
                    state_updates = _extract_chemistry_states(chem)
                    if state_updates:
                        updates.append((chem_id, state_updates))

    return updates


def _extract_chemistry_states(chem):
    states = []

    ph_level = chem.get("pHLevel")
    if ph_level is not None:
        states.append({"key": "pH", "value": float(ph_level), "decimalPlaces": 2})
        states.append({"key": "sensorValue", "value": float(ph_level), "decimalPlaces": 2})

    ph_setpoint = chem.get("pHSetpoint")
    if ph_setpoint is not None:
        states.append({"key": "pHSetpoint", "value": float(ph_setpoint), "decimalPlaces": 1})

    orp_level = chem.get("orpLevel")
    if orp_level is not None:
        states.append({"key": "orp", "value": int(orp_level)})

    orp_setpoint = chem.get("orpSetpoint")
    if orp_setpoint is not None:
        states.append({"key": "orpSetpoint", "value": int(orp_setpoint)})

    si = chem.get("saturationIndex")
    if si is not None:
        states.append({"key": "saturationIndex", "value": float(si), "decimalPlaces": 2})

    acid_tank = chem.get("acidTankLevel")
    if acid_tank is not None:
        states.append({"key": "acidTankLevel", "value": int(acid_tank)})

    base_tank = chem.get("baseTankLevel") or chem.get("orpTankLevel")
    if base_tank is not None:
        states.append({"key": "baseTankLevel", "value": int(base_tank)})

    return states
