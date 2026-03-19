#! /usr/bin/env python
# -*- coding: utf-8 -*-

import logging


class EquipmentDiscovery:
    """Tracks discovered pool equipment from MQTT messages."""

    def __init__(self, logger=None):
        self.logger = logger or logging.getLogger("Plugin.Discovery")
        self.discovered = {}

    def process_message(self, coordinator_dev_id, topic_parts, payload):
        """Process an MQTT message and extract equipment discovery info.
        Returns list of newly discovered equipment dicts, or empty list.
        """
        if coordinator_dev_id not in self.discovered:
            self.discovered[coordinator_dev_id] = {
                "bodies": {},
                "circuits": {},
                "pumps": {},
                "chlorinators": {},
                "chemControllers": {},
            }

        coord_equip = self.discovered[coordinator_dev_id]
        new_equipment = []

        if not isinstance(payload, (dict, list)):
            return new_equipment

        if len(topic_parts) >= 3 and topic_parts[1] == "state":
            subcategory = topic_parts[2]

            if subcategory == "temps" and isinstance(payload, dict):
                bodies = payload.get("bodies", [])
                for body in bodies:
                    body_id = body.get("id")
                    if body_id and body_id not in coord_equip["bodies"]:
                        name = body.get("name", f"Body {body_id}")
                        coord_equip["bodies"][body_id] = {"name": name, "id": body_id}
                        new_equipment.append({"type": "poolBody", "id": body_id, "name": name})

            elif subcategory == "circuits" and isinstance(payload, (dict, list)):
                circuits = [payload] if isinstance(payload, dict) else payload
                for circuit in circuits:
                    if not isinstance(circuit, dict):
                        continue
                    circuit_id = circuit.get("id")
                    if circuit_id and circuit_id not in coord_equip["circuits"]:
                        name = circuit.get("name", f"Circuit {circuit_id}")
                        coord_equip["circuits"][circuit_id] = {"name": name, "id": circuit_id}
                        new_equipment.append({"type": "poolCircuit", "id": circuit_id, "name": name})

            elif subcategory == "pumps" and isinstance(payload, (dict, list)):
                pumps = [payload] if isinstance(payload, dict) else payload
                for pump in pumps:
                    if not isinstance(pump, dict):
                        continue
                    pump_id = pump.get("id")
                    if pump_id and pump_id not in coord_equip["pumps"]:
                        name = pump.get("name", f"Pump {pump_id}")
                        coord_equip["pumps"][pump_id] = {"name": name, "id": pump_id}
                        new_equipment.append({"type": "poolPump", "id": pump_id, "name": name})

            elif subcategory == "chlorinators" and isinstance(payload, (dict, list)):
                chlors = [payload] if isinstance(payload, dict) else payload
                for chlor in chlors:
                    if not isinstance(chlor, dict):
                        continue
                    chlor_id = chlor.get("id")
                    if chlor_id and chlor_id not in coord_equip["chlorinators"]:
                        name = chlor.get("name", f"Chlorinator {chlor_id}")
                        coord_equip["chlorinators"][chlor_id] = {"name": name, "id": chlor_id}
                        new_equipment.append({"type": "poolChlorinator", "id": chlor_id, "name": name})

            elif subcategory == "chemControllers" and isinstance(payload, (dict, list)):
                chems = [payload] if isinstance(payload, dict) else payload
                for chem in chems:
                    if not isinstance(chem, dict):
                        continue
                    chem_id = chem.get("id")
                    if chem_id and chem_id not in coord_equip["chemControllers"]:
                        name = chem.get("name", f"Chemistry {chem_id}")
                        coord_equip["chemControllers"][chem_id] = {"name": name, "id": chem_id}
                        new_equipment.append({"type": "poolChemistry", "id": chem_id, "name": name})

        return new_equipment

    def get_summary(self, coordinator_dev_id):
        """Return a formatted summary of discovered equipment."""
        equip = self.discovered.get(coordinator_dev_id, {})
        lines = []
        for category, items in equip.items():
            if items:
                lines.append(f"  {category}:")
                for item_id, info in sorted(items.items()):
                    lines.append(f"    ID {item_id}: {info['name']}")
        return "\n".join(lines) if lines else "  No equipment discovered yet."
