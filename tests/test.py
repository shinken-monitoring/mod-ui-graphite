import unittest
import urlparse
import sys
import os
import json
import time
from datetime import datetime
import logging

logging.basicConfig(level=logging.DEBUG)

FILE_PATH = os.path.dirname(os.path.realpath(__file__))
ROOT_PATH = os.path.abspath(os.path.join(FILE_PATH, '../'))
sys.path.append(ROOT_PATH)

from module.util import JSONTemplate
from module.graphite_utils import GraphStyle, graphite_time


class TestGraphiteTarget(unittest.TestCase):
    pass


class TestGraphiteURL(unittest.TestCase):
    pass


class TestGraphiteMetric(unittest.TestCase):
    pass


class TestGraphiteTime(unittest.TestCase):
    def test_unixtime_0(self):
        self.assertEqual(graphite_time(0), '17:00_19691231')

    def test_unixtime_now(self):
        self.assertEqual(graphite_time(time.time()), datetime.now().strftime('%H:%M_%Y%m%d'))

    def test_string(self):
        self.assertEqual(graphite_time('test'), 'test')


class TestGraphiteStyle(unittest.TestCase):
    def test_base(self):
        style = GraphStyle()
        style = urlparse.parse_qs(str(style))
        self.assertEqual(style, {'width': ['586'], 'height': ['308'], 'fontSize': ['8']})

    def test_width(self):
        style = GraphStyle(width=10)
        style = urlparse.parse_qs(str(style))
        self.assertEqual(style, {'width': ['10'], 'height': ['308'], 'fontSize': ['8']})
        with self.assertRaises(ValueError):
            GraphStyle(width='test')

    def test_height(self):
        style = GraphStyle(height=7)
        style = urlparse.parse_qs(str(style))
        self.assertEqual(style, {'width': ['586'], 'height': ['7'], 'fontSize': ['8']})
        with self.assertRaises(ValueError):
            GraphStyle(height='test')

    def test_font(self):
        style = GraphStyle(font_size=16)
        style = urlparse.parse_qs(str(style))
        self.assertEqual(style, {'width': ['586'], 'height': ['308'], 'fontSize': ['16']})
        with self.assertRaises(ValueError):
            GraphStyle(font_size='test')

    def test_line_style(self):
        style = GraphStyle(line_style='connected')
        style = urlparse.parse_qs(str(style))
        self.assertEqual(style, {'width': ['586'], 'height': ['308'], 'fontSize': ['8'], 'lineMode': ['connected']})


class TestJSONTemplate(unittest.TestCase):
    data = [
        {
            "width": 586,
            "height": 308,
            "title": "Response Time on {host}",
            "min": 0,
            "targets": [
                {
                    "target": 'legendValue(alias({host}.{service}.rta,"Response Time"),"last")'
                }
            ]
        },
        {
            "width": 586,
            "height": 308,
            "title": "Packet Loss Percentage on {host}",
            "min": 0,
            "max": 100,
            "targets": [
                {
                    "target": 'legendValue(alias({host}.{service}.pl,"Packet loss percentage"),"last")'
                }
            ]
        }
    ]

    filled = [
        {
            "width": 586,
            "height": 308,
            "title": "Response Time on testhost",
            "min": 0,
            "targets": [
                {
                    "target": 'legendValue(alias(testhost.testservice.rta,"Response Time"),"last")'
                }
            ]
        },
        {
            "width": 586,
            "height": 308,
            "title": "Packet Loss Percentage on testhost",
            "min": 0,
            "max": 100,
            "targets": [
                {
                    "target": 'legendValue(alias(testhost.testservice.pl,"Packet loss percentage"),"last")'
                }
            ]
        }
    ]

    def test_load_file_path(self):
        file_path = os.path.join(ROOT_PATH, 'templates', 'graphite', 'check-host-alive.graph')
        template = JSONTemplate(file_path)
        self.assertEqual(template.data, self.data)

    def test_load_bad_path(self):
        file_path = os.path.join(ROOT_PATH, 'templates', 'graphite', 'check_cpu.graph')
        with self.assertRaises(JSONTemplate.NotJsonTemplate):
            JSONTemplate(file_path)

    def test_load_bad_data(self):
        with self.assertRaises(JSONTemplate.NotJsonTemplate):
            JSONTemplate('file_path')

    def test_load_file(self):
        file_path = os.path.join(ROOT_PATH, 'templates', 'graphite', 'check-host-alive.graph')
        template = JSONTemplate(open(file_path, 'rt'))
        self.assertEqual(template.data, self.data)

    def test_load_string(self):
        template = JSONTemplate(json.dumps(self.data))
        self.assertEqual(template.data, self.data)

    def test_fill(self):
        context = dict(host='testhost', service='testservice')
        d = JSONTemplate._fill_template(self.data, context)
        self.assertEqual(d, self.filled)
        self.assertEqual(self.data, self.data)
        self.assertNotEqual(d, self.data)

    def test_load_and_fill(self):
        template = JSONTemplate(json.dumps(self.data))
        context = dict(host='testhost', service='testservice')
        d = template.fill(context)
        self.assertEqual(d, self.filled)
        self.assertEqual(template.data, self.data)
        self.assertNotEqual(d, template.data)


class TestGraphFactory(unittest.TestCase):
    pass


if __name__ == '__main__':
    unittest.main()