import logging
from threading import Thread
from time import sleep
from datetime import datetime, timedelta
from abc import ABC, abstractmethod
from typing import List
from scapy.all import IP, ICMP, sr



class Presence(ABC):

    def __init__(self, name: str, addr: str):
        self.name = name
        self.addr = addr
        self.__listeners = set()

    def add_listener(self, listener):
        self.__listeners.add(listener)

    @property
    @abstractmethod
    def last_time_presence(self) -> datetime:
        pass

    @property
    def age_sec(self) -> int:
        return int((datetime.utcnow() - self.last_time_presence).total_seconds())

    def _notify_listeners(self):
        [listener() for listener in self.__listeners]

    def start(self):
        pass

    def stop(self):
        pass



class IpPresence(Presence):

    def __init__(self, name: str, addr: str):
        self.__is_running = True
        self.addr = addr
        self.__last_time_presence = datetime.now() - timedelta(days=365)
        super().__init__(name, addr)
        self.__check()

    @property
    def last_time_presence(self) -> datetime:
        return self.__last_time_presence

    def __check(self):
        if self.ping() > 0:
            self.__last_time_presence = datetime.utcnow()
        self._notify_listeners()

    def ping(self, count: int = 10):
        successful_pings = 0
        for i in range(count):
            ping_packet = IP(dst=self.addr) / ICMP()
            response, _ = sr(ping_packet, timeout=2, verbose=False)
            if response:
                successful_pings += 1
        return successful_pings

    def start(self):
        Thread(target=self.__check_loop, daemon=True).start()

    def stop(self):
        self.__is_running = False

    def __check_loop(self):
        while self.__is_running:
            try:
                self.__check()
                sleep(6.03)
            except Exception as e:
                logging.warning("error occurred on check " + str(e))
                sleep(3)


class Presences(Presence):

    def __init__(self, name: str, presences: List[Presence]):
        self.__is_running = True
        self.__presences = presences
        [presence.add_listener(self.__notify) for presence in presences]
        super().__init__(name, "all")

    @property
    def last_time_presence(self) -> datetime:
        last_date_presence = datetime.now() - timedelta(days=365)
        for presence in self.__presences:
            if presence.last_time_presence > last_date_presence:
                last_date_presence = presence.last_time_presence
        return last_date_presence

    def __notify(self):
        self._notify_listeners()