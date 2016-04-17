import unittest
import urlparse
import sys
import os
import json
import time
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO)

FILE_PATH = os.path.dirname(os.path.realpath(__file__))
ROOT_PATH = os.path.abspath(os.path.join(FILE_PATH, '../'))
sys.path.append(ROOT_PATH)

from module.util import JSONTemplate, GraphFactory, TemplateNotFound
from module.graphite_utils import GraphStyle, GraphiteTarget, GraphiteURL, GraphiteMetric, graphite_time, \
    GraphiteRewriteRule, GraphiteFunction, GraphiteString
from module.module import Graphite_Webui
from fake_shinken import Host, CheckCommand, Service, ShinkenModuleConfig

os.environ["TZ"] = "UTC"

class TestGraphiteTarget(unittest.TestCase):
    def test_empty(self):
        with self.assertRaises(ValueError):
            GraphiteTarget()

    def test_target_only(self):
        t = GraphiteTarget(target='test')
        self.assertEqual(str(t), 'test')

    def test_alias(self):
        t = GraphiteTarget(target='test', alias='test')
        self.assertEqual(str(t), 'alias(test,"test")')

    def test_color(self):
        t = GraphiteTarget(target='test', color='red')
        self.assertEqual(str(t), 'color(test,"red")')

    def test_alias_and_color(self):
        t = GraphiteTarget(target='test', alias='test', color='red')
        self.assertEqual(str(t), 'alias(color(test,"red"),"test")')

    def test_target_from_target(self):
        t1 = GraphiteTarget(target='test', alias='test', color='red')
        t = GraphiteTarget(t1)
        self.assertEqual(t1.__dict__, t.__dict__)
        self.assertEqual(str(t1), 'alias(color(test,"red"),"test")')
        self.assertEqual(str(t), 'alias(color(test,"red"),"test")')

    def test_target_from_target_mod(self):
        t1 = GraphiteTarget(target='test', alias='test', color='red')
        t = GraphiteTarget(t1, alias='Fred', color='yellow')
        self.assertNotEqual(t1.__dict__, t.__dict__)
        self.assertEqual(str(t1), 'alias(color(test,"red"),"test")')
        self.assertEqual(str(t), 'alias(color(test,"yellow"),"Fred")')


