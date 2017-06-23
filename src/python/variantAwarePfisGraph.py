from pfisGraph import PfisGraph
from graphAttributes import EdgeType, NodeType

class VariantAwarePfisGraph(PfisGraph):
	def __init__(self, dbFilePath, langHelper, projSrc, stopWords=[], goalWords=[], verbose=False):
		variantTopology = True
		PfisGraph.__init__(self, dbFilePath, langHelper, projSrc, variantTopology, stopWords, goalWords, verbose)
		self.name = "Variant aware"

	def updateTopology(self, action, target, referrer, targetNodeType, referrerNodeType):
		PfisGraph.updateTopology(self, action, target, referrer, targetNodeType, referrerNodeType)
		if action in ['Method declaration', 'Changelog declaration', 'Output declaration', 'Package', 'File']:
			self._addEdgesToOtherVariants(referrer, referrerNodeType)
			self._addEdgesToOtherVariants(target, targetNodeType)

	def _addEdgesToOtherVariants(self, node1, node1Type):
		nodes = self.graph.nodes()
		for node2 in nodes:
			node2Type = self.graph.node[node2]['type']
			if node1 != node2 and node2Type == node1Type:
				if self.langHelper.isVariantOf(node1, node2):
					self._addEdge(node1, node2, node1Type, node2Type, EdgeType.SIMILAR)