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

# Graphite utilities for generating graphs
__author__ = 'bjorn'


from datetime import datetime
import re
import logging
import urlparse


# encapsulate graph styles
# TODO - Add additional properties (fgColor, bgColor, unitsystem) (should these be in Style or URL??)
class GraphStyle(object):
    def __init__(self, width=586, height=308, font_size=8, line_style=None, foreground=None, background=None,
                 area_mode=None):
        self.width = int(width)
        self.height = int(height)
        self.font_size = int(font_size)
        self.line_style = line_style
        self.foreground = foreground
        self.background = background
        self.area_mode = area_mode

    def __str__(self):
        s = 'width={0.width}&height={0.height}&fontSize={0.font_size}'
        if self.line_style is not None:
            s += '&lineMode={0.line_style}'
        if self.foreground is not None:
            s += '&fgcolor={0.foreground}'
        if self.background is not None:
            s += '&bgcolor={0.background}'
        if self.area_mode is not None:
            s += '&areaMode={0.area_mode}'
        return s.format(self)


# TODO - Determine how to handle relative times (negative values as offset from now?)
# generate a graphite compatible time from a unix timestamp, if the value provided is not a valid
# timestamp, assume that we have a compatible time
def graphite_time(timestamp):
    try:
        timestamp = int(timestamp)
        return datetime.fromtimestamp(timestamp).strftime('%H:%M_%Y%m%d')
    except (TypeError, ValueError):
        return timestamp


class GraphiteFunction(object):
    def __init__(self, name, args):
        self.name = name
        self.args = args

    def __str__(self):
        logging.debug('Generating Sting for function %s', self.name)
        return '{0.name}({1})'.format(self, ','.join([str(x) for x in self.args]))


class GraphiteString(object):
    def __init__(self, s):
        self.s = s.strip('"')

    def __str__(self):
        return '"{0.s}"'.format(self)


# TODO - Add boolean to place metric on second Y Axis
# TODO - Evaluate other common display functions for inclusion
# everything can just be manually put into the 'target' right now
class GraphiteTarget(object):
    def __init__(self, target='', alias=None, color=None, **kwargs):
        if not target:
            raise ValueError('Target is required')
        if target.__class__ is GraphiteTarget:
            self.__dict__ = dict(target.__dict__)
            if alias is not None:
                self.alias = alias
            if color is not None:
                self.color = color
        elif isinstance(target, dict):
            self.__init__(**target)
        else:
            self.target = self.from_string(target)
            self.alias = alias
            self.color = color

    def __str__(self):
        s = str(self.target)
        if self.color:
            s = 'color(%s,"%s")' % (s, self.color)
        if self.alias:
            s = 'alias(%s,"%s")' % (s, self.alias)
        return s

    @classmethod
    def from_string(self, target='', ):
        if not isinstance(target, basestring):
            return target

        def parse_graphite_args(part):
            logging.debug('Parsing args %s', part)
            open_brackets = 0
            s = ''
            for c in part:
                if c == ',' and not open_brackets:
                    yield s
                    s = ''
                else:
                    if c == '(':
                        open_brackets += 1
                    elif c == ')':
                        open_brackets -= 1
                    s += c
            yield s

        def parse_graphite_part(part):
            logging.debug('Parsing %s', part)
            ndx = part.find('(')
            if ndx < 0:
                logging.debug('No function call')
                if part[0] == '"' and part[-1] == '"':
                    logging.debug('Returning Graphite String')
                    return GraphiteString(part)
                try:
                    return int(part)
                except ValueError:
                    pass
                try:
                    return float(part)
                except ValueError:
                    pass
                logging.debug('Returning Graphite metric %s', part)
                return GraphiteMetric(part)
            fn = part[:ndx]
            logging.debug('Function : %s Arguments : %s', part[:ndx], part[ndx + 1:])
            return GraphiteFunction(fn, [parse_graphite_part(x) for x in parse_graphite_args(part[ndx + 1:-1])])

        return parse_graphite_part(target)


