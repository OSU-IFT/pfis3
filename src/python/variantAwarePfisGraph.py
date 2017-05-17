from pfisGraph import PfisGraph
from graphAttributes import EdgeType

class VariantAwarePfisGraph(PfisGraph):
	def __init__(self, dbFilePath, langHelper, projSrc, stopWords=[], goalWords=[], verbose=False):
		PfisGraph.__init__(self, dbFilePath, langHelper, projSrc, stopWords, goalWords, verbose)

	def updateTopology(self, action, target, referrer, targetNodeType, referrerNodeType):
		PfisGraph.updateTopology(self, action, target, referrer, targetNodeType, referrerNodeType)
		if action in ['Method declaration', 'Changelog declaration'] :
			self._addEdgesToOtherVariants(referrer, referrerNodeType)
			self._addEdgesToOtherVariants(target, targetNodeType)

	def _addEdgesToOtherVariants(self, node1, node1Type):
		nodes = self.graph.nodes()
		for node2 in nodes:
			if node1 != node2 and self.graph.node[node2]['type'] == node1Type:
				if self.langHelper.isVariantOf(node1, node2):
					self._addEdge(node1, node2, node1Type, self.graph.node[node2]['type'], EdgeType.VARIANT_OF)

	def getAllNeighbors(self, node):
		edges = EdgeType.getAll()
		return self.getNeighborsOfDesiredEdgeTypes(node, edges)

	def cloneNode(self, cloneTo, cloneFrom):
		PfisGraph.cloneNode(self, cloneTo, cloneFrom)
		nodeType = self.getNode(cloneTo)['type']
		self._addEdge(cloneTo, cloneFrom, nodeType, nodeType, EdgeType.VARIANT_OF)
