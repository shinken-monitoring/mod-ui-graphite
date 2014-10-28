<a href='https://travis-ci.org/shinken-monitoring/mod-ui-graphite'><img src='https://api.travis-ci.org/shinken-monitoring/mod-ui-graphite.svg?branch=master' alt='Travis Build'></a>
mod-ui-graphite
===============

Description
-----------
Shinken module for enabling graphs from Graphite into WebUI

Installation
------------
* `$ shinken install ui-graphite`
* clone the this git repo and copy the module.py file to the **/var/lib/shinken/modules/ui-graphite**(assuming you install shinken lib in default dir)

Bugfix
------------
* fix the incompatible **metric name** derive process with the module graphite of shinken
* fix the incompatible **_GRAPHITE_PRE** and **_GRAPHITE_POST** process with the module graphite of shinken