# programmatic representation of a graphite URL
# TODO - Add additional properties (fgColor, bgColor, unitSystem)
class GraphiteURL(object):
    def __init__(self, server='', title='', style=GraphStyle(), start=0, end=0, min=None, max=None, targets=None,
                 **kwargs):
        self._start = ''
        self._end = ''
        if server.endswith('/'):
            server=server[:-1]
        self.server = server
        self.start = start
        self.end = end
        self.targets = []
        if targets is not None:
            for t in targets:
                self.add_target(t)
        self.style = style
        for k in ('height', 'width', 'font_size', 'line_style'):
            if k in kwargs:
                setattr(self.style, k, kwargs[k])
        self.title = title
        self.max = max
        self.min = min
        self._targets = ''
        self.tz = None
        if 'tz' in kwargs:
            self.tz = kwargs['tz']
        pass

    # ensure that the start and end times we are given are in the correct format
    @property
    def start(self):
        return self._start

    @start.setter
    def start(self, value):
        self._start = graphite_time(value)

    @property
    def end(self):
        return self._end

    @end.setter
    def end(self, value):
        self._end = graphite_time(value)

    def add_target(self, target, **kwargs):
        self._targets = ''
        self.targets.append(GraphiteTarget(target, **kwargs))

    @property
    def target_string(self):
        try:
            if not self._targets:
                self._targets = '&'.join(['target=%s' % t for t in self.targets])
            return self._targets
        except:
            logging.exception('Unable to generate target string')
            logging.error(self.targets)
            raise

    @classmethod
    def parse(cls, string, style=GraphStyle()):
        parts = urlparse.urlparse(string)
        query = urlparse.parse_qs(parts.query)

        def query_param(key, default=None):
            r = default
            try:
                r = query[key][0]
                del query[key]
            except (KeyError, IndexError):
                pass
            return r

        server = '{0.scheme}://{0.hostname}'.format(parts)
        if parts.port:
            server += ':%d' % parts.port
        path = parts.path.split('/')
        # strip out the final component (should be render or composer) since the args list is
        # separated from the path by a '/?' this is actually the last two elements that need to be dropped
        server += '/'.join(path[:-2])

        obj = cls(style=style, server=server)
        # style
        obj.style.width = query_param('width', obj.style.width)
        obj.style.height = query_param('height', obj.style.height)
        obj.style.font_size = query_param('fontSize', obj.style.font_size)
        obj.style.line_style = query_param('lineMode', obj.style.line_style)
        obj.style.foreground = query_param('fgcolor', obj.style.foreground)
        obj.style.background = query_param('bgcolor', obj.style.background)
        obj.style.area_mode = query_param('areaMode', obj.style.area_mode)
        # url params
        obj.start = query_param('from', None)
        obj.end = query_param('until', None)
        obj.tz = query_param('tz', None)
        obj.title = query_param('title', None)
        obj.min = query_param('yMin', None)
        obj.max = query_param('yMax', None)
        # targets
        for t in query['target']:
            obj.add_target(GraphiteTarget.from_string(t))
        del query['target']
        # extras
        for k, v in query.items():
            logging.warn('unrecognized parameter "%s" : %r', k, v)
        return obj

    def url(self, module='render'):
        if module not in ('render', 'composer'):
            raise ValueError('module must be "render" or "composer" not "%s"' % module)
        s = '{0.server}/{1}/?{0.style}'
        if self.start:
            s += '&from={0.start}'
        if self.end:
            s += '&until={0.end}'
        if self.tz:
            s += '&tz={0.tz}'
        if self.title:
            s += '&title={0.title}'
        if self.min is not None:
            s += '&yMin={0.min}'
        if self.max is not None:
            s += '&yMax={0.max}'
        if self.target_string:
            s += '&{0.target_string}'

        return s.format(self, module)

    def __str__(self):
        return self.url('render')


class GraphiteRewriteRule(object):
    def __init__(self, match, sub):
        self.match = re.compile(match)
        self.sub = sub

    def apply(self, metric):
        return self.match.sub(self.sub, metric)


class GraphiteMetric(object):
    # Specific filter for metrics name
    illegal_char = re.compile(r'[^a-zA-Z0-9_.\-]')
    # Specific filter for host and services names
    illegal_char_hostname = re.compile(r'[^a-zA-Z0-9_\-]')

    rewrite_rules = []

    def __init__(self, *parts):
        self.parts = list()
        for p in parts:
            self.parts.extend(p.split('.'))
        self.parts = parts

    def __str__(self):
        string = GraphiteMetric.join(*self.parts)
        string = GraphiteMetric.normalize(string)
        string = GraphiteMetric.rewrite(string)
        return string

    @staticmethod
    def join(*args):
        return '.'.join([str(a) for a in args if a])

    @classmethod
    def normalize(cls, metric_name):
        return cls.illegal_char.sub("_", metric_name)

    @classmethod
    def normalize_name(cls, metric_name):
        return cls.illegal_char_hostname.sub("_", metric_name)

    @classmethod
    def add_rule(cls, rule, sub):
        if not isinstance(rule, GraphiteRewriteRule):
            rule = GraphiteRewriteRule(rule, sub)
        cls.rewrite_rules.append(rule)

    @classmethod
    def rewrite(cls, metric):
        logging.debug('Input String %s', metric)
        logging.debug('Applying %d transformations', len(cls.rewrite_rules))
        for r in cls.rewrite_rules:
            metric = r.apply(metric)
        logging.debug('Output String %s', metric)
        return metric
