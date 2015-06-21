#!/usr/bin/python

# -*- coding: utf-8 -*-

# Copyright (C) 2009-2012:
#    Gabes Jean, naparuba@gmail.com
#    Gerhard Lausser, Gerhard.Lausser@consol.de
#    Gregory Starck, g.starck@gmail.com
#    Hartmut Goebel, h.goebel@goebel-consult.de
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

from shinken.log import logger
from string import Template
from shinken.basemodule import BaseModule
from datetime import datetime
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


class Graphite_Webui(BaseModule):
    def __init__(self, modconf):
        BaseModule.__init__(self, modconf)
        
        # Separate perfdata multiple values
        self.multival = re.compile(r'_(\d+)$')
        
        # Specific filter to allow metrics to include '.' for Graphite
        self.illegal_char_metric = re.compile(r'[^a-zA-Z0-9_.\-]')
        
        # service name to use for host check
        self.hostcheck = getattr(modconf, 'hostcheck', '__HOST__')
        
        # Specify font and picture size for dashboard widget
        self.dashboard_view_font = getattr(modconf, 'dashboard_view_font', '8')
        self.dashboard_view_width = getattr(modconf, 'dashboard_view_width', '320')
        self.dashboard_view_height = getattr(modconf, 'dashboard_view_height', '240')
        
        # Specify font and picture size for element view
        self.detail_view_font = getattr(modconf, 'detail_view_font', '8')
        self.detail_view_width = getattr(modconf, 'detail_view_width', '586')
        self.detail_view_height = getattr(modconf, 'detail_view_height', '308')

        self.uri = getattr(modconf, 'uri', None)
        if not self.uri:
            raise Exception('The WebUI Graphite module is missing uri parameter.')
        self.uri = self.uri.strip()
        if not self.uri.endswith('/'):
            self.uri += '/'
        # Change YOURSERVERNAME by our server name if we got it
        if 'YOURSERVERNAME' in self.uri:
            my_name = socket.gethostname()
            self.uri = self.uri.replace('YOURSERVERNAME', my_name)
        logger.info("[Graphite UI] Configuration - uri: %s", self.uri)
        
        self.templates_path = getattr(modconf, 'templates_path', '/tmp')
        logger.info("[Graphite UI] Configuration - templates path: %s", self.templates_path)


        # optional "sub-folder" in graphite to hold the data of a specific host
        self.graphite_data_source = self.illegal_char_metric.sub('_',
                                    getattr(modconf, 'graphite_data_source', ''))
        logger.info("[Graphite UI] Configuration - Graphite data source: %s", self.graphite_data_source)


        # optional perfdatas to be filtered
        self.filtered_metrics = {}
        filters = getattr(modconf, 'filter', [])
        for filter in filters:
            filtered_service, filtered_metric = filter.split(':')
            if filtered_service not in self.filtered_metrics:
                self.filtered_metrics[filtered_service] = []
            self.filtered_metrics[filtered_service].append(filtered_metric.split(','))
        
        for service in self.filtered_metrics:
            logger.info("[Graphite UI] Configuration - Filtered metric: %s - %s", service, self.filtered_metrics[service])

        # Use warning, critical, min, max
        self.use_warning = bool(getattr(modconf, 'use_warning', True))
        logger.info("[Graphite UI] Configuration - use warning metrics: %d", self.use_warning)
        self.use_critical = bool(getattr(modconf, 'use_critical', True))
        logger.info("[Graphite UI] Configuration - use critical metrics: %d", self.use_critical)
        self.use_min = bool(getattr(modconf, 'use_min', True))
        logger.info("[Graphite UI] Configuration - use min metrics: %d", self.use_min)
        self.use_max = bool(getattr(modconf, 'use_max', True))
        logger.info("[Graphite UI] Configuration - use max metrics: %d", self.use_max)
        
        
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

        for e in metrics:
            if service in self.filtered_metrics:
                if e.name in self.filtered_metrics[service]:
                    logger.warning("[Graphite UI] Ignore metric '%s' for filtered service: %s", e.name, service)
                    continue
                
            name = self.illegal_char_metric.sub('_', e.name)
            name = self.multival.sub(r'.\1', name)

            # bailout if no value
            if name == '':
                continue
                
            # get metric value and its thresholds values if they exist
            metric = dict()
            metric['name'] = name
            metric['uom'] = e.uom
                
            # Get or ignore extra values depending upon module configuration
            if e.warning and self.use_warning:
                metric['warning'] = e.warning
                
            if e.critical and self.use_critical:
                metric['critical'] = e.critical
                
            if e.min and self.use_min:
                metric['min'] = e.min
                
            if e.max and self.use_max:
                metric['max'] = e.max
                
            result.append(metric)

        logger.debug("[Graphite UI] get_metric_and_value: %s", result)
        return result


    # Private function to replace the fontsize uri parameter by the correct value
    # or add it if not present.
    def _replaceFontSize ( self, url, newsize ):
        # Do we have fontSize in the url already, or not ?
        if re.search('fontSize=',url) is None:
            url = url + '&fontSize=' + newsize
        else:
            url = re.sub(r'(fontSize=)[^\&]+',r'\g<1>' + newsize , url);
        return url

    # Private function to replace the width uri parameter by the correct value
    # or add it if not present.
    def _replaceGraphWidth ( self, url, newwidth ):
        # Do we have graphwidth in the url already, or not ?
        if re.search('width=',url) is None:
            url = url + '&width=' + newwidth
        else:
            url = re.sub(r'(width=)[^\&]+',r'\g<1>' + newwidth , url);
        return url

    # Private function to replace the height uri parameter by the correct value
    # or add it if not present.
    def _replaceGraphHeight ( self, url, newheight ):
        # Do we have graphwidth in the url already, or not ?
        if re.search('height=',url) is None:
            url = url + '&height=' + newheight
        else:
            url = re.sub(r'(height=)[^\&]+',r'\g<1>' + newheight , url);
        return url



    # Ask for an host or a service the graph UI that the UI should
    # give to get the graph image link and Graphite page link too.
    def get_graph_uris(self, elt, graphstart, graphend, source = 'detail', width = 0, height = 0):
        logger.debug("[Graphite UI] get graphs URI for %s (%s view)", elt.host_name, source)
        
        if not elt:
            return []

        t = elt.__class__.my_type
        r = []

        # Graph font size
        fontsize={ '': self.detail_view_font, 'detail': self.detail_view_font, 'dashboard': self.dashboard_view_font}
        # Graph width
        graphwidth={ '': self.detail_view_width, 'detail': self.detail_view_width, 'dashboard': self.dashboard_view_width}
        # Graph height
        graphheight={ '': self.detail_view_height, 'detail': self.detail_view_height, 'dashboard': self.dashboard_view_height}
        
        # Handling Graphite variables
        data_source=""
        graphite_pre=""
        graphite_post=""
        if self.graphite_data_source:
            data_source = ".%s" % self.graphite_data_source
        if t == 'host':
            if "_GRAPHITE_PRE" in elt.customs:
                graphite_pre = "%s." % self.illegal_char_metric.sub("_", elt.customs["_GRAPHITE_PRE"])
        elif t == 'service':
            if "_GRAPHITE_PRE" in elt.host.customs:
                graphite_pre = "%s." % self.illegal_char_metric.sub("_", elt.host.customs["_GRAPHITE_PRE"])
            if "_GRAPHITE_POST" in elt.customs:
                graphite_post = ".%s" % self.illegal_char_metric.sub("_", elt.customs["_GRAPHITE_POST"])

        # Format the start & end time (and not only the date)
        d = datetime.fromtimestamp(graphstart)
        d = d.strftime('%H:%M_%Y%m%d')
        e = datetime.fromtimestamp(graphend)
        e = e.strftime('%H:%M_%Y%m%d')

        # Do we have a template for the given source?
        filename = elt.check_command.get_name().split('!')[0] + '.graph'
        thefile = os.path.join(self.templates_path, source, filename)

        # If not try to use the one for the parent folder
        if not os.path.isfile(thefile):
            # In case of CHECK_NRPE, the check_name is in second place
            if len(elt.check_command.get_name().split('!')) > 1:
                filename = elt.check_command.get_name().split('!')[0] + '_' + elt.check_command.get_name().split('!')[1] + '.graph'
                thefile = os.path.join(self.templates_path, source, filename)
            if not os.path.isfile(thefile):
                thefile = os.path.join(self.templates_path, filename) 

        logger.debug("[Graphite UI] Template filename: %s" % thefile)
        if os.path.isfile(thefile):
            logger.debug("[Graphite UI] Found template: %s" % thefile)
            template_html = ''
            with open(thefile, 'r') as template_file:
                template_html += template_file.read()
            # Read the template file, as template string python object
           
            html = Template(template_html)
            # Build the dict to instantiate the template string
            values = {}
            if t == 'host':
                values['host'] = graphite_pre + self.illegal_char_metric.sub("_", elt.host_name) + data_source
                values['service'] = '__HOST__'
            if t == 'service':
                values['host'] = graphite_pre + self.illegal_char_metric.sub("_", elt.host.host_name) + data_source
                values['service'] = self.illegal_char_metric.sub("_", elt.service_description) + graphite_post
            values['uri'] = self.uri
            # Split, we may have several images.
            for img in html.substitute(values).split('\n'):
                if not img == "":
                    v = {}
                    v['link'] = self.uri
                    v['img_src'] = img.replace('"', "'") + "&from=" + d + "&until=" + e
                    v['img_src'] = self._replaceFontSize(v['img_src'], fontsize[source])
                    r.append(v)
            # No need to continue, we have the images already.
            return r
        logger.debug("[Graphite UI] no template found.")

        # If no template is present, then the usual way
        # Remove all non alphanumeric character
        hostname = self.illegal_char_metric.sub('_', elt.host_name)
        if t == 'host':
            service = self.hostcheck
        else:
            service = self.illegal_char_metric.sub('_', elt.service_description)
        logger.debug("[Graphite UI] no template for an host/service: %s/%s", hostname, service)
        
        couples = self.get_metric_and_value(service, elt.perf_data)
        if len(couples) == 0:
            return []

        # For each metric ...
        for metric in couples:
            logger.debug("[Graphite UI] metric: %s", metric)
            
            uri = self.uri + 'render/?width=586&height=308&lineMode=connected&from=' + d + "&until=" + e
            uri = self._replaceFontSize(uri, fontsize[source])
            if width == 0:
                uri = self._replaceGraphWidth(uri, graphwidth[source])
            else:
                uri = self._replaceGraphWidth(uri, width)
            if height == 0:
                uri = self._replaceGraphHeight(uri, graphheight[source])
            else:
                uri = self._replaceGraphWidth(uri, height)
            
            # Graph title
            uri += '''&title=%s/%s - %s''' % (hostname, service, metric['name'])
                                              
            # Graph main serie
            uri += '''&target=alias(%s%s%s.%s.%s%s,"%s")''' % (graphite_pre, hostname, data_source, service, metric['name'], graphite_post, metric['name'])
                                              
            if 'warning' in metric:
                uri += '''&target=alias(constantLine(%d), "%s")''' % (metric['warning'], 'Warning')
            if 'critical' in metric:
                uri += '''&target=alias(constantLine(%d), "%s")''' % (metric['critical'], 'Critical')
            if 'min' in metric:
                uri += '''&target=alias(constantLine(%d), "%s")''' % (metric['min'], 'Min')
            if 'max' in metric:
                uri += '''&target=alias(constantLine(%d), "%s")''' % (metric['max'], 'Max')
                
            v = {}
            v['link'] = self.uri
            v['img_src'] = uri
            logger.debug("[Graphite UI] uri: %s / %s", v['link'], v['img_src'])
            r.append(v)

        return r
            