class TestGraphiteURL(unittest.TestCase):
    def test_base(self):
        u = GraphiteURL()
        self.assertEqual(u.target_string, '')
        self.assertEqual(u._end, '00:00_19700101')
        self.assertEqual(u._start, '00:00_19700101')
        self.assertEqual(u.url('render'),
                         '/render/?width=586&height=308&fontSize=8&from=00:00_19700101&until=00:00_19700101')
        self.assertEqual(u.url('composer'),
                         '/composer/?width=586&height=308&fontSize=8&from=00:00_19700101&until=00:00_19700101')
        with self.assertRaises(ValueError):
            u.url('test')

    def test_server(self):
        u = GraphiteURL('http://example.com/')
        self.assertEqual(u.target_string, '')
        self.assertEqual(u._end, '00:00_19700101')
        self.assertEqual(u._start, '00:00_19700101')
        self.assertEqual(u.url('render'),
                         'http://example.com/render/?width=586&height=308&fontSize=8&from=00:00_19700101&until=00:00_19700101')
        self.assertEqual(u.url('composer'),
                         'http://example.com/composer/?width=586&height=308&fontSize=8&from=00:00_19700101&until=00:00_19700101')
        with self.assertRaises(ValueError):
            u.url('test')

    def test_min_max(self):
        u = GraphiteURL(min=0, max=100)
        self.assertEqual(u.target_string, '')
        self.assertEqual(u._end, '00:00_19700101')
        self.assertEqual(u._start, '00:00_19700101')
        self.assertEqual(u.url('render'),
                         '/render/?width=586&height=308&fontSize=8&from=00:00_19700101&until=00:00_19700101&yMin=0&yMax=100')
        self.assertEqual(u.url('composer'),
                         '/composer/?width=586&height=308&fontSize=8&from=00:00_19700101&until=00:00_19700101&yMin=0&yMax=100')
        with self.assertRaises(ValueError):
            u.url('test')

    def test_title(self):
        u = GraphiteURL(title="test")
        self.assertEqual(u.target_string, '')
        self.assertEqual(u._end, '00:00_19700101')
        self.assertEqual(u._start, '00:00_19700101')
        self.assertEqual(u.url('render'),
                         '/render/?width=586&height=308&fontSize=8&from=00:00_19700101&until=00:00_19700101&title=test')
        self.assertEqual(u.url('composer'),
                         '/composer/?width=586&height=308&fontSize=8&from=00:00_19700101&until=00:00_19700101&title=test')
        with self.assertRaises(ValueError):
            u.url('test')

    def test_single_target(self):
        u = GraphiteURL(title="test", targets=['test'])
        self.assertEqual(len(u.targets), 1)
        for t in u.targets:
            self.assertIsInstance(t, GraphiteTarget)
        self.assertEqual(u.target_string, 'target=test')
        self.assertEqual(u._end, '00:00_19700101')
        self.assertEqual(u._start, '00:00_19700101')
        self.assertEqual(u.url('render'),
                         '/render/?width=586&height=308&fontSize=8&from=00:00_19700101&until=00:00_19700101&title=test&target=test')
        self.assertEqual(u.url('composer'),
                         '/composer/?width=586&height=308&fontSize=8&from=00:00_19700101&until=00:00_19700101&title=test&target=test')
        with self.assertRaises(ValueError):
            u.url('test')

    def test_multiple_target(self):
        u = GraphiteURL(title="test", targets=['test', 'test2'])
        self.assertEqual(len(u.targets), 2)
        for t in u.targets:
            self.assertIsInstance(t, GraphiteTarget)
        self.assertEqual(u.target_string, 'target=test&target=test2')
        self.assertEqual(u._end, '00:00_19700101')
        self.assertEqual(u._start, '00:00_19700101')
        self.assertEqual(u.url('render'),
                         '/render/?width=586&height=308&fontSize=8&from=00:00_19700101&until=00:00_19700101&title=test&target=test&target=test2')
        self.assertEqual(u.url('composer'),
                         '/composer/?width=586&height=308&fontSize=8&from=00:00_19700101&until=00:00_19700101&title=test&target=test&target=test2')
        with self.assertRaises(ValueError):
            u.url('test')

    def test_add_target(self):
        u = GraphiteURL(title="test", targets=['test'])
        self.assertEqual(len(u.targets), 1)
        u.add_target('test2', alias='Fred')
        self.assertEqual(len(u.targets), 2)
        for t in u.targets:
            self.assertIsInstance(t, GraphiteTarget)
        self.assertEqual(u.target_string, 'target=test&target=alias(test2,"Fred")')
        self.assertEqual(u._end, '00:00_19700101')
        self.assertEqual(u._start, '00:00_19700101')
        self.assertEqual(u.url('render'),
                         '/render/?width=586&height=308&fontSize=8&from=00:00_19700101&until=00:00_19700101&title=test&target=test&target=alias(test2,"Fred")')
        self.assertEqual(u.url('composer'),
                         '/composer/?width=586&height=308&fontSize=8&from=00:00_19700101&until=00:00_19700101&title=test&target=test&target=alias(test2,"Fred")')
        with self.assertRaises(ValueError):
            u.url('test')


class TestGraphiteMetric(unittest.TestCase):
    def test_join(self):
        self.assertEqual(GraphiteMetric.join(''), '')
        self.assertEqual(GraphiteMetric.join('', ''), '')
        self.assertEqual(GraphiteMetric.join('a'), 'a')
        self.assertEqual(GraphiteMetric.join('a', 'b'), 'a.b')
        self.assertEqual(GraphiteMetric.join('a', 'b', 'c'), 'a.b.c')
        self.assertEqual(GraphiteMetric.join('a', 'b.c'), 'a.b.c')
        self.assertEqual(GraphiteMetric.join('a.b', 'c'), 'a.b.c')
        self.assertEqual(GraphiteMetric.join('', 'a', 'b', '1'), 'a.b.1')
        self.assertEqual(GraphiteMetric.join('a', 'b', '', '1'), 'a.b.1')
        self.assertEqual(GraphiteMetric.join('a', 'b', '1', ''), 'a.b.1')
        self.assertEqual(GraphiteMetric.join('a', '', '', '', 'b', '1'), 'a.b.1')

    def test_normalize(self):
        self.assertEqual(GraphiteMetric.normalize('a,,2'), 'a__2')
        self.assertEqual(GraphiteMetric.normalize('a,.2'), 'a_.2')
        self.assertEqual(GraphiteMetric.normalize(',a,2'), '_a_2')
        self.assertEqual(GraphiteMetric.normalize('a,2,'), 'a_2_')


