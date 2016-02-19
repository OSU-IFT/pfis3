from algorithmPFISBase import PFISBase
from collections import deque

class PFISTouchOnce(PFISBase):
        
    def __init__(self, langHelper, name, fileName, history=False, goal = [], \
                 stopWords = [], decayFactor = 0.85, decayHistory = 0.9, \
                 numSpread = 1, includeTop = False):
        PFISBase.__init__(self, langHelper, name, fileName, history, goal, 
                          stopWords, decayFactor, decayHistory, includeTop)
        self.history = history
        self.goal = goal
        self.stopWords = stopWords
        self.DECAY_FACTOR = decayFactor
        self.DECAY_HISTORY = decayHistory
        self.NUM_SPREAD = numSpread
        self.mapNodesToActivation = None
        self.NUM_SPREAD = numSpread
                     
    def spreadActivation(self, pfisGraph):
        queue = deque()
        
        for node in self.mapNodesToActivation:
            queue.append(node)
        
        while len(queue) > 0:
            currentNode = queue.popleft()
            neighbors = pfisGraph.graph.neighbors(currentNode)
            edgeWeight = 1.0 / len(neighbors)
            
            for neighbor in neighbors:
                if neighbor not in self.mapNodesToActivation:
                    self.mapNodesToActivation[neighbor] = (self.mapNodesToActivation[node] * edgeWeight * self.DECAY_FACTOR)
                    queue.append(neighbor)
                    