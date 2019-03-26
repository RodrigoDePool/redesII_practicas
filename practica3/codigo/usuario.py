
class Usuario:
    APP_USER=None

    def __init__(self, nick, tcpPort, udp_port):
        self.nick = nick
        self.tcpPort = tcpPort
        self.udp_port = udp_port