class TestGraphiteTime(unittest.TestCase):
    def test_unixtime_0(self):
        self.assertEqual(graphite_time(0), '00:00_19700101')

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


class TestGraphiteString(unittest.TestCase):
    def test_unquoted_string(self):
        s = GraphiteString('abc')
        self.assertEqual(s.s, 'abc')
        self.assertEqual(str(s), '"abc"')

    def test_quoted_string(self):
        s = GraphiteString('"abc"')
        self.assertEqual(s.s, 'abc')
        self.assertEqual(str(s), '"abc"')


class TestGraphiteFunction(unittest.TestCase):
    def test_simple_fn(self):
        s = GraphiteFunction('average', ['abc', ])
        self.assertEqual(s.name, 'average')
        self.assertEqual(s.args, ['abc', ])
        self.assertEqual(str(s), 'average(abc)')

    def test_string_fn(self):
        t = GraphiteString('abc')
        s = GraphiteFunction('findMetrics', [t, ])
        self.assertEqual(s.name, 'findMetrics')
        self.assertEqual(len(s.args), 1)
        self.assertEqual(s.args[0].s, 'abc')
        self.assertEqual(str(s), 'findMetrics("abc")')

    def test_numeric_fn(self):
        s = GraphiteFunction('average', [10, ])
        self.assertEqual(s.name, 'average')
        self.assertEqual(s.args, [10, ])
        self.assertEqual(str(s), 'average(10)')

    def test_mixed_fn(self):
        t = GraphiteString('test')
        s = GraphiteFunction('average', ['abc', 10, t])
        self.assertEqual(s.name, 'average')
        self.assertEqual(len(s.args), 3)
        self.assertEqual(s.args, ['abc', 10, t])
        self.assertEqual(str(s), 'average(abc,10,"test")')

    def test_nested_fn(self):
        t = GraphiteString('test')
        f = GraphiteString('Fred')
        s = GraphiteFunction('average', ['abc', 10, t])
        s2 = GraphiteFunction('alias', [s, f])
        self.assertEqual(s.name, 'average')
        self.assertEqual(len(s.args), 3)
        self.assertEqual(s.args, ['abc', 10, t])
        self.assertEqual(str(s), 'average(abc,10,"test")')
        self.assertEqual(s2.name, 'alias')
        self.assertEqual(len(s2.args), 2)
        self.assertEqual(s2.args, [s, f])
        self.assertEqual(str(s2), 'alias(average(abc,10,"test"),"Fred")')


class TestGraphiteRewrite(unittest.TestCase):
    def setUp(self):
        GraphiteMetric.rewrite_rules = []

    def test_simple_rewrite(self):
        rule = GraphiteRewriteRule(r'_sum$', '')
        base = 'abcdef'
        r = rule.apply(base)
        self.assertEqual(r, base)
        r = rule.apply('_sum' + base)
        self.assertEqual(r, '_sum' + base)
        r = rule.apply(base + '_sum')
        self.assertEqual(r, base)

    def test_metric_single_rewrite(self):
        self.assertEqual(len(GraphiteMetric.rewrite_rules), 0)
        GraphiteMetric.add_rule('_sum$', '')
        self.assertEqual(len(GraphiteMetric.rewrite_rules), 1)
        base = 'abcdef'
        r = GraphiteMetric.rewrite(base)
        self.assertEqual(r, base)
        r = GraphiteMetric.rewrite('_sum' + base)
        self.assertEqual(r, '_sum' + base)
        r = GraphiteMetric.rewrite(base + '_sum')
        self.assertEqual(r, base)

    def test_metric_multi_rewrite(self):
        self.assertEqual(len(GraphiteMetric.rewrite_rules), 0)
        GraphiteMetric.add_rule('_sum$', '')
        GraphiteMetric.add_rule(r'^(world)', r'hello.\1')
        self.assertEqual(len(GraphiteMetric.rewrite_rules), 2)
        base = 'abcdef'
        r = GraphiteMetric.rewrite(base)
        self.assertEqual(r, base)
        r = GraphiteMetric.rewrite('_sum' + base)
        self.assertEqual(r, '_sum' + base)
        r = GraphiteMetric.rewrite('world' + base)
        self.assertEqual(r, 'hello.world' + base)
        r = GraphiteMetric.rewrite(base + '_sum')
        self.assertEqual(r, base)
        r = GraphiteMetric.rewrite('world' + base + '_sum')
        self.assertEqual(r, 'hello.world' + base)
        pass


