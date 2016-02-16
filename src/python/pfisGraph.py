import networkx as nx
import re
import sqlite3
from navpath import NavigationPath
from nltk.stem import PorterStemmer
from knownPatches import KnownPatches

class PfisGraph(object):
    
    # NAVIGATION_TIMESTAMPS_QUERY = "SELECT timestamp, action, target, referrer from logger_log WHERE action = 'Text selection offset' ORDER BY timestamp"
    
    
    SCENT_QUERY = "SELECT action, target, referrer FROM logger_log WHERE action IN " \
                  "('Package', 'Imports', 'Extends', 'Implements', " \
                  "'Method declaration', 'Constructor invocation', 'Method invocation', 'Variable declaration', 'Variable type', " \
                  "'Constructor invocation scent', 'Method declaration scent', 'Method invocation scent') " \
                  "AND timestamp >= ? AND timestamp < ?"
    TOPOLOGY_QUERY = "SELECT action, target, referrer FROM logger_log WHERE action IN " \
                     "('Package', 'Imports', 'Extends', 'Implements', " \
                     "'Method declaration', 'Constructor invocation', 'Method invocation', 'Variable declaration', 'Variable type') " \
                     "AND timestamp >= ? AND timestamp < ?"
    ADJACENCY_QUERY = "SELECT timestamp, action, target, referrer FROM logger_log WHERE action = 'Method declaration offset' " \
                      "AND timestamp >= ? AND timestamp < ? ORDER BY timestamp"
                      
    REGEX_SPLIT_CAMEL_CASE = re.compile(r'_|\W+|\s+|(?<=[a-z])(?=[A-Z])|(?<=[A-Z])(?=[A-Z][a-z])|(?<=[a-zA-Z])(?=[0-9]+)|(?<=[0-9])(?=[a-zA-Z]+)')
    

    def __init__(self, dbFilePath, langHelper, projSrc, stopWords=[], verbose=False):
        self.dbFilePath = dbFilePath
        self.langHelper = langHelper
        self.stopWords = stopWords
        self.VERBOSE_BUILD = verbose
        self.graph = None
        self.endTimestamp = '0'
        self.navNumber = -1
        self.navPath = NavigationPath(dbFilePath, langHelper, projSrc, verbose=True)
        self.__initGraph()
    
    def __initGraph(self):
        self.graph = nx.Graph()
        self.updateGraphByOneNavigation()
        
    def getNavigationPath(self):
        return self.navPath
        
    def updateGraphByOneNavigation(self):
        conn = sqlite3.connect(self.dbFilePath)
        conn.row_factory = sqlite3.Row
        
        newEndTimestamp = 0

        if self.navNumber < self.navPath.getLength() - 1:
            self.navNumber += 1
            newEndTimestamp = self.navPath.navigations[self.navNumber].toFileNav.timestamp
        
        print 'Updating PFIS Graph...'
        
        self.__addScentNodesUpTo(conn, newEndTimestamp)
        self.__addTopologyNodesUpTo(conn, newEndTimestamp)
        self.__addAdjacencyNodesUpTo(conn, newEndTimestamp)
        
        print 'Done updating PFIS Graph.'
        
        self.endTimestamp = newEndTimestamp
    
        conn.close()
        
    def makePrediction(self, predictiveAlgorithm):
        predictiveAlgorithm.makePrediction(self, self.navPath, self.navNumber)
        
    def __addScentNodesUpTo(self, conn, newEndTimestamp):
        # Inserts nodes into the graph up to a given timestamp in the database
        # provided by the conn.
        print '\tProcessing scent. Adding scent-related nodes...'
        
        c = conn.cursor()
        if self.VERBOSE_BUILD:
            print "\tExecuting scent query from ", self.endTimestamp, "to", newEndTimestamp
        c.execute(self.SCENT_QUERY, [self.endTimestamp, newEndTimestamp])
        
        for row in c:
            action, target, referrer = \
                row['action'], self.langHelper.fixSlashes(row['target']), \
                self.langHelper.fixSlashes(row['referrer'])
            
            # Note that these can return None if the relation is undefined
            targetNodeType = NodeType.getTargetNodeType(action, target)
            referrerNodeType = NodeType.getReferrerNodeType(action, referrer, self.langHelper)

            # Case 1: target and referrer contain either FQNs or file paths, so
            # create a  node for every target and referrer. Each of these nodes then
            # gets an edge to each of the words within the FQN or path, excluding
            # stop words. These words are not stemmed.
            if action in ('Package', 'Imports', 'Extends', 'Implements',
                          'Method declaration', 'Constructor invocation',
                          'Method invocation', 'Variable declaration',
                          'Variable type'):
                for word in self.__getWordNodes_splitNoStem(target, self.stopWords):
                    self.__addEdge(target, word, targetNodeType, NodeType.WORD, EdgeType.CONTAINS)
        
                for word in self.__getWordNodes_splitNoStem(referrer, self.stopWords):
                    self.__addEdge(referrer, word, referrerNodeType, NodeType.WORD, EdgeType.CONTAINS)
        
            # Case 2: These actions have code content within them. In this case we
            # want to add an edge from the FQN node in target to the code content in
            # referrer. The FQNs should already exist because of step 1. Words are
            # added in two ways. In the first pass, the complete word is added,
            # camelCase intact without stemming. In the second pass, the camel case
            # is split, the resulting words are stemmed and those are added to the
            # FQN node.
            elif action in ('Constructor invocation scent',
                            'Method declaration scent',
                            'Method invocation scent'):
                for word in self.__getWordNodes_splitNoStem(referrer, self.stopWords):
                    self.__addEdge(target, word, targetNodeType, NodeType.WORD, EdgeType.CONTAINS)
                    
                for word in self.__getWordNodes_splitCamelAndStem(referrer, self.stopWords):
                    self.__addEdge(target, word, targetNodeType, NodeType.WORD, EdgeType.CONTAINS)
        c.close()
        
        print '\tDone adding scent-related nodes.'
        self.__printGraphStats()
        
    def __addTopologyNodesUpTo(self, conn, newEndTimestamp):
        # Build the graph according to the code structure recorded by PFIG. See
        # each section of the build for details.
    
        print "\tProcessing topology. Adding location nodes to the graph..."
    
        c = conn.cursor()
        c.execute(self.TOPOLOGY_QUERY, [self.endTimestamp, newEndTimestamp])
    
        for row in c:
            action, target, referrer, = \
                row['action'], self.langHelper.fixSlashes(row['target']), \
                self.langHelper.fixSlashes(row['referrer'])
            
            targetNodeType = NodeType.getTargetNodeType(action, target)
            referrerNodeType = NodeType.getReferrerNodeType(action, referrer, self.langHelper)
            
            if action == 'Package':
                # target = FILE, referrer = PACKAGE
                # Link the file to the package
                self.__addEdge(target, referrer,
                               targetNodeType,
                               referrerNodeType,
                               EdgeType.CONTAINS)
                # Link the package to the root 'Packages' node
                self.__addEdge('Packages', referrer,
                               NodeType.SPECIAL,
                               referrerNodeType,
                               EdgeType.CONTAINS)
                # Link the file to its class FQN
                fqn = self.__getClassFQN(target)
                self.__addEdge(target, fqn,
                               targetNodeType,
                               NodeType.CLASS,
                               EdgeType.CONTAINS)
            elif action == 'Imports':
                # target = FILE, referrer = CLASS
                # Link the file to its class FQN
                fqn = self.__getClassFQN(target)
                targetPackage = self.langHelper.package(target)
                self.__addEdge(target, fqn,
                               targetNodeType,
                               NodeType.CLASS,
                               EdgeType.CONTAINS)
                # Link the class FQN to the imported class
                self.__addEdge(fqn, referrer,
                               NodeType.CLASS,
                               referrerNodeType,
                               EdgeType.IMPORTS)
                # Link the file to its package
                self.__addEdge(targetPackage, target,
                               NodeType.PACKAGE,
                               targetNodeType,
                               EdgeType.CONTAINS)
                # Link the package to 'Packages'
                self.__addEdge('Packages', targetPackage,
                               NodeType.SPECIAL,
                               NodeType.PACKAGE,
                               EdgeType.CONTAINS)
            elif action == 'Extends':
                # target = CLASS, referrer = CLASS
                # Link the class to the class it extends
                self.__addEdge(target, referrer,
                               targetNodeType,
                               referrerNodeType,
                               EdgeType.EXTENDS)
            elif action == 'Implements':
                # target = CLASS, referrer = CLASS
                # Link the class to the class it implements
                self.__addEdge(target, referrer,
                               targetNodeType,
                               referrerNodeType,
                               EdgeType.IMPLEMENTS)
            elif action == 'Method declaration':
                # target = CLASS, referrer = METHOD
                # Link the class to the method it declares
                self.__addEdge(target, referrer,
                               targetNodeType,
                               referrerNodeType,
                               EdgeType.CONTAINS)
            elif action == 'Method invocation':
                # target = METHOD, referrer = METHOD
                # Link the calling method to the called method
                self.__addEdge(target, referrer,
                               targetNodeType,
                               referrerNodeType,
                               EdgeType.CALLS)
                # Link the called method it its class
                fqn = self.__getClassFQN(referrer)
                self.__addEdge(fqn, referrer, 
                               NodeType.CLASS, 
                               referrerNodeType, 
                               EdgeType.CONTAINS)
            elif action == 'Variable declaration':
                # target = CLASS/METHOD, referrer = VARIABLE
                # Link the variable to the method or class it is defined within
                self.__addEdge(target, referrer,
                               targetNodeType,
                               referrerNodeType,
                               EdgeType.CONTAINS)
            elif action == 'Variable type':
                # target = VARIABLE, referrer = CLASS/PRIMITIVE
                # Link the variable to its type
                self.__addEdge(target, referrer,
                               targetNodeType,
                               referrerNodeType,
                               EdgeType.TYPE)
        c.close
    
        print "\tDone processing topology."
        self.__printGraphStats()
        
    def __addAdjacencyNodesUpTo(self, conn, newEndTimestamp):
        knownPatches = KnownPatches(self.langHelper)
    
        print "\tProcessing adjacency. Adding adjacency edges to the graph..."
    
        c = conn.cursor()
        c.execute(self.ADJACENCY_QUERY, [self.endTimestamp, newEndTimestamp])
        
        for row in c:
            target, referrer = self.langHelper.fixSlashes(row['target']), int(row['referrer'])
            
            knownPatches.addFilePatch(target);
            method = knownPatches.findMethodByFqn(target);
            method.startOffset = referrer
        
        c.close()
        
        adjacentMethodLists = knownPatches.getAdajecentMethods()
        
        for methods in adjacentMethodLists:
            for i in range(1, len(methods)):
                self.__addEdge(methods[i].fqn, methods[i - 1].fqn, 
                               NodeType.METHOD, 
                               NodeType.METHOD, 
                               EdgeType.ADJACENT)
