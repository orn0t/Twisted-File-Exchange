#!/usr/bin/python

import struct
import json
import time

from twisted.internet.protocol import DatagramProtocol, ClientFactory, Protocol, connectionDone
from twisted.internet.endpoints import TCP4ServerEndpoint

from twisted.internet.task import LoopingCall
from twisted.internet import reactor


from service import airTelnetFactory
from air import airDataManager, airBundle

dataManager = airDataManager()

class airCargo(object):
    def __init__(self, data):
        self.__file_id = data['file_id']
        self.__filename = data['filename']
        self.__size = data['size']
        self.__sender = data['sender']
        self.__ready = 0

        self.__buff = ''

        self.__connection = None
        self.__fp = None



    def download(self):
        self.__fp = open('/tmp/' + str(time.time()) + self.__filename, 'wb')

        reactor.connectTCP(self.__sender, 9999, airCargoFactory({
            'onReceive': self.onReceive,
            'onConnect': self.onConnect,
            'onClose': self.onClose,
        }))

    def onReceive(self, data):

        self.__ready += len(data)

        self.__buff += data

        if self.__ready >= self.__size and self.__connection is not None:
            self.__connection.transport.loseConnection()

    def onClose(self, data):
        jsonSize = struct.unpack('>h', self.__buff[:2])
        head = jsonSize[0] + 2

        self.__fp.write(self.__buff[head:])

        self.__fp.close()

    def onConnect(self, connection):
        jsonData = json.dumps({'fileid': self.__file_id, 'from': 0, 'to': self.__size})
        raw = struct.pack('>h', len(jsonData)) + jsonData

        connection.transport.write(raw)

    def getID(self):
        return self.__file_id

    def getSender(self):
        return self.__sender

    def getName(self):
        return self.__filename

class airCargoDownloader(Protocol):

    def __init__(self, callbacks):
        self.__callbacks = callbacks

    def dataReceived(self, data):
        self.__callbacks['onReceive'].__call__(data)

    def connectionMade(self):
        self.__callbacks['onConnect'].__call__(self)

    def connectionLost(self, reason=connectionDone):
        self.__callbacks['onClose'].__call__(reason)

class airCargoFactory(ClientFactory):
    def __init__(self, callbacks):
        self.__callbacks = callbacks

    def buildProtocol(self, addr):
        return airCargoDownloader(self.__callbacks)

class airReceiver(DatagramProtocol):

    def __init__(self):
        self.__loopHeartBeat = None
        self.__loopResponse = None

    def datagramReceived(self, data, (host, port)):
        pack = airBundle(data)

        if pack.is_valid():
            if 'iamalive' == pack.type:
                found = False
                for user in dataManager.users:
                    if pack.name == user['name']:
                        user['up'] = time.time()
                        found = True

                    elif time.time() - user['up'] > 5000:
                        dataManager.users.remove(user)

                if not found:
                    dataManager.users.append({'name': pack.name, 'up': time.time(), 'ip': host})

            elif 'send-file' == pack.type:
                found = False
                for f in dataManager.files:
                    if pack.file_id == f.getID():
                        found = True
                        break

                if not found:
                    dataManager.files.append(airCargo({
                        'file_id': pack.file_id,
                        'filename': pack.filename,
                        'sender': host,
                        'size': pack.size
                    }))

    def sendHeartBeat(self):
        beatPack = airBundle({'type': 'iamalive', 'name': 'or.n0t'})

        self.transport.write(beatPack.compile(), ('<broadcast>', 9999))

    def sendResponse(self):
        while len(dataManager.bundles) > 0:
            response = dataManager.bundles.pop()

            self.transport.write(response.compile(), (response.getSender(), 9999))

            response.afterSend.__call__()

    def startProtocol(self):
        self.transport.setBroadcastAllowed(True)

        self.__loopHeartBeat = LoopingCall(self.sendHeartBeat)
        self.__loopHeartBeat.start(1)

        self.__loopResponse = LoopingCall(self.sendResponse)
        self.__loopResponse.start(1)

    def stopProtocol(self):
        pass

reactor.listenUDP(9999, airReceiver())

endpoint = TCP4ServerEndpoint(reactor, 2233)
endpoint.listen(airTelnetFactory(dataManager))

reactor.run()