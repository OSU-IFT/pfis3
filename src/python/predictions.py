import os

class Prediction:
    def __init__(self, navNum, rank, length, numTies, fromLoc, toLoc, timestamp, topPredictions=[]):

        self.navNum = str(navNum)
        self.rank = str(rank)
        self.length = str(length)
        self.numTies = str(numTies)
        self.fromLoc = fromLoc
        self.toLoc = toLoc
        self.timestamp = str(timestamp)
        self.topPredictions = topPredictions

    def __str__(self):
        return self.navNum + '\t' + self.timestamp + '\t' + self.rank + '\t' \
            + self.length + '\t' + self.numTies + '\t' \
            + self.fromLoc + '\t' + self.toLoc + '\t' + str(self.topPredictions)

class Predictions:
    def __init__(self, algName, outputFolder, fileName):
        self.outputFolder = outputFolder
        self.filePath = os.path.join(outputFolder, fileName)
        self.algName = algName
        self.entries = []

    def getHeaderString(self):
        return "Prediction"+ '\t' + "Timestamp" + '\t' + "Rank" + '\t' \
            + "Out of" + '\t' + "No. of Ties" + '\t' \
            + "From loc" + '\t' + "To loc" + '\t' + "Top predictions" + '\n'

    def addPrediction(self, logEntry):
        self.entries.append(logEntry);

    def saveToFile(self):
        print 'Saving results to ' + self.filePath + '...'
        print 'Appending results to ' + self.outputFolder + '/all.txt...'
        
        logFile = open(self.filePath, 'w');
        allLogs = open(self.outputFolder + '/all.txt', 'a')
        logFile.write(self.getHeaderString())
        allLogs.write('\n' + self.algName + '\n')
        allLogs.write(self.getHeaderString())
        
        for entry in self.entries:
            allLogs.write(str(entry) + '\n')
            logFile.write(str(entry) + '\n')
        
        logFile.close()
        allLogs.close()
        
        print 'Done.'
