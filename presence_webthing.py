import sys
import logging
import tornado.ioloop
from typing import Dict
from webthing import (MultipleThings, Property, Thing, Value, WebThingServer)
from presence import Presence, IpPresence, Presences
from redzoo.math.display import duration



class PresenceThing(Thing):

    # regarding capabilities refer https://iot.mozilla.org/schemas
    # there is also another schema registry http://iotschema.org/docs/full.html not used by webthing

    def __init__(self, description: str, presence: Presence):
        Thing.__init__(
            self,
            'urn:dev:ops:presence-1',
            'presence_' + presence.name,
            ['MultiLevelSensor'],
            description
        )
        self.ioloop = tornado.ioloop.IOLoop.current()
        self.presence = presence
        self.presence.add_listener(self.on_value_changed)

        self.name = Value(presence.name)
        self.add_property(
            Property(self,
                     'name',
                     self.name,
                     metadata={
                         'title': 'name',
                         "type": "string",
                         'description': 'the device name',
                         'readOnly': True,
                     }))

        self.addr = Value(presence.addr)
        self.add_property(
            Property(self,
                     'addr',
                     self.addr,
                     metadata={
                         'title': 'addr',
                         "type": "string",
                         'description': 'the device address',
                         'readOnly': True,
                     }))

        self.last_time_presence = Value(presence.last_time_presence.strftime("%Y-%m-%dT%H:%M"))
        self.add_property(
            Property(self,
                     'last_time_presence_utc',
                     self.last_time_presence,
                     metadata={
                         'title': 'last_time_presence_utc',
                         "type": "string",
                         'description': 'the last time presence ISO8601 string (UTC)',
                         'readOnly': True,
                     }))

        self.elapsed_since_last_seen = Value(duration(presence.age_sec, 1))
        self.add_property(
            Property(self,
                     'elapsed_since_last_seen',
                     self.elapsed_since_last_seen,
                     metadata={
                         'title': 'elapsed_since_last_seen',
                         "type": "string",
                         'description': 'elapsed time since last seen',
                         'readOnly': True,
                     }))


    def on_value_changed(self):
        self.ioloop.add_callback(self._on_value_changed)

    def _on_value_changed(self):
        self.last_time_presence.notify_of_external_update(self.presence.last_time_presence.strftime("%Y-%m-%dT%H:%M"))
        self.elapsed_since_last_seen.notify_of_external_update(duration(self.presence.age_sec, 1))


def run_server(description: str, port: int, name_address_map: Dict[str, str]):
    if len(name_address_map) < 2:
        presences = [IpPresence("presence_" + dev_name, name_address_map[dev_name]) for dev_name in name_address_map.keys()]
    else:
        presences = [IpPresence("presence_" + dev_name, name_address_map[dev_name]) for dev_name in name_address_map.keys()]
        presences = [Presences("presence_all", presences)] + presences
    shutters_tings = [PresenceThing(description, presence) for presence in presences]
    server = WebThingServer(MultipleThings(shutters_tings, "presence"), port=port, disable_host_validation=True)
    try:
        logging.info('starting the server http://localhost:' + str(port))
        [presence.start() for presence in presences]
        server.start()
    except KeyboardInterrupt:
        logging.info('stopping the server')
        [presence.stop() for presence in presences]
        server.stop()
        logging.info('done')



def parse_devices(config: str) -> Dict[str, str]:
    name_address_map = {}
    for device in config.split("&"):
        name, address = device.split('=')
        name_address_map[name.strip()] = address.strip()
    return name_address_map


if __name__ == '__main__':
    logging.basicConfig(format='%(asctime)s %(name)-20s: %(levelname)-8s %(message)s', level=logging.INFO, datefmt='%Y-%m-%d %H:%M:%S')
    logging.getLogger('tornado.access').setLevel(logging.ERROR)
    logging.getLogger('urllib3.connectionpool').setLevel(logging.WARNING)
    run_server("description", int(sys.argv[1]), parse_devices(sys.argv[2]))
