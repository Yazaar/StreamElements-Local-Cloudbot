class Webhook:
    def __init__(self, method : str, data : str | None, secret : str):
        self.data = data
        self.method = method
        self.secret = secret
    
    def legacy(self):
        return (self.secret, self.data)

class CrossTalk:
    def __init__(self, data):
        self.data = data
    
    def legacy(self):
        return (self.data, )