#                 print '\t\tAdded edge from '
#                 print '\t\t\t' + methods[i - 1].fqn + ' to '
#                 print '\t\t\t' + methods[i].fqn
        
        print "\tDone processing adjacency."
        self.__printGraphStats()
        
    #==============================================================================#
    # Helper methods for building the graph                                        #
    #==============================================================================#
    
    def __addEdge(self, node1, node2, node1Type, node2Type, edgeType):
        self.graph.add_edge(node1, node2, type=edgeType)
        self.graph.node[node1]['type'] = node1Type
        self.graph.node[node2]['type'] = node2Type
        # if self.VERBOSE_BUILD: 
        # print "\tAdding edge from", node1, "to", node2, "of type", edgeType
    
    def __getWordNodes_splitNoStem(self, s, stopWords):
        # Returns a list of word nodes from the given string after stripping all
        # non-alphanumeric characters. A word node is a tuple containing 'word' and
        # a String containing the word. Words are always lower case. No stemming is
        # done in this case.
        return [word.lower() \
                    for word in re.split(r'\W+|\s+', s) \
                    if word != '' and word.lower() not in stopWords]
    
    def __getWordNodes_splitCamelAndStem(self, s, stopWords):
        # Returns a list of word nodes from the given string after stripping all
        # non-alphanumeric characters, splitting camel case and stemming each word.
        # A word node is a tuple that contains 'word' and a String containing the
        # word. Words are always lower case.
        return [PorterStemmer().stem(word).lower() \
                    for word in self.__splitCamelWords(s, stopWords) \
                    if word.lower() not in stopWords]
    
    def __splitCamelWords(self, s, stopWords):
        # Split camel case words. E.g.,
        # camelSplit("HelloWorld.java {{RSSOwl_AtomFeedLoader}}")
        # --> ['Hello', 'World', 'java', 'RSS', 'Owl', 'Atom', 'Feed', 'Loader']
        result = []
        last = 0
        for match in self.REGEX_SPLIT_CAMEL_CASE.finditer(s):
            if s[last:match.start()] != '':
                result.append(s[last:match.start()])
            last = match.end()
    
        if s[last:] != '':
            result.append(s[last:])
    
        return result
    
    def __getClassFQN(self, s):
        normalized = self.langHelper.normalize(s)
        
        if normalized != '':
            return 'L' + normalized + ';'
        else:
            raise Exception("convertFilePathToFQN: invalid path: " + s)
        
    def __printGraphStats(self):
        print "\tGraph contains " + str(len(self.graph.node)) + " nodes."
        print "\tGraph contains " + str(len(self.graph.edge)) + " edges."
   

