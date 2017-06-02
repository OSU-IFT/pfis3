from pfisGraph import PfisGraph
from variantAwarePfisGraph import VariantAwarePfisGraph
from variantAndEquivalenceAwarePfisGraph import VariantAndEquivalenceAwarePfisGraph

class GraphFactory:
	def __init__(self, langHelper, dbPath, projSrcPath, variantTopology = False, stopWords=[], goalWords=[]):
		self.langHelper = langHelper
		self.dbPath = dbPath
		self.projSrcPath = projSrcPath
		self.stopWords = stopWords
		self.goalWords = goalWords
		self.variantTopology = variantTopology

	def getGraph(self, algorithmsNode):
		nodeAttrib = algorithmsNode.attrib
		if 'graphType' in nodeAttrib:
			graphType = nodeAttrib["graphType"]

		if graphType == None:
			graphType = "PfisGraph"

		if graphType.lower() == "PfisGraph".lower():
			return PfisGraph(self.dbPath, self.langHelper, self.projSrcPath, self.variantTopology, self.stopWords, self.goalWords)

		if graphType.lower() == "VariantAwarePfisGraph".lower():
			return VariantAwarePfisGraph(self.dbPath, self.langHelper, self.projSrcPath, self.stopWords, self.goalWords)

		if graphType.lower() == "VariantAndEquivalenceAwarePfisGraph".lower():
			if 'variantsDb' in nodeAttrib:
				variantsDb = nodeAttrib["variantsDb"]

			if variantsDb is None:
				raise Exception("Missing attrib: variantsDb for graphType VariantAndEquivalenceAwarePfisGraph in XML config file.")

			divorcedUntilMarried = False
			if 'divorcedUntilMarried' in nodeAttrib and nodeAttrib["divorcedUntilMarried"].lower() == 'true':
				divorcedUntilMarried = True

			return VariantAndEquivalenceAwarePfisGraph(self.dbPath, self.langHelper, self.projSrcPath, variantsDb, divorcedUntilMarried, self.stopWords, self.goalWords)
