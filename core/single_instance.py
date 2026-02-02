from PyQt6.QtNetwork import QLocalServer, QLocalSocket

APP_ID = "DynamicAppLauncherSingleInstance"

class SingleInstance:
    def __init__(self):
        self.server = None

    def is_running(self):
        # Try to connect to existing server
        socket = QLocalSocket()
        socket.connectToServer(APP_ID)
        if socket.waitForConnected(100):
            # Already running
            socket.write(b"ACTIVATE")
            socket.flush()
            socket.waitForBytesWritten(100)
            socket.disconnectFromServer()
            return True
        return False

    def start_server(self, callback):
        # Start server to listen for new instance messages
        self.server = QLocalServer()
        try:
            # remove any leftover from crashed instance
            QLocalServer.removeServer(APP_ID)
        except Exception:
            pass

        self.server.listen(APP_ID)

        self.server.newConnection.connect(lambda: self.on_new_connection(callback))

    def on_new_connection(self, callback):
        # Called when second instance tries to connect
        socket = self.server.nextPendingConnection()
        if socket:
            socket.waitForReadyRead(100)
            data = socket.readAll().data()
            if data == b"ACTIVATE":
                callback()
            socket.disconnectFromServer()
