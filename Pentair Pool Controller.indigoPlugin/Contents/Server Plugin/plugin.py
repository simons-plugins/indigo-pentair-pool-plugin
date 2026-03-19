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

        category = topic_parts[1] if len(topic_parts) > 1 else ""
        subcategory = topic_parts[2] if len(topic_parts) > 2 else ""

        # TODO: Handler routing will be added in subsequent tasks

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
