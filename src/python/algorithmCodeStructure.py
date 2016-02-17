from predictiveAlgorithm import PredictiveAlgorithm
from predictions import PredictionEntry
from collections import deque

class CodeStructure(PredictiveAlgorithm):
        
    def __init__(self, langHelper, name, edgeTypes):
        PredictiveAlgorithm.__init__(self, langHelper, name)
        self.edgeTypes = edgeTypes
        self.nodeDistances = None
        
    def makePrediction(self, pfisGraph, navPath, navNumber):
        if navNumber < 1 or navNumber >= navPath.getLength():
            raise RuntimeError('makePrediction: navNumber must be > 0 and less than the length of navPath') 
        
        navToPredict = navPath.navigations[navNumber]
        fromMethodFqn = navToPredict.fromFileNav.methodFqn
        methodToPredict = navToPredict.toFileNav.methodFqn
        self.nodeDistances = {}
        
        if not navToPredict.isToUnknown() and methodToPredict in pfisGraph.graph.node:
            result = self.__breadthFirstSearch(pfisGraph, fromMethodFqn, methodToPredict) 
            if result > 0:
                sortedRanks = sorted(self.nodeDistances, key = lambda node: self.nodeDistances[node])
                firstIndex = self.__getFirstIndex(sortedRanks, result)
                lastIndex = self.__getLastIndex(sortedRanks, result)
                numTies = lastIndex - firstIndex + 1
                rankWithTies = self.getRankConsideringTies(firstIndex + 1, numTies)
                
                return PredictionEntry(navNumber, rankWithTies, len(self.nodeDistances.keys()), numTies,
                           fromMethodFqn,
                           methodToPredict,
                           navToPredict.toFileNav.timestamp)
        
        return PredictionEntry(navNumber, 999999, len(self.nodeDistances.keys()), 0,
                           str(navToPredict.fromFileNav),
                           str(navToPredict.toFileNav),
                           navToPredict.toFileNav.timestamp)
    
    def __breadthFirstSearch(self, pfisGraph, fromNode, methodToPredict):
        if fromNode not in pfisGraph.graph.node:
            raise RuntimeError('isConnected: Node not found in PFIS Graph: ' + fromNode)
        
        queue = deque()
        self.nodeDistances[fromNode] = 0
        queue.append(fromNode)
        
        while len(queue) > 0:
            
            currentNode = queue.popleft()
            
            for neighbor in self.__getNeighborsOfDesiredEdgeTypes(pfisGraph, currentNode):
                if neighbor not in self.nodeDistances:
                    self.nodeDistances[neighbor] = self.nodeDistances[currentNode] + 1
                    queue.append(neighbor)
                    
        if methodToPredict in self.nodeDistances:
            return self.nodeDistances[methodToPredict] 
        
        return -1
    
    def __getNeighborsOfDesiredEdgeTypes(self, pfisGraph, node):
        validNeighbors = []
        
        for neighbor in pfisGraph.graph.neighbors(node):
            for edgeType in self.edgeTypes:
                if edgeType in pfisGraph.graph[node][neighbor]['types'] and neighbor not in validNeighbors:
                    validNeighbors.append(neighbor)
                
        return validNeighbors
    
    def __getFirstIndex(self, sortedRankList, value):
        for i in range(0, len(sortedRankList)):
            if self.nodeDistances[sortedRankList[i]] == value: return i
        return -1
    
    def __getLastIndex(self, sortedRankList, value):
        for i in range(len(sortedRankList) - 1, -1, -1):
            if self.nodeDistances[sortedRankList[i]] == value: return i
        return -1
