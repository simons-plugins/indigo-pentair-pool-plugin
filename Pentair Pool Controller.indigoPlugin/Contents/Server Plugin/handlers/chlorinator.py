#! /usr/bin/env python
# -*- coding: utf-8 -*-


def process_chlorinator_message(topic_parts, payload, logger):
    """Process chlorinator state messages. Returns list of (chlorinator_id, state_updates) tuples."""
    updates = []

    if isinstance(payload, dict):
        chlorinators = [payload] if "id" in payload else []
        for chlor in chlorinators:
            chlor_id = chlor.get("id")
            if chlor_id is None:
                continue
            state_updates = _extract_chlorinator_states(chlor)
            if state_updates:
                updates.append((chlor_id, state_updates))

    elif isinstance(payload, list):
        for chlor in payload:
            if isinstance(chlor, dict):
                chlor_id = chlor.get("id")
                if chlor_id is not None:
                    state_updates = _extract_chlorinator_states(chlor)
                    if state_updates:
                        updates.append((chlor_id, state_updates))

    return updates


def _extract_chlorinator_states(chlor):
    states = []

    is_on = chlor.get("isOn")
    if is_on is not None:
        states.append({"key": "status", "value": "on" if is_on else "off"})

    salt = chlor.get("saltLevel")
    if salt is not None:
        states.append({"key": "saltPPM", "value": int(salt)})

    current_output = chlor.get("currentOutput")
    if current_output is not None:
        states.append({"key": "outputPercent", "value": int(current_output)})

    pool_setpoint = chlor.get("poolSetpoint")
    if pool_setpoint is not None:
        states.append({"key": "targetOutput", "value": int(pool_setpoint)})

    super_chlor = chlor.get("superChlor") or chlor.get("superChlorinate")
    if super_chlor is not None:
        states.append({"key": "superChlorinate", "value": bool(super_chlor)})

    status = chlor.get("status")
    if status is not None:
        status_val = status.get("val") if isinstance(status, dict) else status
        if status_val is not None and int(status_val) > 0:
            states.append({"key": "status", "value": "error"})

    return states


def build_set_output_payload(chlorinator_id, percent):
    return {"id": int(chlorinator_id), "poolSetpoint": int(percent)}


def build_super_chlorinate_payload(chlorinator_id, enabled):
    return {"id": int(chlorinator_id), "superChlorinate": bool(enabled)}
