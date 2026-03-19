#! /usr/bin/env python
# -*- coding: utf-8 -*-
####################
# Pentair Pool Controller - Indigo Plugin
# Integrates Pentair pool systems via nodejs-poolController MQTT
####################

import json
import queue
import time
from datetime import datetime

import indigo

try:
    from mqtt_handler import ThreadMqttHandler, PAHO_AVAILABLE
except ImportError:
    PAHO_AVAILABLE = False

from discovery import EquipmentDiscovery
from handlers.body import process_body_message, build_set_setpoint_payload, build_set_heat_mode_payload
from handlers.circuit import process_circuit_message, build_circuit_state_payload
from handlers.pump import process_pump_message, build_set_speed_payload, build_set_program_payload
from handlers.chlorinator import process_chlorinator_message, build_set_output_payload, build_super_chlorinate_payload
from handlers.chemistry import process_chemistry_message


class Plugin(indigo.PluginBase):

    def __init__(self, pluginId, pluginDisplayName, pluginVersion, pluginPrefs, **kwargs):
        super().__init__(pluginId, pluginDisplayName, pluginVersion, pluginPrefs, **kwargs)
        self.debug = pluginPrefs.get("showDebugInfo", False)
        self.logMqtt = pluginPrefs.get("logMqtt", False)
        self.tempUnits = pluginPrefs.get("tempUnits", "F")

        # Per-coordinator state: {dev_id: {"thread": Thread, "queue": Queue}}
        self.coordinators = {}

        # Map child devices to their coordinator: {child_dev_id: coordinator_dev_id}
        self.device_coordinator_map = {}

        self.discovery = EquipmentDiscovery(logger=self.logger)

    # -------------------------------------------------------------------------
    # Plugin lifecycle
    # -------------------------------------------------------------------------

    def startup(self):
        self.logger.info("Pentair Pool Controller starting")
        if not PAHO_AVAILABLE:
            self.logger.error(
                "paho-mqtt library not found. Ensure it is in the plugin's Packages/ directory."
            )

    def shutdown(self):
        self.logger.info("Pentair Pool Controller stopping")
        for dev_id in list(self.coordinators.keys()):
            self._stop_coordinator(dev_id)

    def runConcurrentThread(self):
        try:
            while True:
                for dev_id, coord in list(self.coordinators.items()):
                    self._drain_queue(dev_id, coord["queue"])
                self.sleep(0.1)
        except self.StopThread:
            pass

    # -------------------------------------------------------------------------
    # Device lifecycle
    # -------------------------------------------------------------------------

    def deviceStartComm(self, dev):
        if dev.deviceTypeId == "poolController":
            self._start_coordinator(dev)
        else:
            controller_id = dev.pluginProps.get("controllerId", "")
            if controller_id:
                self.device_coordinator_map[dev.id] = int(controller_id)
            self.logger.debug(f"Started child device: {dev.name}")

    def deviceStopComm(self, dev):
        if dev.deviceTypeId == "poolController":
            self._stop_coordinator(dev.id)
        else:
            self.device_coordinator_map.pop(dev.id, None)

    # -------------------------------------------------------------------------
    # Preferences
    # -------------------------------------------------------------------------

    def closedPrefsConfigUi(self, valuesDict, userCancelled):
        if not userCancelled:
            self.debug = valuesDict.get("showDebugInfo", False)
            self.logMqtt = valuesDict.get("logMqtt", False)
            self.tempUnits = valuesDict.get("tempUnits", "F")

    # -------------------------------------------------------------------------
    # Coordinator management
    # -------------------------------------------------------------------------

    def _start_coordinator(self, dev):
        if not PAHO_AVAILABLE:
            self.logger.error("Cannot start coordinator — paho-mqtt not available")
            dev.updateStateOnServer("mqttStatus", "error")
            return

        dev_id = dev.id
        props = dev.pluginProps

        msg_queue = queue.Queue()
        thread = ThreadMqttHandler(
            dev_id=dev_id,
            broker_host=props.get("brokerHost", "localhost"),
            broker_port=props.get("brokerPort", 1883),
            username=props.get("mqttUsername", ""),
            password=props.get("mqttPassword", ""),
            root_topic=props.get("rootTopic", "pool"),
            message_queue=msg_queue,
            logger=self.logger
        )

        self.coordinators[dev_id] = {
            "thread": thread,
            "queue": msg_queue,
            "root_topic": props.get("rootTopic", "pool")
        }

        dev.updateStateOnServer("mqttStatus", "connecting")
        thread.start()
        self.logger.info(f"Starting MQTT connection for {dev.name}")

    def _stop_coordinator(self, dev_id):
        coord = self.coordinators.pop(dev_id, None)
        if coord and coord["thread"].is_alive():
            coord["thread"].stop()
            coord["thread"].join(timeout=5)
            self.logger.debug(f"Stopped MQTT handler for coordinator {dev_id}")

    # -------------------------------------------------------------------------
    # Message processing
    # -------------------------------------------------------------------------

    def _drain_queue(self, coordinator_dev_id, msg_queue):
        while not msg_queue.empty():
            try:
                msg = msg_queue.get_nowait()
            except queue.Empty:
                break

            msg_type = msg.get("type")

            if msg_type == "connection_status":
                self._handle_connection_status(msg)
            elif msg_type == "mqtt_message":
                self._handle_mqtt_message(coordinator_dev_id, msg)

    def _handle_connection_status(self, msg):
        dev_id = msg["dev_id"]
        status = msg["status"]
        try:
            dev = indigo.devices[dev_id]
            dev.updateStateOnServer("mqttStatus", status)
            if status == "connected":
                dev.updateStateImageOnServer(indigo.kStateImageSel.SensorOn)
            else:
                dev.updateStateImageOnServer(indigo.kStateImageSel.SensorOff)
        except KeyError:
            pass

    def _handle_mqtt_message(self, coordinator_dev_id, msg):
        topic = msg["topic"]
        topic_parts = msg["topic_parts"]
        payload = msg["payload"]

        if self.logMqtt:
            self.logger.debug(f"MQTT [{msg['sequence']}]: {topic} = {payload}")

        # Update lastMessage timestamp on coordinator
        try:
            dev = indigo.devices[coordinator_dev_id]
            dev.updateStateOnServer("lastMessage", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        except KeyError:
            pass

        # Route based on topic structure: {root}/state/{category}/...
        if len(topic_parts) < 3:
            return

        self._route_message(coordinator_dev_id, topic_parts, payload)

    def _route_message(self, coordinator_dev_id, topic_parts, payload):
        """Route an MQTT message to the appropriate handler."""
        if len(topic_parts) < 3:
            return

        # Feed all messages to discovery
        new_equip = self.discovery.process_message(coordinator_dev_id, topic_parts, payload)
        for equip in new_equip:
            self.logger.info(
                f"Discovered {equip['type']}: {equip['name']} (ID {equip['id']})"
            )

        category = topic_parts[1] if len(topic_parts) > 1 else ""
        subcategory = topic_parts[2] if len(topic_parts) > 2 else ""

        if category == "state":
            if subcategory == "temps":
                self._process_body_updates(coordinator_dev_id, topic_parts, payload)
            elif subcategory == "circuits":
                self._process_circuit_updates(coordinator_dev_id, topic_parts, payload)
            elif subcategory == "pumps":
                self._process_pump_updates(coordinator_dev_id, topic_parts, payload)
            elif subcategory == "chlorinators":
                self._process_chlorinator_updates(coordinator_dev_id, topic_parts, payload)
            elif subcategory == "chemControllers":
                self._process_chemistry_updates(coordinator_dev_id, topic_parts, payload)

    def _process_body_updates(self, coordinator_dev_id, topic_parts, payload):
        updates = process_body_message(topic_parts, payload, self.logger)
        for item in updates:
            if item[0] == "air_temp":
                try:
                    dev = indigo.devices[coordinator_dev_id]
                    dev.updateStateOnServer("airTemp", item[1])
                except KeyError:
                    pass
                continue
            body_id, state_updates = item
            target_dev = self._find_child_device(coordinator_dev_id, "poolBody", "bodyId", str(body_id))
            if target_dev and state_updates:
                target_dev.updateStatesOnServer(state_updates)

    def _process_circuit_updates(self, coordinator_dev_id, topic_parts, payload):
        updates = process_circuit_message(topic_parts, payload, self.logger)
        for circuit_id, state_updates in updates:
            target_dev = self._find_child_device(coordinator_dev_id, "poolCircuit", "circuitId", str(circuit_id))
            if target_dev and state_updates:
                target_dev.updateStatesOnServer(state_updates)

    def _process_pump_updates(self, coordinator_dev_id, topic_parts, payload):
        updates = process_pump_message(topic_parts, payload, self.logger)
        for pump_id, state_updates in updates:
            target_dev = self._find_child_device(coordinator_dev_id, "poolPump", "pumpId", str(pump_id))
            if target_dev and state_updates:
                target_dev.updateStatesOnServer(state_updates)

    def _process_chlorinator_updates(self, coordinator_dev_id, topic_parts, payload):
        updates = process_chlorinator_message(topic_parts, payload, self.logger)
        for chlor_id, state_updates in updates:
            target_dev = self._find_child_device(coordinator_dev_id, "poolChlorinator", "chlorinatorId", str(chlor_id))
            if target_dev and state_updates:
                target_dev.updateStatesOnServer(state_updates)

    def _process_chemistry_updates(self, coordinator_dev_id, topic_parts, payload):
        updates = process_chemistry_message(topic_parts, payload, self.logger)
        for chem_id, state_updates in updates:
            target_dev = self._find_child_device(coordinator_dev_id, "poolChemistry", "chemControllerId", str(chem_id))
            if target_dev and state_updates:
                target_dev.updateStatesOnServer(state_updates)

    # -------------------------------------------------------------------------
    # Thermostat actions
    # -------------------------------------------------------------------------

    def actionControlThermostat(self, action, dev):
        coordinator_id = int(dev.pluginProps.get("controllerId", 0))
        body_id = dev.pluginProps.get("bodyId", "1")

        if action.thermostatAction == indigo.kThermostatAction.SetHeatSetpoint:
            new_setpoint = action.actionValue
            payload = build_set_setpoint_payload(body_id, new_setpoint)
            self._publish(coordinator_id, "state/body/setPoint", payload)
            self.logger.info(f"Set {dev.name} heat setpoint to {new_setpoint}")

        elif action.thermostatAction == indigo.kThermostatAction.SetHvacMode:
            mode_map = {
                indigo.kHvacMode.Off: 0,
                indigo.kHvacMode.HeatOn: 1,
            }
            njspc_mode = mode_map.get(action.actionValue, 0)
            payload = build_set_heat_mode_payload(body_id, njspc_mode)
            self._publish(coordinator_id, "state/body/heatMode", payload)

        elif action.thermostatAction == indigo.kThermostatAction.RequestStatusAll:
            self.logger.debug(f"Status request for {dev.name} — updated via MQTT")

    # -------------------------------------------------------------------------
    # Relay actions (circuits)
    # -------------------------------------------------------------------------

    def actionControlDevice(self, action, dev):
        if dev.deviceTypeId != "poolCircuit":
            return

        coordinator_id = int(dev.pluginProps.get("controllerId", 0))
        circuit_id = dev.pluginProps.get("circuitId", "")

        if action.deviceAction == indigo.kDeviceAction.TurnOn:
            payload = build_circuit_state_payload(circuit_id, True)
            self._publish(coordinator_id, "state/circuits/setState", payload)
        elif action.deviceAction == indigo.kDeviceAction.TurnOff:
            payload = build_circuit_state_payload(circuit_id, False)
            self._publish(coordinator_id, "state/circuits/setState", payload)
        elif action.deviceAction == indigo.kDeviceAction.Toggle:
            new_state = not dev.onState
            payload = build_circuit_state_payload(circuit_id, new_state)
            self._publish(coordinator_id, "state/circuits/setState", payload)

    # -------------------------------------------------------------------------
    # Custom actions (pump, chlorinator)
    # -------------------------------------------------------------------------

    def setPumpSpeed(self, action):
        dev = indigo.devices[action.deviceId]
        coordinator_id = int(dev.pluginProps.get("controllerId", 0))
        pump_id = dev.pluginProps.get("pumpId", "1")
        rpm = action.props.get("rpm", 2400)
        payload = build_set_speed_payload(pump_id, rpm)
        self._publish(coordinator_id, "state/pumps/setSpeed", payload)
        self.logger.info(f"Set {dev.name} speed to {rpm} RPM")

    def setPumpProgram(self, action):
        dev = indigo.devices[action.deviceId]
        coordinator_id = int(dev.pluginProps.get("controllerId", 0))
        pump_id = dev.pluginProps.get("pumpId", "1")
        program = action.props.get("program", 1)
        payload = build_set_program_payload(pump_id, program)
        self._publish(coordinator_id, "state/pumps/setProgram", payload)
        self.logger.info(f"Set {dev.name} to program {program}")

    def setChlorinatorOutput(self, action):
        dev = indigo.devices[action.deviceId]
        coordinator_id = int(dev.pluginProps.get("controllerId", 0))
        chlor_id = dev.pluginProps.get("chlorinatorId", "1")
        percent = action.props.get("percent", 50)
        payload = build_set_output_payload(chlor_id, percent)
        self._publish(coordinator_id, "state/chlorinator", payload)
        self.logger.info(f"Set {dev.name} output to {percent}%")

    def setSuperChlorinate(self, action):
        dev = indigo.devices[action.deviceId]
        coordinator_id = int(dev.pluginProps.get("controllerId", 0))
        chlor_id = dev.pluginProps.get("chlorinatorId", "1")
        enabled = action.props.get("enabled", True)
        payload = build_super_chlorinate_payload(chlor_id, enabled)
        self._publish(coordinator_id, "state/chlorinator", payload)
        self.logger.info(f"{'Enabled' if enabled else 'Disabled'} super chlorinate on {dev.name}")

    # -------------------------------------------------------------------------
    # Menu items
    # -------------------------------------------------------------------------

    def discoverEquipment(self):
        self.logger.info("Equipment discovery — listening for MQTT messages...")
        self.logger.info("Create devices via Indigo's device dialog using the discovered IDs.")
        for dev_id in self.coordinators:
            try:
                dev = indigo.devices[dev_id]
                self.logger.info(f"Coordinator: {dev.name}")
                self.logger.info(self.discovery.get_summary(dev_id))
            except KeyError:
                pass

    def showDiscoveredEquipment(self):
        self.discoverEquipment()

    # -------------------------------------------------------------------------
    # Helper: find child device
    # -------------------------------------------------------------------------

    def _find_child_device(self, coordinator_dev_id, device_type_id, prop_key, prop_value):
        """Find a child device by type and property value."""
        for dev in indigo.devices.iter(f"self.{device_type_id}"):
            props = dev.pluginProps
            if (props.get("controllerId") == str(coordinator_dev_id) and
                    props.get(prop_key) == prop_value):
                return dev
        return None

    def getControllerList(self, filter="", valuesDict=None, typeId="", targetId=0):
        """Return list of pool controller devices for config UI menus."""
        controllers = []
        for dev in indigo.devices.iter("self.poolController"):
            controllers.append((str(dev.id), dev.name))
        return controllers

    # -------------------------------------------------------------------------
    # MQTT publishing helper
    # -------------------------------------------------------------------------

    def _publish(self, coordinator_dev_id, topic, payload):
        coord = self.coordinators.get(coordinator_dev_id)
        if coord:
            coord["thread"].publish(topic, payload)
