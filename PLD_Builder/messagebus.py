#!/usr/bin/python
# I would name this file as fedmsg,
# but don't know how to import 'fedmsg' from system dir and from local dir

import fedmsg
import fedmsg.config

config = fedmsg.config.load_config([], None)
config['active'] = True
config['endpoints']['relay_inbound'] = config['relay_inbound']
fedmsg.init(name='relay_inbound', cert_prefix='builder', **config)

def notify(topic, **kwargs):
    fedmsg.publish(
        topic=topic,
        msg=dict(kwargs),
        modname="builder",
    )
