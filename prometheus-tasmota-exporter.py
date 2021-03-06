#!/usr/bin/env python
# -*- coding: utf-8 -*-

import json
import time
from datetime import datetime, timedelta
from systemd.journal import JournaldLogHandler
import logging
import pyjq
import urllib2
from prometheus_client import start_http_server
from prometheus_client.core import GaugeMetricFamily, StateSetMetricFamily, REGISTRY

logger = logging.getLogger(__name__)
journald_handler = JournaldLogHandler()
journald_handler.setFormatter(logging.Formatter(
    '[%(levelname)s] %(message)s'
))
logger.addHandler(journald_handler)
logger.setLevel(logging.DEBUG)

statusQuery = '.StatusSTS | to_entries | map(select(.key | match("^POWER";"i"))) | map({key: .key, value: .value | test("ON") }) | from_entries'
energyQuery = '.StatusSNS | select(.ENERGY) | .ENERGY | to_entries | map(select( .key == "Total" or .key == "Yesterday" or .key == "Today")) | from_entries'
energyQuery = '.StatusSNS.ENERGY.Total'
powerQuery = '.StatusSNS.ENERGY.Power'
voltageQuery = '.StatusSNS.ENERGY.Voltage'
currentQuery = '.StatusSNS.ENERGY.Current'
powerSupplyQuery = '.StatusSTS.Vcc'
uptimeQuery = '.StatusSTS.Uptime'


class TasmotaCollector(object):

    def __init__(self, urls):
        self.urls = urls

    def collect(self):
        for u in self.urls:
            try:
                logger.info("Requesting JSON for %s" % u)
                data = json.load(urllib2.urlopen(
                    "http://%s/cm?cmnd=status%%200" % u))
                tmp = self._collectStatus(u, data)
                if tmp:
                    yield tmp
                tmp = self._collectEnergy(u, data)
                if tmp:
                    yield tmp
                tmp = self._collectPower(u, data)
                if tmp:
                    yield tmp
                tmp = self._collectVoltage(u, data)
                if tmp:
                    yield tmp
                tmp = self._collectPowerSupply(u, data)
                if tmp:
                    yield tmp
                tmp = self._collectUptime(u, data)
                if tmp:
                    yield tmp
            except Exception as e:
                logger.error("%s: %s", u, e)

    def _collectStatus(self, node, data):
        metric = StateSetMetricFamily(
            'switch_state',
            'State of switches',
            labels=["node", "domain"])
        result = pyjq.first(statusQuery, data)
        logger.info("Statuses: %s" % result)
        metric.add_metric(
            [node, "switch"], result)
        return metric

    def _collectEnergy(self, node, data):
        result = pyjq.first(energyQuery, data)
        logger.info("Energy: %s" % result)
        if result != None:
            metric = GaugeMetricFamily('energy', 'Energy reported by sensor',
                                       labels=["node", "domain", "type", "unit"])
            metric.add_metric([node, "sensor", "energy", "kWh"], result)
            return metric

    def _collectPower(self, node, data):
        result = pyjq.first(powerQuery, data)
        logger.info("Power: %s" % result)
        if result != None:
            metric = GaugeMetricFamily('power', 'Power reported by sensor',
                                       labels=["node", "domain", "type", "unit"])
            metric.add_metric([node, "sensor", "power", "W"], result)
            return metric

    def _collectVoltage(self, node, data):
        result = pyjq.first(voltageQuery, data)
        logger.info("Voltage: %s" % result)
        if result != None:
            metric = GaugeMetricFamily(
                'voltage',
                'Voltage reported by sensor',
                labels=["node", "domain", "type", "unit"])
            metric.add_metric(
                [node, "sensor", "voltage", "V"], result)
            return metric

    def _collectCurrent(self, node, data):
        result = pyjq.first(currentQuery, data)
        logger.info("Current: %s" % result)
        if result != None:
            metric = GaugeMetricFamily(
                'current',
                'Current reported by sensor',
                labels=["node", "domain", "type", "unit"])
            metric.add_metric(
                [node, "sensor", "current", "A"], result)
            return metric

    def _collectPowerSupply(self, node, data):
        result = pyjq.first(powerSupplyQuery, data)
        logger.info("Power supply: %s" % result)
        if result != None:
            metric = GaugeMetricFamily(
                'esp_power_supply',
                'Voltage provided to ESP module',
                labels=["node", "domain", "type", "unit"])
            metric.add_metric(
                [node, "sensor", "voltage", "V"], result)
            return metric

    def _collectUptime(self, node, data):
        result = pyjq.first(uptimeQuery, data)
        logger.info("Power supply: %s" % result)
        if result != None:
            (d, t) = result.split('T')
            t = datetime.strptime(t, '%H:%M:%S')
            td = timedelta(days=int(d), hours = t.hour, minutes = t.minute, seconds =t.second)
            metric = GaugeMetricFamily(
                'uptime',
                'Voltage provided to ESP module',
                labels=["node", "domain", "type", "unit"])
            metric.add_metric(
                [node, "sensor", "time", "s"], td.total_seconds())
            return metric


if __name__ == "__main__":
    REGISTRY.register(TasmotaCollector(
        ["albohes-1.home", "sonoff-pow-1.home"]))
    start_http_server(9118)
    while True:
        time.sleep(1)
