from graphAttributes import EdgeType
from predictiveAlgorithm import PredictiveAlgorithm
from predictions import Prediction
from pfisGraph import NodeType


class PFISBase(PredictiveAlgorithm):
	def __init__(self, langHelper, name, fileName, history=False, goal=False, \
	             decayFactor=0.85, decaySimilarity=0.85, decayVariant=0.85, decayHistory=0.9, changelogGoalActivation=False,
	             includeTop=False, numTopPredictions=0, verbose=False):
		PredictiveAlgorithm.__init__(self, langHelper, name, fileName, includeTop, numTopPredictions, verbose)
		self.changeLogGoalWordActivation = changelogGoalActivation
		self.history = history
		self.goal = goal
		self.DECAY_FACTOR = decayFactor
		self.DECAY_HISTORY = decayHistory
		self.DECAY_SIMILARITY = decaySimilarity
		self.DECAY_VARIANT = decayVariant
		self.mapNodesToActivation = None
		self.VERBOSE = True

		self.GOAL_WORD_ACTIVATION = 1.0

	def spreadActivation(self, pfisGraph, fromMethodFqn):
		raise NotImplementedError('spreadActivation is not implemented in PFISBase')

	def makePrediction(self, pfisGraph, navPath, navNumber):
		print "{}: Predict #{}: {}".format(self.name, navNumber, navPath.getNavigation(navNumber))
		if navNumber < 1 or navNumber >= navPath.getLength():
			raise RuntimeError('makePrediction: navNumber must be > 0 and less than the length of navPath')

		navToPredict = navPath.getNavigation(navNumber)
		if navToPredict.isToUnknown():
			return Prediction(navNumber, 999999, 0, 0,
			                  str(navToPredict.fromFileNav),
			                  str(navToPredict.toFileNav),
			                  navToPredict.toFileNav.timestamp)

		fromMethodFqn = navToPredict.fromFileNav.methodFqn
		methodToPredict = navToPredict.toFileNav.methodFqn

		self.initialize(fromMethodFqn, navNumber, navPath, pfisGraph)

		self.spreadActivation(pfisGraph, fromMethodFqn)

		if self.mapNodesToActivation == None:
			print "Map was empty!!!!!!!!"

		fromMethodEquivalentFqn = pfisGraph.getFqnOfEquivalentNode(fromMethodFqn)
		toMethodEquivalentFqn = pfisGraph.getFqnOfEquivalentNode(methodToPredict)

		if fromMethodEquivalentFqn != toMethodEquivalentFqn:
			excludeMethod = fromMethodEquivalentFqn
		else:
			excludeMethod = None

		sortedMethods = self.__getMethodNodesFromGraph(pfisGraph, excludeMethod)
		if toMethodEquivalentFqn in sortedMethods:
			ranking = self.getRankForMethod(toMethodEquivalentFqn, sortedMethods, self.mapNodesToActivation)
			topPredictions = []
			if self.includeTop:
				topPredictions = self.getTopPredictions(sortedMethods, self.mapNodesToActivation)

			return Prediction(navNumber, ranking["rankWithTies"], len(sortedMethods), ranking["numTies"],
			                  str(navToPredict.fromFileNav),
			                  str(navToPredict.toFileNav),
			                  navToPredict.toFileNav.timestamp,
			                  topPredictions)

		else:
			raise Exception("Node not in activation list: ", toMethodEquivalentFqn)

	def initialize(self, fromMethodFqn, navNumber, navPath, pfisGraph):
		# Reset the graph
		self.mapNodesToActivation = {}

		if not self.history:
			# If there is no history, only activate the fromMethodNode
			self.setPatchActivation(pfisGraph, fromMethodFqn, 1.0)
		else:
			# If there is history, activate nodes in reverse navigation order
			# using the DECAY_HISTORY property
			self.__initializeHistory(pfisGraph, navPath, navNumber)

		if self.goal:
			self._initializeGoalWords(pfisGraph)

		if self.changeLogGoalWordActivation:
			self.__initializeChangelogsWithGoalwordsActivation(pfisGraph)

	def setPatchActivation(self, pfisGraph, fromMethodFqn, value):
		fromPatchEquivalent = pfisGraph.getFqnOfEquivalentNode(fromMethodFqn)
		if fromPatchEquivalent not in self.mapNodesToActivation.keys():
			if self.VERBOSE:
				print "{0} : {1}".format(fromPatchEquivalent, value)
			self.mapNodesToActivation[fromPatchEquivalent] = value

	def __initializeHistory(self, pfisGraph, navPath, navNumber):
		activation = 1.0
		# Stop before the first navigation
		for visitedPatch in [navPath.getNavigation(i).fromFileNav.methodFqn for i in range(navNumber, 0, -1)]:
			if pfisGraph.containsNode(visitedPatch):
				self.setPatchActivation(pfisGraph, visitedPatch, activation)
			activation *= self.DECAY_HISTORY

	def _initializeGoalWords(self, pfisGraph, reset=False):
		if reset == False:
			goalWordWeight = self.GOAL_WORD_ACTIVATION
			print "Initialize Goal Words with: ", goalWordWeight
		else:
			goalWordWeight = 0.0
			print "Resetting goalwords activation to ", goalWordWeight

		for stemmedWord in pfisGraph.getGoalWords():
			if pfisGraph.containsNode(stemmedWord):
				if pfisGraph.getNode(stemmedWord)['type'] == NodeType.WORD:
					self.mapNodesToActivation[stemmedWord] = goalWordWeight
					if self.VERBOSE:
						print "Goal word: {}: {}".format(stemmedWord, goalWordWeight)


	def __getMethodNodesFromGraph(self, pfisGraph, excludeNode=None):
		activatedMethodNodes = []
		sortedNodes = []

		for node in self.mapNodesToActivation:
			if node == excludeNode:
				continue

			if pfisGraph.containsNode(node):
				if self.langHelper.isNavigablePatch(node):
					activatedMethodNodes.append(node)

			sortedNodes = sorted(activatedMethodNodes, key=lambda method: self.mapNodesToActivation[method],
			                     reverse=True)
		return sortedNodes

	def __initializeChangelogsWithGoalwordsActivation(self, pfisGraph):
		if not self.goal:
			print "Activating Changelogs with GoalWords..."
			self._initializeGoalWords(pfisGraph)

		goalWords = [word for word in pfisGraph.getGoalWords()
		                 if pfisGraph.containsNode(word) and pfisGraph.getNode(word)['type'] == NodeType.WORD]

		for node in self.mapNodesToActivation.keys():
			if pfisGraph.getNode(node)['type'] == NodeType.WORD and node in goalWords:
				patchesContainingWord = pfisGraph.getNeighborsOfDesiredEdgeTypes(node, [EdgeType.CONTAINS])
				changelogsContainingWord = [p for p in patchesContainingWord if pfisGraph.getNode(p)['type'] == NodeType.CHANGELOG]

				for changelog in changelogsContainingWord:
					if changelog not in self.mapNodesToActivation.keys():
						self.mapNodesToActivation[changelog] = 0.0

					initialValue = self.mapNodesToActivation[changelog]
					self.mapNodesToActivation[changelog] = initialValue + self.GOAL_WORD_ACTIVATION * self.DECAY_FACTOR

					if self.VERBOSE:
						print 'Goalword {} to {}: {} + ({}*{}) = {}'.format(node, changelog,
						                                                   initialValue, self.mapNodesToActivation[node], self.DECAY_FACTOR, self.mapNodesToActivation[changelog])

		self._initializeGoalWords(pfisGraph, reset=True)

	def activatePatchWithGoalWordSimilarity(self, pfisGraph, patchFqn, resetHistory = False):
		if resetHistory:
			self.mapNodesToActivation = {}

		if patchFqn not in self.mapNodesToActivation.keys():
			self.mapNodesToActivation[patchFqn] = 0.0

		goalWords = [word for word in pfisGraph.getGoalWords()
		                 if pfisGraph.containsNode(word) and pfisGraph.getNode(word)['type'] == NodeType.WORD]

		patchNeighbors = pfisGraph.getNeighborsOfDesiredEdgeTypes(patchFqn, [EdgeType.CONTAINS])

		for word in goalWords:
			if word in patchNeighbors:
				self.mapNodesToActivation[patchFqn] = self.mapNodesToActivation[patchFqn] + \
			                                      self.GOAL_WORD_ACTIVATION * self.DECAY_FACTOR

	def getDecayWeight(self, edgeTypes):
		def getEdgeWeightForType(edgeType):
			if edgeType == EdgeType.SIMILAR:
				return self.DECAY_SIMILARITY
			elif edgeType == EdgeType.IN_VARIANT:
				return self.DECAY_VARIANT
			elif edgeType in [EdgeType.ADJACENT, EdgeType.CALLS, EdgeType.CONTAINS]:
				return self.DECAY_FACTOR
			raise Exception("Invalid Edge Type: ", edgeType)

		return max([getEdgeWeightForType(edgeType) for edgeType in edgeTypes])