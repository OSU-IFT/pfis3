from pfisGraph import PfisGraph
from graphAttributes import EdgeType, NodeType

class VariantAwarePfisGraph(PfisGraph):
	def __init__(self, dbFilePath, langHelper, projSrc, stopWords=[], goalWords=[], verbose=False):
		variantTopology = True
		PfisGraph.__init__(self, dbFilePath, langHelper, projSrc, variantTopology, stopWords, goalWords, verbose)
		self.name = "Variant aware"

	def updateTopology(self, action, target, referrer, targetNodeType, referrerNodeType):
		PfisGraph.updateTopology(self, action, target, referrer, targetNodeType, referrerNodeType)

		if action in ['Method declaration', 'Changelog declaration', 'Output declaration'] :
			self._addEdgesToOtherVariants(referrer, referrerNodeType)
			self._addEdgesToOtherVariants(target, targetNodeType)

		if self.variantTopology:
			if self.langHelper.isNavigablePatch(target):
				variantName = self.langHelper.getVariantName(target)
				self._addEdge(target, variantName, targetNodeType, NodeType.VARIANT, EdgeType.VARIANT_CONTAINS)
			if self.langHelper.isNavigablePatch(referrer):
				variantName = self.langHelper.getVariantName(referrer)
				self._addEdge(referrer, variantName, referrerNodeType, NodeType.VARIANT, EdgeType.VARIANT_CONTAINS)


	def _addEdgesToOtherVariants(self, node1, node1Type):
		nodes = self.graph.nodes()
		for node2 in nodes:
			if node1 != node2 and self.graph.node[node2]['type'] == node1Type:
				if self.langHelper.isVariantOf(node1, node2):
					self._addEdge(node1, node2, node1Type, self.graph.node[node2]['type'], EdgeType.SIMILAR)

	def getAllNeighbors(self, node):
		edges = EdgeType.getAll()
		return self.getNeighborsOfDesiredEdgeTypes(node, edges)

	def cloneNode(self, cloneTo, cloneFrom):
		PfisGraph.cloneNode(self, cloneTo, cloneFrom)

		# Add SIMILAR edges between newly created node and its variants.
		nodeType = self.getNode(cloneTo)['type']
		self._addEdgesToOtherVariants(cloneTo, nodeType)