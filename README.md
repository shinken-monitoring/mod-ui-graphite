
UI-Graphite2 module
=====================

Shinken module for viewing Graphite graphs in the Web UI, version 2

This version is a refactoring of the previous ui-graphite module which allows:

   - improve configuration features:
      - configure host check metric name
      - define graph and font size for dashboard anf element page graphs
      - allow to define if warning, critical, min and max thresholds are present on graphs
      - allow to define warning, critical, min and max lines colors
      - define graphs timezone (default is Europe/Paris)
      - define graphs line mode (connected, staircase, slope)

This module is fully compatible with the graphite2 broker module and with the WebUI2.

Installation
--------------------------------
```
   su - shinken

   shinken install ui-graphite2
```

Configuration
--------------------------------

```
   vi /etc/shinken/modules/webui2.cfg

   => modules ui-graphite2
```

Run
--------------------------------
```
   su -
   /etc/init.d/shinken restart
```

Hosts specific configuration
--------------------------------
The `_GRAPHITE_PRE` and `_GRAPHITE_GROUP` defined in the hosts configuration are used to prefix the requested metrics.


Services specific configuration
--------------------------------
The `_GRAPHITE_POST` defined in the services configuration are used to postfix the requested metrics.
