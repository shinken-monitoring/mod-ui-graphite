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
import os
from string import Template

from .graphite_utils import GraphiteURL, GraphStyle, GraphiteMetric, graphite_time

from shinken.log import logger
from shinken.basemodule import BaseModule
from shinken.log import logger
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


class TemplateNotFound(BaseException):
    pass


class Graphite_Webui(BaseModule):
    def __init__(self, modconf):
        BaseModule.__init__(self, modconf)
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

            name = multival.sub(r'.\1', name)

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


    # function to retrieve the graphite prefix for a host
    def graphite_pre(self, elt):
        elt_type = elt.__class__.my_type
        if elt_type == 'host':
            if "_GRAPHITE_PRE" in elt.customs:
                elt.customs["_GRAPHITE_PRE"]
        elif elt_type == 'service':
            if "_GRAPHITE_PRE" in elt.host.customs:
                elt.host.customs["_GRAPHITE_PRE"]
        return ''

    # function to retrieve the graphite postfix for a host
    def graphite_post(self, elt):
        elt_type = elt.__class__.my_type
        if elt_type == 'service' and "_GRAPHITE_POST" in elt.customs:
            elt.customs["_GRAPHITE_POST"]
        return ''

    # check all possible template paths for a template for a particular element
    def _get_template_path(self, elt, source):
        command_parts = elt.check_command.get_name().split('!')
        filename = command_parts[0] + '.graph'
        template_file = os.path.join(self.templates_path, source, filename)
        logger.debug('Checking for template at "%s"', template_file)
        if os.path.isfile(template_file):
            return template_file

        # If not try to use the one for the parent folder
        template_file = os.path.join(self.templates_path, filename)
        logger.debug('Checking for template at "%s"', template_file)
        if os.path.isfile(template_file):
            return template_file
        # In case of CHECK_NRPE, the check_name is in second place
        if len(command_parts) > 1:
            filename = command_parts[0] + '_' + command_parts[1] + '.graph'
            template_file = os.path.join(self.templates_path, source, filename)
            logger.debug('Checking for template at "%s"', template_file)
            if os.path.isfile(template_file):
                return template_file

            template_file = os.path.join(self.templates_path, filename)
            logger.debug('Checking for template at "%s"', template_file)
            if os.path.isfile(template_file):
                return template_file

        hostname, service, _ = self.get_element_names(elt)
        logger.debug("[Graphite UI] no template found for %s/%s", hostname, service)
        raise TemplateNotFound()

    # determine the hostname, servicename and the element type
    def get_element_names(self, elt):
        element_type = elt.__class__.my_type
        try:
            hostname = elt.host_name
        except AttributeError:
            hostname = elt.host.host_name
        if element_type == 'host':
            service = self.hostcheck
        else:
            service = elt.service_description
        return hostname, service, element_type

    # retrieve a style with graceful fallback
    def get_style(self, name):
        try:
            return self.styles[name]
        except KeyError:
            logger.warning("No style %s, falling back to default")
            return self.styles['default']

    # Ask for an host or a service the graph UI that the UI should
    # give to get the graph image link and Graphite page link too.
    def get_graph_uris(self, elt, graph_start, graph_end, source='detail', **kwargs):
        if not elt:
            return []
        logger.debug("[Graphite UI] get graphs URI for %s (%s view)", elt.host_name, source)

        try:
            return self._get_uris_from_file(elt, graph_start, graph_end, source)
        except TemplateNotFound:
            pass
        except:
            logger.exception('Error while generating graph uris')
            return []

        try:
            return self._generate_graph_uris(elt, graph_start, graph_end, source)
        except:
            logger.exception('Error while generating graph uris')
            return []

    # function to generate a list of uris
    def _generate_graph_uris(self, elt, graph_start, graph_end, source):
        hostname, service, elt_type = self.get_element_names(elt)
        couples = self.get_metric_and_value(service, elt.perf_data)

        if len(couples) == 0:
            logger.warning('No perfdata found to graph')
            return []

        # For each metric ...
        uris = []
        style = self.get_style(source)
        for metric in couples:
            logger.debug("[Graphite UI] metric: %s", metric)
            title = '%s/%s - %s' % (hostname, service, metric['name'])
            graph = GraphiteURL(server=self.uri, title=title, style=style, start=graph_start, end=graph_end)

            # Graph main series
            graphite_metric = GraphiteMetric.join(self.graphite_pre(elt), elt.hostname, self.graphite_data_source,
                                                  service, metric['name'], self.graphite_post(elt))
            graphite_metric = GraphiteMetric.normalize(graphite_metric)
            graph.add_target('''alias(%s,"%s")''' % (graphite_metric, metric['name']))

            for t in ('warning', 'critical', 'min', 'max'):
                if t in metric:
                    graph.add_target('alias(constantLine(%d), "%s")' % (metric['t'], t.Title()))

            v = dict(
                link=graph.url('composer'),
                img_src=graph.url('render')
            )
            logger.debug("[Graphite UI] uri: %s / %s", v['link'], v['img_src'])
            uris.append(v)

        return uris

    # retrieve uri's from a template file
    def _get_uris_from_file(self, elt, graph_start, graph_end, source):
        uris = []
        # Do we have a template for the given source?
        # we do not catch the exception here as it is caught by the calling function
        template_file = self._get_template_path(elt, source)

        hostname, service, element_type = self.get_element_names(elt)
        graph_end = graphite_time(graph_end)
        graph_start = graphite_time(graph_start)
        style = self.get_style(source)

        logger.debug("[Graphite UI] Found template: %s" % template_file)
        template_html = ''
        with open(template_file, 'r') as template_file:
            template_html += template_file.read()
        # Read the template file, as template string python object

        html = Template(template_html)
        # Build the dict to instantiate the template string

        context = dict(
            uri=self.uri,
            host=GraphiteMetric.normalize(
                GraphiteMetric.join(self.graphite_pre(elt), hostname, self.graphite_data_source)),
            service=GraphiteMetric.normalize(GraphiteMetric.join(service, self.graphite_post(elt)))
        )

        # Private function to replace the fontsize uri parameter by the correct value
        # or add it if not present.
        def _replace_font_size(url):
            # Do we have fontSize in the url already, or not ?
            if re.search('fontSize=', url) is None:
                url = url + '&fontSize=' + style.font_size
            else:
                url = re.sub(r'(fontSize=)[^&]+', r'\g<1>' + style.font_size, url)
            return url

        # Split, we may have several images.
        for img in html.substitute(context).split('\n'):
            if not img == "":
                link = _replace_font_size(img.replace('"', "'") + "&from=" + graph_start + "&until=" + graph_end)

                v = dict(
                    link=self.uri,
                    img_src=link
                )
                uris.append(v)
        return uris
