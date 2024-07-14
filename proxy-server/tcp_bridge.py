import select
import socket
from struct import pack
import threading
from scapy.all import *
from scapy.all import sniff, IP, TCP


def threaded(fn):
    def wrapper(*args, **kwargs):
        _thread = threading.Thread(target=fn, args=args, kwargs=kwargs)
        _thread.start()
        return _thread

    return wrapper


class TCPBridge(object):

    def __init__(self, host, port, dst_host, dst_port):
        self.host = host
        self.port = port
        self.dst_host = dst_host
        self.dst_port = dst_port

        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server.settimeout(1)
        self.server.bind((self.host, self.port))
        self.stop = False

    @threaded
    def tunnel(self, sock: socket.socket, sock2: socket.socket, chunk_size=1024):
        try:
            while not self.stop:
                # this line is for raising exception when connection is broken
                sock.getpeername() and sock2.getpeername()
                r, w, x = select.select([sock, sock2], [], [], 1000)
                if sock in r:
                    data = sock.recv(chunk_size)
                    if len(data) == 0:
                        break
                    sock2.sendall(data)

                if sock2 in r:
                    data = sock2.recv(chunk_size)
                    if len(data) == 0:
                        break
                    sock.sendall(data)
        except:
            pass
        try:
            sock2.close()
        except:
            pass
        try:
            sock.close()
        except:
            pass

    def run(self) -> None:
        self.server.listen()

        while not self.stop:
            try:
                (sock, addr) = self.server.accept()
                if sock is None:
                    continue
                client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                client_socket.connect((self.dst_host, self.dst_port))
                self.tunnel(sock, client_socket)
            except KeyboardInterrupt:
                self.stop = True
            except TimeoutError as exp:
                pass
            except Exception as exp:
                print("Exception:", exp)


PROXY_IP = "192.168.44.131"
PROXY_PORT = 8080  # Example proxy port


def modify_and_forward(packet):
    if packet.haslayer(IP) and packet.haslayer(TCP):
        if packet[IP].dst == "192.168.44.130" and packet[TCP].dport == 80:
            # Change the destination IP to the proxy IP
            packet[IP].dst = PROXY_IP
            # Change the destination port to the proxy port
            packet[TCP].dport = PROXY_PORT

            # Delete checksums so Scapy recalculates them
            del packet[IP].chksum
            del packet[TCP].chksum

            # Forward the modified packet
            sendp(packet)


if __name__ == "__main__":
    # TODO:change destonation ip
    tcp_bridge = TCPBridge("0.0.0.0", 8082, "192.168.44.130", 80)
    tcp_bridge.run()
    sniff(filter="ip and tcp", prn=modify_and_forward)
