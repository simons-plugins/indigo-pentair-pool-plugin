#! /usr/bin/env python
# -*- coding: utf-8 -*-


def process_chlorinator_message(topic_parts, payload, logger):
    """Process chlorinator state messages. Returns list of (chlorinator_id, state_updates) tuples."""
    updates = []

    try:
        if isinstance(payload, dict):
            chlorinators = [payload] if "id" in payload else []
            for chlor in chlorinators:
                chlor_id = chlor.get("id")
                if chlor_id is None:
                    continue
                state_updates = _extract_chlorinator_states(chlor, logger)
                if state_updates:
                    updates.append((chlor_id, state_updates))

        elif isinstance(payload, list):
            for chlor in payload:
                if isinstance(chlor, dict):
                    chlor_id = chlor.get("id")
                    if chlor_id is not None:
                        state_updates = _extract_chlorinator_states(chlor, logger)
                        if state_updates:
                            updates.append((chlor_id, state_updates))
    except Exception as err:
        logger.error(f"Error parsing chlorinator message: {err}")

    return updates


def _extract_chlorinator_states(chlor, logger=None):
    states = []

    try:
        is_on = chlor.get("isOn")
        if is_on is not None:
            states.append({"key": "status", "value": "on" if is_on else "off"})
    except (ValueError, TypeError) as err:
        if logger:
            logger.debug(f"Unexpected isOn value in chlorinator: {err}")

    try:
        salt = chlor.get("saltLevel")
        if salt is not None:
            states.append({"key": "saltPPM", "value": int(salt)})
    except (ValueError, TypeError) as err:
        if logger:
            logger.debug(f"Unexpected saltLevel value in chlorinator: {err}")

    try:
        current_output = chlor.get("currentOutput")
        if current_output is not None:
            states.append({"key": "outputPercent", "value": int(current_output)})
    except (ValueError, TypeError) as err:
        if logger:
            logger.debug(f"Unexpected currentOutput value in chlorinator: {err}")

    try:
        pool_setpoint = chlor.get("poolSetpoint")
        if pool_setpoint is not None:
            states.append({"key": "targetOutput", "value": int(pool_setpoint)})
    except (ValueError, TypeError) as err:
        if logger:
            logger.debug(f"Unexpected poolSetpoint value in chlorinator: {err}")

    try:
        super_chlor = chlor.get("superChlor") or chlor.get("superChlorinate")
        if super_chlor is not None:
            states.append({"key": "superChlorinate", "value": bool(super_chlor)})
    except (ValueError, TypeError) as err:
        if logger:
            logger.debug(f"Unexpected superChlor value in chlorinator: {err}")

    try:
        status = chlor.get("status")
        if status is not None:
            status_val = status.get("val") if isinstance(status, dict) else status
            if status_val is not None and int(status_val) > 0:
                states.append({"key": "status", "value": "error"})
    except (ValueError, TypeError, AttributeError) as err:
        if logger:
            logger.debug(f"Unexpected status value in chlorinator: {err}")

    return states


def build_set_output_payload(chlorinator_id, percent):
    return {"id": int(chlorinator_id), "poolSetpoint": int(percent)}


def build_super_chlorinate_payload(chlorinator_id, enabled):
    return {"id": int(chlorinator_id), "superChlorinate": bool(enabled)}
