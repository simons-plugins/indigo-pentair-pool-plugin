#! /usr/bin/env python
# -*- coding: utf-8 -*-
####################
# Pentair Pool Controller - Indigo Plugin
# Integrates Pentair pool systems via nodejs-poolController MQTT
####################

import indigo


class Plugin(indigo.PluginBase):

    def __init__(self, pluginId, pluginDisplayName, pluginVersion, pluginPrefs, **kwargs):
        super().__init__(pluginId, pluginDisplayName, pluginVersion, pluginPrefs, **kwargs)
        self.debug = pluginPrefs.get("showDebugInfo", False)
        self.logMqtt = pluginPrefs.get("logMqtt", False)

    def startup(self):
        self.logger.info("Pentair Pool Controller starting")

    def shutdown(self):
        self.logger.info("Pentair Pool Controller stopping")

    def deviceStartComm(self, dev):
        self.logger.info(f"Starting device: {dev.name}")

    def deviceStopComm(self, dev):
        self.logger.info(f"Stopping device: {dev.name}")

    def closedPrefsConfigUi(self, valuesDict, userCancelled):
        if not userCancelled:
            self.debug = valuesDict.get("showDebugInfo", False)
            self.logMqtt = valuesDict.get("logMqtt", False)
