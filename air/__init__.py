import struct
import json
import zlib


class airDataManager(object):

    def __init__(self):
        self.users = []
        self.files = []
        self.bundles = []

class airBundle(object):
    def __init__(self, data, sender=None):
        self.__sender = sender
        self.__obj = {}
        self.__isValid = False

        if type(data).__name__ == 'dict':
            self.__obj = data

        else:
            if len(data) >= struct.calcsize('>LL'):
                (signature, crc32) = struct.unpack('>LL', data[:8])

                tail = data[8:]

                if zlib.crc32(tail) & 0xffffffff == crc32:
                    self.__obj = json.loads(tail)

                    self.__isValid = True

    def compile(self):
        json_data = json.dumps(self.__obj)

        head = struct.pack('>LL', 0xDEADBABA, zlib.crc32(json_data) & 0xffffffff )

        return head + json_data

    def is_valid(self):
        return self.__isValid

    def setAfterSend(self, func):
        self.afterSend = func

    def getSender(self):
        return self.__sender

    def __getattr__(self, item):
        return self.__obj.get(item)

    def __str__(self):
        return json.dumps(self.__obj)
