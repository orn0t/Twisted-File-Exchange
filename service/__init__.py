import json

from twisted.internet.protocol import Factory
from twisted.protocols.basic import LineReceiver

from air import airBundle

class airTelnet(LineReceiver):
    def __init__(self, dataManager):
        self.__dataManager = dataManager

    def connectionMade(self):
        self.sendLine("Wellcome to or.n0t AirDropKiller console \n\n")

    def lineReceived(self, line):
        parts = line.split(' ')
        (command, args) = (parts[0], parts[1:])

        if 'exit' == command:
            self.transport.loseConnection()

        elif 'users' == command:
            self.sendLine(json.dumps(self.__dataManager.users))

        elif 'remove' == command:
            for user in self.__dataManager.users:
                if args[0] == user['name']:
                    self.__dataManager.users.remove(user)

        elif 'files' == line:
            fff = []
            for f in self.__dataManager.files:
                fff.append( str(f.getID()) + ':' + f.getName())
            self.sendLine(json.dumps(fff))

        elif 'confirm' == command:
            for f in self.__dataManager.files:
                if f.getID() == int(args[0]):
                    bundle = airBundle({'type': 'confirm', 'id': f.getID()}, f.getSender())
                    bundle.setAfterSend(f.download)

                    self.__dataManager.bundles.append(bundle)

class airTelnetFactory(Factory):
    def __init__(self, dataManager):
        self.__dataManager = dataManager

    def buildProtocol(self, addr):
        return airTelnet(self.__dataManager)