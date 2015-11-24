#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright (C) 2009-2015:
#    Bjorn, @Simage
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

__author__ = 'bjorn'

import logging
import os
from string import Template
import json

from .graphite_utils import GraphiteURL, GraphiteMetric, graphite_time


logger = logging.getLogger('utils')


class TemplateNotFound(BaseException):
    pass


# TODO - Implement relative offsets to allow graphs that start some period of time ago and end now
class GraphFactory(object):
    def __init__(self, element, graph_start, graph_end, source='detail', log=logger, cfg=None):
        if log is None:
            log = logger.getLogger('GraphFactory')
        self.source = source
        self.logger = log
        self.cfg = cfg
        self.element = element
        self.graph_start = graph_start
        self.graph_end = graph_end

    # property to retrieve the graphite prefix for a host
    @property
    def prefix(self):
        self.logger.debug(self.element.customs)
        self.logger.debug(self.element_type)
        if self.element_type == 'host':
            if "_GRAPHITE_PRE" in self.element.customs:
                if "_GRAPHITE_GROUP" in self.element.customs:
                    return GraphiteMetric.join(
                        self.element.customs["_GRAPHITE_PRE"],
                        self.element.customs["_GRAPHITE_GROUP"]
                    )
                else:
                    return self.element.customs["_GRAPHITE_PRE"]
            else:
                if "_GRAPHITE_GROUP" in self.element.customs:
                    return self.element.customs["_GRAPHITE_GROUP"]
        elif self.element_type == 'service':
            if "_GRAPHITE_PRE" in self.element.host.customs:
                if "_GRAPHITE_GROUP" in self.element.host.customs:
                    return GraphiteMetric.join(
                        self.element.host.customs["_GRAPHITE_PRE"],
                        self.element.host.customs["_GRAPHITE_GROUP"]
                    )
                else:
                    return self.element.host.customs["_GRAPHITE_PRE"]
            else:
                if "_GRAPHITE_GROUP" in self.element.host.customs:
                    return self.element.host.customs["_GRAPHITE_GROUP"]
        return ''

    # property to retrieve the graphite postfix for a host
    @property
    def postfix(self):
        if self.element_type == 'service' and "_GRAPHITE_POST" in self.element.customs:
            return self.element.customs["_GRAPHITE_POST"]
        return ''

    @property
    def template_path(self):
        command_parts = self.element.check_command.get_name().split('!')
        filename = command_parts[0] + '.graph'
        template_file = os.path.join(self.cfg.templates_path, self.source, filename)
        self.logger.debug('Checking for template at "%s"', template_file)
        if os.path.isfile(template_file):
            return template_file

        # If not try to use the one for the parent folder
        template_file = os.path.join(self.cfg.templates_path, filename)
        self.logger.debug('Checking for template at "%s"', template_file)
        if os.path.isfile(template_file):
            return template_file
        # In case of CHECK_NRPE, the check_name is in second place
        if len(command_parts) > 1:
            filename = command_parts[0] + '_' + command_parts[1] + '.graph'
            template_file = os.path.join(self.cfg.templates_path, self.source, filename)
            self.logger.debug('Checking for template at "%s"', template_file)
            if os.path.isfile(template_file):
                return template_file

            template_file = os.path.join(self.cfg.templates_path, filename)
            self.logger.debug('Checking for template at "%s"', template_file)
            if os.path.isfile(template_file):
                return template_file

        self.logger.debug("[Graphite UI] no template found for %s/%s", self.hostname, self.servicename)
        raise TemplateNotFound()

    # determine the hostname, servicename and the element type
    @property
    def hostname(self):
        try:
            return GraphiteMetric.normalize_name(self.element.host_name)
        except AttributeError:
            return GraphiteMetric.normalize_name(self.element.host.host_name)

    @property
    def element_type(self):
        return self.element.__class__.my_type

    @property
    def servicename(self):
        if self.element_type == 'service':
            return GraphiteMetric.normalize_name(self.element.service_description)
        else:
            return GraphiteMetric.normalize_name(self.cfg.hostcheck)

    # retrieve a style with graceful fallback
    def get_style(self, name):
        try:
            return self.cfg.styles[name]
        except KeyError:
            self.logger.warning("No style %s, falling back to default", name)
            return self.cfg.styles['default']

    @property
    def style(self):
        return self.get_style(self.source)

    # Ask for an host or a service the graph UI that the UI should
    # give to get the graph image link and Graphite page link too.
    def get_graph_uris(self):
        self.logger.debug("[Graphite UI] get graphs URI for %s/%s (%s view)", self.hostname, self.servicename,
                          self.source)

        try:
            return self._get_uris_from_file()
        except TemplateNotFound:
            pass
        except:
            self.logger.exception('Error while generating graph uris')
            return []

        try:
            return self._generate_graph_uris()
        except:
            self.logger.exception('Error while generating graph uris')
            return []

    # function to generate a list of uris
    def _generate_graph_uris(self):
        couples = self.cfg.get_metric_and_value(self.servicename, self.element.perf_data)

        if len(couples) == 0:
            self.logger.debug('No perfdata found to graph')
            return []

        # For each metric ...
        uris = []
        for metric in couples:
            self.logger.debug("[Graphite UI] metric: %s", metric)
            title = '%s/%s - %s' % (self.hostname, self.servicename, metric['name'])
            graph = GraphiteURL(server=self.cfg.uri, title=title, style=self.style,
                                start=self.graph_start, end=self.graph_end, tz=self.cfg.tz)

            # Graph main series
            graphite_metric = GraphiteMetric(self.prefix, self.hostname,
                                             self.cfg.graphite_data_source,
                                             self.servicename, metric['name'], self.postfix)
            graph.add_target(graphite_metric, alias=metric['name'], color='green')

            #TODO - Shinken appears to store these in graphite, rather than using the current value as a constant line,
            #TODO - use the approppriate time series from graphite
            #NOTE - the Graphite module allows the filtering of constant metrics to avoid storing warn, crit, ... in Graphite!
            #NOTE - constantLine function is much appropriate in this case.
            colors = {'warning': 'orange', 'critical': 'red', 'min': 'blue', 'max': 'black'}
            for t in ('warning', 'critical', 'min', 'max'):
                if t in metric:
                    n = 'color_%s' % t
                    graph.add_target('constantLine(%d)' % metric[t], alias=t.title(), color=getattr(self.cfg, n))

            v = dict(
                link=graph.url('composer'),
                img_src=graph.url('render')
            )
            self.logger.debug("[Graphite UI] uri: %s / %s", v['link'], v['img_src'])
            uris.append(v)

        return uris

    def _parse_json_template(self, template):
        try:
            template = JSONTemplate(template)
        except:
            raise JSONTemplate.NotJsonTemplate()

        graph_end = graphite_time(self.graph_end)
        graph_start = graphite_time(self.graph_start)
        uris = []

        context = dict(
            uri=self.cfg.uri,
            host=GraphiteMetric.normalize(
                GraphiteMetric.join(self.prefix, self.hostname, self.cfg.graphite_data_source)),
            service=GraphiteMetric.normalize(GraphiteMetric.join(self.servicename, self.postfix))
        )
        for g in template.fill(context):
            u = GraphiteURL(server=self.cfg.uri, start=graph_start, end=graph_end, style=self.style, **g)
            uris.append(dict(link=u.url('composer'), img_src=u.url('render')))

        return uris

    # retrieve uri's from a template file
    def _get_uris_from_file(self):
        uris = []
        # Do we have a template for the given source?
        # we do not catch the exception here as it is caught by the calling function
        template_file = self.template_path
        self.logger.debug("[Graphite UI] Found template: %s" % template_file)

        try:
            return self._parse_json_template(template_file)
        except JSONTemplate.NotJsonTemplate:
            pass

        graph_end = graphite_time(self.graph_end)
        graph_start = graphite_time(self.graph_start)
        template_html = ''
        with open(template_file, 'r') as template_file:
            template_html += template_file.read()
        # Read the template file, as template string python object
        html = Template(template_html)
        # Build the dict to instantiate the template string

        context = dict(
            uri=self.cfg.uri,
            host=GraphiteMetric.normalize(
                GraphiteMetric.join(self.prefix, self.hostname, self.cfg.graphite_data_source)),
            service=GraphiteMetric.normalize(GraphiteMetric.join(self.servicename, self.postfix))
        )


        # Split, we may have several images.
        for img in html.substitute(context).split('\n'):
            if not img:
                continue
            graph = GraphiteURL.parse(img, style=self.style)
            uris.append(dict(link=graph.url('composer'), img_src=graph.url('render')))
        return uris


class JSONTemplate(object):
    class NotJsonTemplate(BaseException):
        pass

    def __init__(self, data):
        try:
            if os.path.isfile(data):
                data = open(data, 'rt')
        except Exception as e:
            logger.debug('Unable to read from path %s', data)
        try:
            if hasattr(data, 'read'):
                self.data = json.load(data)
            else:
                self.data = json.loads(data)
        except ValueError:
            logger.debug('Unable to parse JSON')
            logger.debug(data)
            raise self.NotJsonTemplate(data)

    def fill(self, ctx):
        return JSONTemplate._fill_template(self.data, ctx)

    @classmethod
    def _fill_template(self, obj, ctx):
        if hasattr(obj, 'format'):  # string or stringlike
            return obj.format(**ctx)
        elif hasattr(obj, 'items'):  # dictionary like we hope
            return dict((k, self._fill_template(v, ctx)) for k, v in obj.items())
        elif hasattr(obj, '__iter__'):  # its iterable so treat it as a list
            return [self._fill_template(v, ctx) for v in obj]
        else:
            return obj
