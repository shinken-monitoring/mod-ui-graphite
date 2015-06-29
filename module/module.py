#!/usr/bin/python

# -*- coding: utf-8 -*-

# Copyright (C) 2009-2012:
# Gabes Jean, naparuba@gmail.com
# Gerhard Lausser, Gerhard.Lausser@consol.de
# Gregory Starck, g.starck@gmail.com
# Hartmut Goebel, h.goebel@goebel-consult.de
#
# This file is part of Shinken.
#
# Shinken is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Shinken is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with Shinken.  If not, see <http://www.gnu.org/licenses/>.

"""
This class is for linking the WebUI with Graphite,
for mainly get graphs and links.
"""

import re
import socket

from .graphite_utils import GraphStyle
from .util import GraphFactory
from shinken.log import logger
from shinken.basemodule import BaseModule
from shinken.misc.perfdata import PerfDatas


properties = {
    'daemons': ['webui'],
    'type': 'graphite_webui'
}


# called by the plugin manager
def get_instance(plugin):
    logger.info("[Graphite UI] Get a graphite UI data module for plugin %s" % plugin.get_name())

    instance = Graphite_Webui(plugin)
    return instance


class Graphite_Webui(BaseModule):
    def __init__(self, modconf):
        BaseModule.__init__(self, modconf)
        self._uri = ''
        self.app = None

        # service name to use for host check
        self.hostcheck = getattr(modconf, 'hostcheck', '__HOST__')

        # load styles
        self.styles = dict(default=GraphStyle())
        self._load_styles(modconf)

        self.uri = getattr(modconf, 'uri', '')
        logger.info("[Graphite UI] Configuration - uri: %s", self.uri)

        self.templates_path = getattr(modconf, 'templates_path', '/tmp')
        logger.info("[Graphite UI] Configuration - templates path: %s", self.templates_path)

        # optional "sub-folder" in graphite to hold the data of a specific host
        self.graphite_data_source = getattr(modconf, 'graphite_data_source', '')
        logger.info("[Graphite UI] Configuration - Graphite data source: %s", self.graphite_data_source)

        # optional perfdatas to be filtered
        self.filtered_metrics = {}
        filters = getattr(modconf, 'filter', [])
        for f in filters:
            filtered_service, filtered_metric = f.split(':')
            if filtered_service not in self.filtered_metrics:
                self.filtered_metrics[filtered_service] = []
            self.filtered_metrics[filtered_service].append(filtered_metric.split(','))

        for service in self.filtered_metrics:
            logger.info("[Graphite UI] Configuration - Filtered metric: %s - %s", service,
                        self.filtered_metrics[service])

        # Use warning, critical, min, max
        for s in ('warning', 'critical', 'min', 'max'):
            n = 'use_%s' % s
            setattr(self, n, bool(getattr(modconf, n, True)))
            logger.info("[Graphite UI] Configuration - use %s metrics: %d", n, getattr(self, n))

    @property
    def uri(self):
        return self._uri

    @uri.setter
    def uri(self, value):
        uri = value.strip()
        if not uri:
            raise ValueError('Invalid URI provided to yhe WebUI Graphite module.')
        if not uri.endswith('/'):
            uri += '/'

        # Change YOURSERVERNAME by our server name if we got it
        if 'YOURSERVERNAME' in uri:
            my_name = socket.gethostname()
            uri = uri.replace('YOURSERVERNAME', my_name)
        self._uri = uri

    def _load_styles(self, modconf):
        # Specify font and picture size for dashboard widget
        font = getattr(modconf, 'dashboard_view_font', '8')
        width = getattr(modconf, 'dashboard_view_width', '320')
        height = getattr(modconf, 'dashboard_view_height', '240')
        self.styles['dashboard'] = GraphStyle(width=width, height=height, font_size=font)

        # Specify font and picture size for element view
        font = getattr(modconf, 'detail_view_font', '8')
        width = getattr(modconf, 'detail_view_width', '586')
        height = getattr(modconf, 'detail_view_height', '308')
        self.styles['detail'] = GraphStyle(width=width, height=height, font_size=font)

    # Try to connect if we got true parameter
    def init(self):
        pass

    # To load the webui application
    def load(self, app):
        self.app = app

    # Give the link for the GRAPHITE UI, with a Name
    def get_external_ui_link(self):
        return {'label': 'Graphite', 'uri': self.uri}

    # For a perf_data like /=30MB;4899;4568;1234;0  /var=50MB;4899;4568;1234;0 /toto=
    # return ('/', '30'), ('/var', '50')
    # TODO - ask graphite for the metrics it knows about by posting to {graphiteserver}/find
    # This really belongs in the factory, however by leaving it in here we decouple the factory from any direct shinken
    # dependencies and can test without the shinken libraries installed
    def get_metric_and_value(self, service, perf_data):
        result = []
        metrics = PerfDatas(perf_data)

        # Separate perfdata multiple values
        multival = re.compile(r'_(\d+)$')

        for e in metrics:
            if service in self.filtered_metrics:
                if e.name in self.filtered_metrics[service]:
                    logger.warning("[Graphite UI] Ignore metric '%s' for filtered service: %s", e.name, service)
                    continue

            name = multival.sub(r'.\1', e.name)

            # bailout if no value
            if name == '':
                continue

            # get metric value and its thresholds values if they exist
            metric = dict(
                name=name,
                uom=e.uom
            )

            # Get or ignore extra values depending upon module configuration
            for s in ('warning', 'critical', 'min', 'max'):
                if getattr(e, s) and getattr(self, 'use_%s' % s):
                    metric[s] = getattr(e, s)

            result.append(metric)

        logger.debug("[Graphite UI] get_metric_and_value: %s", result)
        return result

    def get_graph_uris(self, element, graph_start, graph_end, source='detail'):
        factory = GraphFactory(element, graph_start, graph_end, source, cfg=self, log=logger)
        return factory.get_graph_uris()

