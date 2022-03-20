import ipaddress, socket
from sys import argv

def portOverload():
    argvLength = len(argv)
    for i in range(argvLength):
        if argv[i] == '--port' and i != argvLength - 1:
            try:
                port = int(argv[i + 1])
                if port > -1 and port < 65354:
                    return True, port
            except Exception:
                pass
    return False, -1

def localIP(environ, currentIP=None):
    if 'HTTP_X_FORWARDED_FOR' in environ and currentIP != None:
        return environ['HTTP_X_FORWARDED_FOR'] == currentIP
    
    if 'REMOTE_ADDR' in environ:
        try:
            ipObj = ipaddress.ip_address(environ['REMOTE_ADDR'])
        except ValueError:
            return False
        return ipObj.is_private

def getServerIP():
    return socket.gethostbyname(socket.gethostname())
