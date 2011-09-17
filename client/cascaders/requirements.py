from collections import defaultdict

class RequireFunctions:
    '''
    Used to create a graph of functions that depend on other functions
    having been run and then correctly run the functions
    '''

    def __init__(self):
        self.resetState()

    def resetState(self):
        self.edges = defaultdict(list)
        self.readyNodes = []
        self.nodeCount = 0

    def add(self, name, function, requirements = []):
        '''
        Add a function to be run

        name - name of the thing to be run
        function - function itself
        requirements - other things that this function depends on
        '''
        node = (name, function, requirements)
        self.nodeCount += 1
        if len(requirements) == 0:
            self.readyNodes.append(node)
        else:
            for req in requirements:
                self.edges[req].append(node)

    def run(self):
        '''
        Topological sort is used to run all functions in the correct order
        '''
        doneCount = 0
        while len(self.readyNodes):
            name, function, _ = self.readyNodes.pop(0)
            function()
            doneCount += 1 
            for node in self.edges[name]:
                node[2].remove(name)
                if len(node[2]) == 0:
                    self.readyNodes.append(node)
        if self.nodeCount != doneCount:
            raise ValueError('Cycle in graph detected, not all functions run')
        self.resetState()
