# Graphite utilities for generating graphs

# generate a graphite compatible time from a unix timestamp, if the value provided is not a valid timestamp, assume that we have a compatible time

from datetime import datetime
import re
import logging



# encapsulate graph styles
class GraphStyle(object):
    def __init__(self, width=586, height=308, font_size=8, line_style=None):
        self.width = int(width)
        self.height = int(height)
        self.font_size = int(font_size)
        self.line_style = line_style

    def __str__(self):
        s = 'width={0.width}&height={0.height}&fontSize={0.font_size}'
        if self.line_style is not None:
            s += '&lineMode={0.line_style}'
        return s.format(self)


def graphite_time(timestamp):
    try:
        timestamp = int(timestamp)
        return datetime.fromtimestamp(timestamp).strftime('%H:%M_%Y%m%d')
    except ValueError:
        return timestamp


class GraphiteTarget(object):
    def __init__(self, target='', alias=None, color=None, **kwargs):
        if not target:
            raise ValueError('Target is required')
        if target.__class__ is GraphiteTarget:
            self.__dict__ = dict(target.__dict__)
            if alias is not None:
                self.alias=alias
            if color is not None:
                self.color=color
        elif isinstance(target,dict):
            self.__init__(**target)
        else:
            self.target = target
            self.alias = alias
            self.color = color

    def __str__(self):
        s = self.target
        if self.alias:
            s = 'alias(%s,"%s")' % (s, self.alias)
        if self.color:
            s = 'color(%s,"%s")' % (s, self.color)
        return s


# programmatic representation of a graphite URL
class GraphiteURL(object):
    def __init__(self, server='', title='', style=GraphStyle(), start=0, end=0, min=None, max=None, targets=None,**kwargs):
        self._start = ''
        self._end = ''
        self.server = server
        self.start = start
        self.end = end
        self.targets = []
        if targets is not None:
            for t in targets:
                self.add_target(t)
        self.style = style
        for k in ('height','width','font_size','line_style'):
            if k in kwargs:
                setattr(self.style,k,kwargs[k])
        self.title = title
        self.max = max
        self.min = min
        self._targets = ''
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
    def parse(cls, string):
        pass

    def url(self, module='render'):
        if module not in ('render', 'composer'):
            raise ValueError('module must be "render" or "composer" not "%s"' % module)
        s = '{0.server}{1}/?{0.style}&from={0.start}&until={0.end}'
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


class GraphiteMetric(object):
    illegal_char = re.compile(r'[^a-zA-Z0-9_.\-]')

    @staticmethod
    def join(*args):
        return '.'.join([str(a) for a in args if a])

    @classmethod
    def normalize(cls, metric_name):
        return cls.illegal_char.sub("_", metric_name)
