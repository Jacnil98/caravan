import os
import socket
import network
import time
import websocket_helper
from time import sleep
from ws_connection import WebSocketConnection, ClientClosedError

class WebSocketClient:
    def __init__(self, conn):
        self.connection = conn

    def process(self):
        pass


class WebSocketServer:
    def __init__(self, page, max_connections=1):
        self._listen_s = None
        self._clients = []
        self._max_connections = max_connections
        self._page = page
        self.ip = None

    def _setup_conn(self, port, accept_handler):
        self._listen_s = socket.socket()
        self._listen_s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        ai = socket.getaddrinfo("0.0.0.0", port)
        addr = ai[0][4]

        self._listen_s.bind(addr)
        self._listen_s.listen(1)
        if accept_handler:
            self._listen_s.setsockopt(socket.SOL_SOCKET, 20, accept_handler)
        for i in (network.AP_IF, network.STA_IF):
            iface = network.WLAN(i)
            if iface.active():
                #print("WebSocket started on ws://%s:%d" % (iface.ifconfig()[0], port))
                self.ip = iface.ifconfig()[0]

    def _accept_conn(self, listen_sock):
        cl, remote_addr = listen_sock.accept()
        print("Client connection from:", remote_addr)

        if len(self._clients) >= self._max_connections:
            # Maximum connections limit reached
            cl.setblocking(True)
            cl.sendall("HTTP/1.1 503 Too many connections\n\n")
            cl.sendall("\n")
            #TODO: Make sure the data is sent before closing
            sleep(0.1)
            cl.close()
            return

        try:
            websocket_helper.server_handshake(cl)
        except OSError:
            # Not a websocket connection, serve webpage
            self._serve_page(cl)
            return

        self._clients.append(self._make_client(WebSocketConnection(remote_addr, cl, self.remove_connection)))

    def _make_client(self, conn):
        return WebSocketClient(conn)

    def _serve_page(self, sock):
        try:
            sock.sendall('HTTP/1.1 200 OK\nConnection: close\nServer: WebSocket Server\nContent-Type: text/html\n')
            length = os.stat(self._page)[6]
            sock.sendall('Content-Length: {}\n\n'.format(length))
            # Process page by lines to avoid large strings
            with open(self._page, 'r') as f:
                for line in f:
                    sock.sendall(line)
        except OSError:
            # Error while serving webpage
            pass
        sock.close()

    def stop(self):
        if self._listen_s:
            self._listen_s.close()
        self._listen_s = None
        for client in self._clients:
            client.connection.close()
        #print("Stopped WebSocket server.")

    def start(self, port=80):
        if self._listen_s:
            self.stop()
        self._setup_conn(port, self._accept_conn)
        #print("Started WebSocket server.")

    def process_all(self, pitch, roll, tilt, in_temp, out_temp, version):
        for client in self._clients:
            client.process(pitch, roll, tilt, in_temp, out_temp, version)

    def send_something(self):
        for client in self._clients:
            client.connection.write(str(time.ticks_ms()))

    def remove_connection(self, conn):
        for client in self._clients:
            if client.connection is conn:
                self._clients.remove(client)
                return

# Define a WebSocket server that creates instances of the ValueGenerator client
class AppServer(WebSocketServer):
    def __init__(self, ssid, password):
        super().__init__("percentage.html", 10)
        self.ssid = ssid
        self.password = password
        self.try_connect()

    def _make_client(self, conn):
        return ValueGenerator(conn)
    
    # Define a function to connect to the Wi-Fi network
    def try_connect(self):
        wlan = network.WLAN(network.STA_IF)
        wlan.active(True)
        wlan.connect(self.ssid, self.password)
        wlan.config(pm = 0xa11140)
        self.start(3000)
        # Wait until the Wi-Fi connection is established
        while True:
            if wlan.status() < 0 or wlan.status() >= 3:
                return
            time.sleep(1)

# Define a WebSocket client that sends accelerometer data over the connection
class ValueGenerator(WebSocketClient):
    def __init__(self, conn):
        super().__init__(conn)

    def process(self, pitch, roll, tilt, in_temp, out_temp, version):
        # Write the pitch and roll angles to the WebSocket connection
        self.connection.write("{:.1f},{:.1f},{:.0f},{:.0f},{:.0f},{:.1f}".format(pitch, roll, tilt, in_temp, out_temp, version))
