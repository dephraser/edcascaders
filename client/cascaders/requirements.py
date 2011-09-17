

class RequireFunctions:
    '''
    This is a brute force attempt at running functions that require
    other functioins to have been run first

    As said, this is nasty and brute force, there are much nicer ways
    to do it
    '''

    def __init__(self):
        self.lists = []

    def _removeFromAllReq(self, remove):
        for name, function, req in self.lists:
            try:
                req.remove(remove)
            except ValueError:
                pass

    def _runOnce(self):
        for i, (name, function, req) in enumerate(self.lists):
            if len(req) == 0:
                function()
                self._removeFromAllReq(name)
                self.lists.pop(i)
                return True
        return False

    def add(self, name, function, requirements = []):
        self.lists.append((name, function, requirements))

    def run(self):
        while True:
            if len(self.lists) == 0:
                return
            if not self._runOnce():
                raise Exception('Circular depenency detected')