class TestGraphFactory(unittest.TestCase):
    def setUp(self):
        self.maxDiff = None
        self.host = Host('testhost', CheckCommand('check-host-alive'))
        self.service_cpu = Service('check_cpu', self.host, CheckCommand('check_cpu'))
        self.service_test = Service('testservice', self.host, CheckCommand('testservice'))
        self.config = ShinkenModuleConfig()
        self.config.set_value('templates_path', os.path.join(ROOT_PATH, 'templates', 'graphite'))
        self.config.set_value('hostcheck', '__HOST__')
        self.config.set_value('uri', 'http://example.com/graphite/')
        self.config.set_value('tz', None)
        self.config.set_value('lineMode', None)
        self.config.set_value('color_warning', None)
        self.config.set_value('color_critical', None)
        self.config.set_value('color_min', None)
        self.config.set_value('color_max', None)
        self.config.set_value('lineMode', None)
        self.config.set_value('graphite_data_source', '')
        self.config.set_value('get_metric_and_value', lambda x, y: [
            {'name': 'testMetric', 'uom': 'msec', 'min': 0, 'max': 3.7, 'critical': 500, 'warning': 600}])
        self.styles = {
            'default': GraphStyle(),
            'detail': GraphStyle(),
            'dashboard': GraphStyle(font_size=4)
        }
        self.config.set_value('styles', self.styles)

    def test_zero_attributes(self):
        def get_name():
            return 'ui-graphite2'

        def get_metric(metrics, name):
            for m in metrics:
                if m['name'] == name:
                    return m
            return None

        self.config.set_value('get_name', get_name)
        self.config.set_value('properties', {})
        wui = Graphite_Webui(self.config)
        metrics = wui.get_metric_and_value(self.service_cpu, "m0=0ms;1.1;2.2;3.3;4.4 " +
                                                             "m1=0ms;0;2.2;3.3;4.4 " +
                                                             "m2=0ms;1.1;0;3.3;4.4 " +
                                                             "m3=0ms;1.1;2.2;0;4.4 " +
                                                             "m4=0ms;1.1;2.2;3.3;0")
        self.assertEqual(5,len(metrics))
        metric = get_metric(metrics, "m0")
        self.assertEqual("m0", metric.get('name'))
        self.assertEqual("ms", metric.get('uom'))
        self.assertEqual(1.1, metric.get('warning'))
        self.assertEqual(2.2, metric.get('critical'))
        self.assertEqual(3.3, metric.get('min'))
        self.assertEqual(4.4, metric.get('max'))

        metric = get_metric(metrics, "m1")
        self.assertEqual("m1", metric.get('name'))
        self.assertEqual("ms", metric.get('uom'))
        self.assertEqual(0, metric.get('warning'))
        self.assertEqual(2.2, metric.get('critical'))
        self.assertEqual(3.3, metric.get('min'))
        self.assertEqual(4.4, metric.get('max'))

        metric = get_metric(metrics, "m2")
        self.assertEqual("m2", metric.get('name'))
        self.assertEqual("ms", metric.get('uom'))
        self.assertEqual(1.1, metric.get('warning'))
        self.assertEqual(0, metric.get('critical'))
        self.assertEqual(3.3, metric.get('min'))
        self.assertEqual(4.4, metric.get('max'))

        metric = get_metric(metrics, "m3")
        self.assertEqual("m3", metric.get('name'))
        self.assertEqual("ms", metric.get('uom'))
        self.assertEqual(1.1, metric.get('warning'))
        self.assertEqual(2.2, metric.get('critical'))
        self.assertEqual(0, metric.get('min'))
        self.assertEqual(4.4, metric.get('max'))

        metric = get_metric(metrics, "m4")
        self.assertEqual("m4", metric.get('name'))
        self.assertEqual("ms", metric.get('uom'))
        self.assertEqual(1.1, metric.get('warning'))
        self.assertEqual(2.2, metric.get('critical'))
        self.assertEqual(3.3, metric.get('min'))
        self.assertEqual(0, metric.get('max'))

    def test_host_json_template(self):
        fact = GraphFactory(self.host, 0, 140000, source='dashboard', log=logging, cfg=self.config)
        self.assertEqual(fact.prefix, '')
        self.assertEqual(fact.postfix, '')
        self.assertEqual(fact.template_path, os.path.join(self.config.templates_path, 'check-host-alive.graph'))
        self.assertEqual(fact.hostname, 'testhost')
        self.assertEqual(fact.servicename, self.config.hostcheck)
        self.assertEqual(fact.element_type, 'host')
        self.assertEqual(fact.style, self.styles['dashboard'])
        self.assertEqual(fact.get_style('test'), self.styles['default'])
        uris = fact.get_graph_uris()
        self.assertEqual(len(uris), 2)
        self.assertEqual(uris[0], {
            'link': 'http://example.com/graphite/composer/?width=586&height=308&fontSize=4&from=00:00_19700101&until=14:53_19700102&title=Response Time on testhost&yMin=0&target=legendValue(alias(testhost.__HOST__.rta,"Response Time"),"last")',
            'img_src': 'http://example.com/graphite/render/?width=586&height=308&fontSize=4&from=00:00_19700101&until=14:53_19700102&title=Response Time on testhost&yMin=0&target=legendValue(alias(testhost.__HOST__.rta,"Response Time"),"last")'
        })
        self.assertEqual(uris[1], {
            'link': 'http://example.com/graphite/composer/?width=586&height=308&fontSize=4&from=00:00_19700101&until=14:53_19700102&title=Packet Loss Percentage on testhost&yMin=0&yMax=100&target=legendValue(alias(testhost.__HOST__.pl,"Packet loss percentage"),"last")',
            'img_src': 'http://example.com/graphite/render/?width=586&height=308&fontSize=4&from=00:00_19700101&until=14:53_19700102&title=Packet Loss Percentage on testhost&yMin=0&yMax=100&target=legendValue(alias(testhost.__HOST__.pl,"Packet loss percentage"),"last")'
        })

    def test_service_url_template(self):
        fact = GraphFactory(self.service_cpu, 0, 140000, source='detail', log=logging, cfg=self.config)
        self.assertEqual(fact.prefix, '')
        self.assertEqual(fact.postfix, '')
        self.assertEqual(fact.template_path, os.path.join(self.config.templates_path, 'check_cpu.graph'))
        with self.assertRaises(JSONTemplate.NotJsonTemplate):
            fact._parse_json_template(fact.template_path)
        self.assertEqual(fact.hostname, 'testhost')
        self.assertEqual(fact.servicename, 'check_cpu')
        self.assertEqual(fact.element_type, 'service')
        self.assertEqual(fact.style, self.styles['detail'])
        self.assertEqual(fact.get_style('test'), self.styles['default'])
        uris = fact.get_graph_uris()
        self.assertEqual(len(uris), 1)
        self.assertEqual(uris[0], {
            'link': '''http://example.com/graphite/composer/?width=586&height=308&fontSize=8&fgcolor=000000&bgcolor=FFFFFF&areaMode=stacked&yMax=100&target=alias(legendValue(testhost.check_cpu._user_,"last"),"User")&target=alias(legendValue(testhost.check_cpu._sys_,"last"),"Sys")&target=alias(legendValue(testhost.check_cpu._softirq_,"last"),"SoftIRQ")&target=alias(legendValue(testhost.check_cpu._nice_,"last"),"Nice")&target=alias(legendValue(testhost.check_cpu._irq_,"last"),"IRQ")&target=alias(legendValue(testhost.check_cpu._iowait_,"last"),"I/O Wait")&target=alias(legendValue(testhost.check_cpu._idle_,"last"),"Idle")''',
            'img_src': '''http://example.com/graphite/render/?width=586&height=308&fontSize=8&fgcolor=000000&bgcolor=FFFFFF&areaMode=stacked&yMax=100&target=alias(legendValue(testhost.check_cpu._user_,"last"),"User")&target=alias(legendValue(testhost.check_cpu._sys_,"last"),"Sys")&target=alias(legendValue(testhost.check_cpu._softirq_,"last"),"SoftIRQ")&target=alias(legendValue(testhost.check_cpu._nice_,"last"),"Nice")&target=alias(legendValue(testhost.check_cpu._irq_,"last"),"IRQ")&target=alias(legendValue(testhost.check_cpu._iowait_,"last"),"I/O Wait")&target=alias(legendValue(testhost.check_cpu._idle_,"last"),"Idle")'''
        })

    def test_service_generate(self):
        fact = GraphFactory(self.service_test, 0, 140000, source='fake', log=logging, cfg=self.config)
        self.assertEqual(fact.prefix, '')
        self.assertEqual(fact.postfix, '')
        with self.assertRaises(TemplateNotFound):
            logging.warning(fact.template_path)
        self.assertEqual(fact.hostname, 'testhost')
        self.assertEqual(fact.servicename, 'testservice')
        self.assertEqual(fact.element_type, 'service')
        self.assertEqual(fact.style, self.styles['default'])
        self.assertEqual(fact.get_style('test'), self.styles['default'])
        uris = fact.get_graph_uris()
        self.assertEqual(len(uris), 1)
        self.assertEqual(uris[0], {
            'link': 'http://example.com/graphite/composer/?width=586&height=308&fontSize=8&from=00:00_19700101&until=14:53_19700102&title=testhost/testservice - testMetric&target=alias(constantLine(600),"Warning")&target=alias(constantLine(500),"Critical")&target=alias(constantLine(0),"Min")&target=alias(constantLine(3.7),"Max")&target=alias(color(testhost.testservice.testMetric,"green"),"testMetric")',
            'img_src': 'http://example.com/graphite/render/?width=586&height=308&fontSize=8&from=00:00_19700101&until=14:53_19700102&title=testhost/testservice - testMetric&target=alias(constantLine(600),"Warning")&target=alias(constantLine(500),"Critical")&target=alias(constantLine(0),"Min")&target=alias(constantLine(3.7),"Max")&target=alias(color(testhost.testservice.testMetric,"green"),"testMetric")'
        })

    def test_service_generate_graphite_path_mods(self):
        fact = GraphFactory(self.service_test, 0, 140000, source='fake', log=logging, cfg=self.config)
        self.config.graphite_data_source = 'shinken'
        self.service_test.add_custom('_GRAPHITE_PRE', 'joe')
        self.service_test.add_custom('_GRAPHITE_POST', 'FRED')
        self.host.add_custom('_GRAPHITE_PRE', 'frank')
        self.host.add_custom('_GRAPHITE_POST', 'foo')
        self.assertEqual(fact.prefix, 'frank')
        self.assertEqual(fact.postfix, 'FRED')
        with self.assertRaises(TemplateNotFound):
            logging.warning(fact.template_path)
        self.assertEqual(fact.hostname, 'testhost')
        self.assertEqual(fact.servicename, 'testservice')
        self.assertEqual(fact.element_type, 'service')
        self.assertEqual(fact.style, self.styles['default'])
        self.assertEqual(fact.get_style('test'), self.styles['default'])
        uris = fact.get_graph_uris()
        self.assertEqual(len(uris), 1)
        self.assertEqual(uris[0], {
            'link': 'http://example.com/graphite/composer/?width=586&height=308&fontSize=8&from=00:00_19700101&until=14:53_19700102&title=testhost/testservice - testMetric&target=alias(constantLine(600),"Warning")&target=alias(constantLine(500),"Critical")&target=alias(constantLine(0),"Min")&target=alias(constantLine(3.7),"Max")&target=alias(color(frank.testhost.shinken.testservice.testMetric.FRED,"green"),"testMetric")',
            'img_src': 'http://example.com/graphite/render/?width=586&height=308&fontSize=8&from=00:00_19700101&until=14:53_19700102&title=testhost/testservice - testMetric&target=alias(constantLine(600),"Warning")&target=alias(constantLine(500),"Critical")&target=alias(constantLine(0),"Min")&target=alias(constantLine(3.7),"Max")&target=alias(color(frank.testhost.shinken.testservice.testMetric.FRED,"green"),"testMetric")'
        })


if __name__ == '__main__':
    unittest.main()
