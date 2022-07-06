#!/usr/bin/python
# -*- coding: utf-8 -*-

# Licensed under the MIT license:
# http://www.opensource.org/licenses/mit-license
# Copyright (c) 2017 Simon Effenberg <savar@schuldeigen.de>
# Copyright (c) 2017 Thumbor Community Extensions

from prometheus_client import Counter, start_http_server, Summary
from thumbor.metrics import BaseMetrics


class Metrics(BaseMetrics):

    def __init__(self, config):
        super().__init__(config)

        if not hasattr(Metrics, 'http_server_started'):
            port = config.PROMETHEUS_SCRAPE_PORT
            if isinstance(port, str):
                port = int(port)
            start_http_server(port)
            Metrics.http_server_started = True
            Metrics.counters = {}
            Metrics.summaries = {}

        # hard coded mapping right now
        self.mapping = {
                'response.status': ['statuscode'],
                'response.format': ['extension'],
                'response.bytes': ['extension'],
                'response.time': ['statuscode_extension'],
                'original_image.status': ['statuscode', 'networklocation'],
                # When https://github.com/thumbor-community/prometheus/issues/9 is resolved,
                # replace two lines below with
                # 'original_image.fetch': ['statuscode', 'networklocation'],
                'original_image.fetch.count': ['statuscode', 'networklocation'], 
                'original_image.fetch.latency': ['statuscode', 'networklocation'], # Remove when https://github.com/thumbor-community/prometheus/issues/9 is resolved
        }

    def incr(self, metricname, value=1):
        # Remove monkey patches below when https://github.com/thumbor-community/prometheus/issues/9 is resolved
        if (metricname == "response.smart"):
            metricname = "response.smart.count"
        if (metricname == "response.none_smart"):
            metricname = "response.none_smart.count"
        if (metricname.startswith("original_image.fetch.")):
            metricname = metricname.replace("original_image.fetch.", "original_image.fetch.counter.")

        name, labels = self.__data(metricname)

        if name not in Metrics.counters:
            Metrics.counters[name] = Counter(name, name, labels.keys())

        counter = Metrics.counters[name]

        if len(labels) != 0:
            counter = counter.labels(**labels)

        counter.inc(value)

    def timing(self, metricname, value):
        # Remove monkey patches below when https://github.com/thumbor-community/prometheus/issues/9 is resolved
        if (metricname == "response.smart"):
            metricname = "response.smart.latency"
        if (metricname == "response.none_smart"):
            metricname = "response.none_smart.latency"
        if (metricname.startswith("original_image.fetch.")):
            metricname = metricname.replace("original_image.fetch.", "original_image.fetch.latency.")

        name, labels = self.__data(metricname)

        if name not in Metrics.summaries:
            Metrics.summaries[name] = Summary(name, name, labels.keys())

        summary = Metrics.summaries[name]

        if len(labels) != 0:
            summary = summary.labels(**labels)

        summary.observe(value)

    def __data(self, metricname):
        basename = self.__basename(metricname)

        return (self.__format(basename), self.__labels(basename, metricname))

    def __format(self, basename):
        # stolen from https://github.com/prometheus/statsd_exporter
        # _ -> __
        # - -> __
        # . -> _

        # following prometheus advice to prefix names with the app name
        return "thumbor_{0}".format(
            basename.replace('_','__').replace('-','__').replace('.','_')
        )

    def __labels(self, name, metricname):
        if name not in self.mapping:
            return {}

        keys = self.mapping[name]

        # the split('.', MAXSPLIT) is mainly necessary to get the correct
        # stuff for original_image.fetch where the networklocation is
        # something like 'domain' so like 'test.com' and would be splitted at
        # least 1 time too often
        values = metricname.replace(name + '.', '').split('.', len(self.mapping[name])-1)

        return dict(zip(keys, values))

    def __basename(self, metricname):
        for mapped in self.mapping.keys():
            if metricname.startswith(mapped + "."):
                metricname = mapped
        return metricname