class NodeType(object):
    PACKAGE = 0
    FILE = 1
    CLASS = 2
    METHOD = 3
    VARIABLE = 4
    PRIMITIVE = 5
    PROJECT = 6
    WORD = 7
    SPECIAL = 8
    
    __targetNodes = {}
    __targetNodes["Extends"] = CLASS
    __targetNodes["Implements"] = CLASS
    __targetNodes["Imports"] = FILE
    __targetNodes["Method declaration"] = CLASS
    __targetNodes["Method declaration scent"] = METHOD
    __targetNodes["Method invocation"] = METHOD
    __targetNodes["Method invocation scent"] = METHOD
    __targetNodes["New file header"] = METHOD
    __targetNodes["Package"] = FILE
    __targetNodes["Variable type"] = VARIABLE
                
    __referrerNodes = {}
    __referrerNodes["Extends"] = CLASS
    __referrerNodes["Implements"] = CLASS
    __referrerNodes["Imports"] = CLASS
    __referrerNodes["Method declaration"] = METHOD
    __referrerNodes["Method invocation"] = METHOD
    __referrerNodes["Package"] = PACKAGE
    __referrerNodes["Variable declaration"] = VARIABLE
                    
    @staticmethod
    def getTargetNodeType(action, target):
        if action == 'Variable declaration':
            if target.find('.') == -1:
                return NodeType.CLASS
            else:
                return NodeType.METHOD
        
        if action in NodeType.__targetNodes:
            return NodeType.__targetNodes[action]
        
        return None
                
    @staticmethod
    def getReferrerNodeType(action, referrer, langHelper):
        if action == 'Variable type':
            if len(referrer) == 1:
                return NodeType.PRIMITIVE
            return NodeType.CLASS
            
        if action == 'Package Explorer tree':
            if langHelper.hasCorrectExtension(referrer):
                return NodeType.FILE
            return NodeType.PACKAGE
            
        if action in NodeType.__referrerNodes:
            return NodeType.__referrerNodes[action]
        
        return None
        
    
class EdgeType(object):
    CONTAINS = 0
    IMPORTS = 1
    EXTENDS = 2
    IMPLEMENTS = 3
    CALLS = 4
    ADJACENT = 5
    TYPE = 6
