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
    logger.debug("[Graphite UI]Get an GRAPHITE UI module for plugin %s" % plugin.get_name())

    instance = Graphite_Webui(plugin)
    return instance


class Graphite_Webui(BaseModule):
    def __init__(self, modconf):
        BaseModule.__init__(self, modconf)
        self.multival = re.compile(r'_(\d+)$')
        self.uri = getattr(modconf, 'uri', None)
        self.templates_path = getattr(modconf, 'templates_path', '/tmp')

        if not self.uri:
            raise Exception('The WebUI Graphite module is missing uri parameter.')

        self.uri = self.uri.strip()
        if not self.uri.endswith('/'):
            self.uri += '/'

        # Change YOURSERVERNAME by our server name if we got it
        if 'YOURSERVERNAME' in self.uri:
            my_name = socket.gethostname()
            self.uri = self.uri.replace('YOURSERVERNAME', my_name)

        # optional "sub-folder" in graphite to hold the data of a specific host
        self.graphite_data_source = self.illegal_char.sub('_',
                                    getattr(modconf, 'graphite_data_source', ''))

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
    def get_metric_and_value(self, perf_data):
        res = []
        metrics = PerfDatas(perf_data)

        for e in metrics:
            try:
                logger.debug("[Graphite UI] groking: %s" % str(e))
            except UnicodeEncodeError:
                pass

            name = self.illegal_char.sub('_', e.name)
            name = self.multival.sub(r'.*', name)

            # get metric value and its thresholds values if they exist
            name_value = {name: (e.value, e.uom)}
            if e.warning and e.critical:
                name_value[name + '_warn'] = e.warning
                name_value[name + '_crit'] = e.critical
            # bailout if need
            if name_value[name] == '':
                continue
            try:
                logger.debug("[Graphite UI] Got in the end: %s, %s" % (name, e.value))
            except UnicodeEncodeError:
                pass
            for key, value in name_value.items():
                res.append((key, value))
        return res

    # Private function to replace the fontsize uri parameter by the correct value
    # or add it if not present.
    def _replaceFontSize ( self, url, newsize ):

    # Do we have fontSize in the url already, or not ?
        if re.search('fontSize=',url) is None:
            url = url + '&fontSize=' + newsize
        else:
            url = re.sub(r'(fontSize=)[^\&]+',r'\g<1>' + newsize , url);
        return url




    # Ask for an host or a service the graph UI that the UI should
    # give to get the graph image link and Graphite page link too.
    def get_graph_uris(self, elt, graphstart, graphend, source = 'detail'):
        # Ugly to hard-code such values. But where else should I put them ?
        fontsize={ 'detail': '8', 'dashboard': '18'}
        if not elt:
            return []

        t = elt.__class__.my_type
        r = []

        # Hanling Graphite variables
        data_source=""
        graphite_pre=""
        graphite_post=""
        if self.graphite_data_source:
            data_source = ".%s" % self.graphite_data_source
        if t == 'host':
            if "_GRAPHITE_PRE" in elt.customs:
                graphite_pre = "%s." % self.illegal_char.sub("_", elt.customs["_GRAPHITE_PRE"])
        elif t == 'service':
            if "_GRAPHITE_PRE" in elt.host.customs:
                graphite_pre = "%s." % self.illegal_char.sub("_", elt.host.customs["_GRAPHITE_PRE"])
            if "_GRAPHITE_POST" in elt.customs:
                graphite_post = ".%s" % self.illegal_char.sub("_", elt.customs["_GRAPHITE_POST"])

        # Format the start & end time (and not only the date)
        d = datetime.fromtimestamp(graphstart)
        d = d.strftime('%H:%M_%Y%m%d')
        e = datetime.fromtimestamp(graphend)
        e = e.strftime('%H:%M_%Y%m%d')

        filename = elt.check_command.get_name().split('!')[0] + '.graph'

        # Do we have a template for the given source?
        thefile = os.path.join(self.templates_path, source, filename)

        # If not try to use the one for the parent folder
        if not os.path.isfile(thefile):
            # In case of CHECK_NRPE, the check_name is in second place
            if len(elt.check_command.get_name().split('!')) > 1:
                filename = elt.check_command.get_name().split('!')[0] + '_' + elt.check_command.get_name().split('!')[1] + '.graph'
                thefile = os.path.join(self.templates_path, source, filename)
            if not os.path.isfile(thefile):
                thefile = os.path.join(self.templates_path, filename) 

        if os.path.isfile(thefile):
            template_html = ''
            with open(thefile, 'r') as template_file:
                template_html += template_file.read()
            # Read the template file, as template string python object
           
            html = Template(template_html)
            # Build the dict to instantiate the template string
            values = {}
            if t == 'host':
                values['host'] = graphite_pre + self.illegal_char.sub("_", elt.host_name) + data_source
                values['service'] = '__HOST__'
            if t == 'service':
                values['host'] = graphite_pre + self.illegal_char.sub("_", elt.host.host_name) + data_source
                values['service'] = self.illegal_char.sub("_", elt.service_description) + graphite_post
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

        # If no template is present, then the usual way

        if t == 'host':
            couples = self.get_metric_and_value(elt.perf_data)

            # If no values, we can exit now
            if len(couples) == 0:
                return []

            # Remove all non alpha numeric character
            host_name = self.illegal_char.sub('_', elt.host_name)

            # Send a bulk of all metrics at once
            for (metric, _) in couples:
                uri = self.uri + 'render/?width=586&height=308&lineMode=connected&from=' + d + "&until=" + e
                if re.search(r'_warn|_crit', metric):
                    continue
                target = "&target=%s%s%s.__HOST__.%s" % (graphite_pre,
                                                         host_name,
                                                         data_source,
                                                         metric)
                uri += target + target + "?????"
                v = {}
                v['link'] = self.uri
                v['img_src'] = uri
                v['img_src'] = self._replaceFontSize(v['img_src'], fontsize[source])
                r.append(v)

            return r
        if t == 'service':
            couples = self.get_metric_and_value(elt.perf_data)

            # If no values, we can exit now
            if len(couples) == 0:
                return []

            # Remove all non alpha numeric character
            desc = self.illegal_char.sub('_', elt.service_description)
            host_name = self.illegal_char.sub('_', elt.host.host_name)

            # Send a bulk of all metrics at once
            for (metric, value) in couples:
                uri = self.uri + 'render/?width=586&height=308&lineMode=connected&from=' + d + "&until=" + e
                if re.search(r'_warn|_crit', metric):
                    continue
                elif value[1] == '%':
                    uri += "&yMin=0&yMax=100"
                target = "&target=%s%s%s.%s.%s%s" % (graphite_pre,
                                                  host_name,
                                                  data_source,
                                                  desc,
                                                  metric,
                                                  graphite_post )
                uri += target + target + "?????"
                v = {}
                v['link'] = self.uri
                v['img_src'] = uri
                v['img_src'] = self._replaceFontSize(v['img_src'], fontsize[source])
                r.append(v)
            return r

        # Oups, bad type?
        return []

