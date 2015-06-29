__author__ = 'bjorn'

# fake shinken objects for testing, we only implement what we need for simplicity


class ShinkenObject(object):
    class __metaclass__(type):
        @property
        def my_type(cls):
            return cls.__name__.lower()

    def __init__(self, check):
        self.customs = {}
        self.check_command = check
        self.perf_data = ''

    def add_custom(self, key, value):
        self.customs[key] = value


class CheckCommand(object):
    def __init__(self, name):
        self._name = name

    def get_name(self):
        return self._name


class Host(ShinkenObject):
    def __init__(self, hostname, check):
        ShinkenObject.__init__(self, check)
        self.host_name = hostname
        self.services = []


class Service(ShinkenObject):
    def __init__(self, name, host, check):
        ShinkenObject.__init__(self, check)
        self.host = host
        host.services.append(self)
        self.service_description = name


class ShinkenModuleConfig(object):
    def __init__(self):
        pass

    def set_value(self, key, value):
        setattr(self, key, value)

    def del_value(self, key):
        delattr(self, key)

    def get_value(self, key):
        return getattr(self, key)

    def duplicate(self):
        new = self.__class__()
        new.__dict__ = dict(self.__dict__)
        return new
