import sqlite3
import iso8601
from pfigFileHeader import PFIGFileHeader
from knownPatches import KnownPatches

class NavPath:
    def __init__(self):
        self.navPath = []

    def addEntry(self, entry):
        self.navPath.append(entry)
        l = len(self.navPath)
        if l > 1:
            entry.prevEntry = self.navPath[l - 2]

    def __iter__(self):
        return self.navPath.__iter__()

    def isUnknownMethodAt(self, index):
        return self.navPath[index].unknownMethod

    def getLength(self):
        return len(self.navPath)

    def getEntryAt(self, index):
        return self.navPath[index]

    def getMethodAt(self, index):
        return self.navPath[index].method

    def getTimestampAt(self, index):
        return self.navPath[index].timestamp

    def getPrevEntryAt(self, index):
        return self.navPath[index].prevEntry

    def removeAt(self, index):
        del self.navPath[index]

    def toStr(self):
        out = 'NavPath:\n'
        for entry in self.navPath:
            out += '\t' + entry.method + ' at ' + entry.timestamp +'\n'
        return out

class NavPathEntry:
    def __init__(self, timestamp, method):
        self.timestamp = str(timestamp)
        self.method = method
        self.prevEntry = None
        self.unknownMethod = False

        if method.__contains__("UNKNOWN"):
            self.unknownMethod = True;
            
### REFACTORING STARTS HERE
            
class NavigationPath(object):
    
    TEXT_SELECTION_OFFSET_QUERY = "SELECT timestamp, action, target, referrer FROM logger_log WHERE action = 'Text selection offset' ORDER BY timestamp"
    METHOD_DECLARATIONS_QUERY = "SELECT timestamp, action, target, referrer from logger_log WHERE action IN ('Method declaration', 'Method declaration offset', 'Method declaration length') AND timestamp <= ? ORDER BY timestamp"
    
    def __init__(self, dbFilePath, langHelper, projectFolderPath, verbose = False):
        self.navigations = []
        self.fileNavigations = []
        self.dbFilePath = dbFilePath
        self.knownPatches = KnownPatches(langHelper)
        self.langHelper = langHelper
        self.projectFolderPath = projectFolderPath
        self.VERBOSE_PATH = verbose
        
        conn = sqlite3.connect(self.dbFilePath)
        conn.row_factory = sqlite3.Row
        
        if self.VERBOSE_PATH:
            print 'Building path...'
        self.__findFileNavigationsInDb(conn)
        self.__findMethodsForFileNavigations(conn)
        if self.VERBOSE_PATH:
            print 'Done building path.'
            self.__printNavigations()
        conn.close()
        
    def __findFileNavigationsInDb(self, conn):
        # Here, we find all the instances of Text selection offset actions in
        # the PFIG log. These are stored into the self.fileNavigations list. We
        # remove any obvious duplicates that have the same file path and offset
        # in this function. We store time stamps here since they will be used to
        # determine if self.knownMethods entries need to be added or updated.
        c = conn.cursor()
        c.execute(self.TEXT_SELECTION_OFFSET_QUERY)
        
        prevFilePath = None
        prevOffset = None
        
        for row in c:
            timestamp, filePath, offset = \
                str(iso8601.parse_date(row['timestamp'])), row['target'], int(row['referrer'])
            
            if prevFilePath != filePath or prevOffset != offset:
                if self.langHelper.hasCorrectExtension(filePath):
                    self.fileNavigations.append(FileNavigation(timestamp, filePath, offset))
                
            prevFilePath = filePath
            prevOffset = offset
        c.close()
        
    def __findMethodsForFileNavigations(self, conn):
        # Here we map the file paths and offsets in the fileNavigations list to
        # FQNs of methods. This is done by querying for all the Method
        # declarations within the database and storing that data to the
        # self.knownMethods object. The insertions into knownMethods will create
        # entries if they are new or update them if they already exist. Since
        # code can be changed between navigations, we need to update 
        # self.knownMethods to reflect the most recent state of the code up to
        # each navigation.
        # After building the known methods, we test an entry from
        # fileNavigations against the set of known methods by offset. This is
        # what maps Text selection offsets to methods.
        prevNavigation = None
        
        # Iterate over the data gathered from the Text selection offsets
        for toNavigation in self.fileNavigations:
            if self.VERBOSE_PATH:
                print '\tProcessing text selection offset: ' + toNavigation.toStr()
            
            # For every navigation's timestamp, we fill the knownMethods object
            # with the details of every method declaration up to the timestamp
            # of the toNavigation. The knownMethods object will be queried to
            # determine in which method (if any) a text selection offset occurs.
            
            # Note that the queries here are by a method's FQN. This allows us
            # to update the method's declaration info if it gets updated at some
            # point in the future.
            
            c = conn.execute(self.METHOD_DECLARATIONS_QUERY, [toNavigation.timestamp])
            for row in c:
                action, target, referrer = row['action'], \
                    row['target'], row['referrer']
                
                if action == 'Method declaration':
                    self.knownPatches.addFilePatch(referrer)
                elif action == 'Method declaration offset':
                    method = self.knownPatches.findMethodByFqn(target)
                    if method is not None:
                        method.startOffset = int(referrer);
                elif action == 'Method declaration length':
                    method = self.knownPatches.findMethodByFqn(target)
                    if method is not None:
                        method.length = int(referrer);
                        
            # We query known methods here to see if the offset of the current
            # toNavigation is among the known patches.
            
            toMethodPatch = self.knownPatches.findMethodByOffset(toNavigation.filePath, toNavigation.offset)
            
            fromNavigation = None
            fromMethodPatch = None
            
            # Recall that navigations contains the navigation data after its
            # been translated to methods and headers
            
            # If there was at least 1 navigation already, the to destination
            # from the previous navigation serves as this navigations from. A
            # clone is necessary since this may be later transformed into a 
            # PFIG header and we don't want to affect the to destination from
            # the previous navigation.
            
            if len(self.navigations) > 0:
                prevNavigation = self.navigations[-1]
                fromNavigation = prevNavigation.toFileNav.clone()
                fromMethodPatch = self.knownPatches.findMethodByOffset(fromNavigation.filePath, fromNavigation.offset)
            
            # Create the navigation object representing this navigation
            navigation = Navigation(fromNavigation, toNavigation.clone())
            
            # Set method FQN data
            if navigation.fromFileNav is not None and fromMethodPatch is not None:
                navigation.fromFileNav.methodFqn = fromMethodPatch.fqn
            if navigation.toFileNav is not None and toMethodPatch is not None:
                navigation.toFileNav.methodFqn = toMethodPatch.fqn
            
            if not navigation.isToSameMethod():
                self.__addPFIGFileHeadersIfNeeded(conn, prevNavigation, navigation)
                
                # If the current navigation's from does not have a method FQN,
                # then it was not a valid navigation, so don't count it, except
                # for the first navigation where fromFileNav itself should be
                # None
                if navigation.fromFileNav is None or navigation.fromFileNav.methodFqn is not None:
                    self.navigations.append(navigation)
        c.close()
        
    def __addPFIGFileHeadersIfNeeded(self, conn, prevNav, currNav):
        # If it's the first navigation, don't do anything
        if prevNav is None:
            return 
        
        # If the previous navigation's to is not a known method and the current
        # navigation's from is the same unknown method, then this might need to
        # be converted to a header.
        if prevNav.isToUnknown() and currNav.isFromUnknown():
            if self.knownPatches.findMethodByOffset(currNav.fromFileNav.filePath, currNav.fromFileNav.offset) is None:
                if prevNav.toFileNav.filePath == currNav.fromFileNav.filePath and prevNav.toFileNav.offset == currNav.fromFileNav.offset:
                    if self.VERBOSE_PATH:
                            print '\tChecking if ' + prevNav.toFileNav.toStr() + ' is a header...'
                    headerData = PFIGFileHeader.addPFIGJavaFileHeader(conn, currNav, self.projectFolderPath, self.langHelper)
                    
                    # If headerData comes back as not None, then it was indeed a
                    # header and needs to be added to navigation and 
                    # knownPatches.
                    if headerData is not None:
                        if self.VERBOSE_PATH:
                            print '\tConverted to ' + headerData.fqn
                        
                        # Add to the navigation and the knownPatches
                        currNav.fromFileNav.methodFqn = headerData.fqn
                        self.knownPatches.addFilePatch(headerData.fqn)
                        
                        # Update the properties
                        method = self.knownPatches.findMethodByFqn(headerData.fqn)
                        method.startOffset = 0
                        method.length = headerData.length
                    
                    elif self.VERBOSE_PATH:
                        print '\tNot a header.'
            
    
    def __printNavigations(self):
        print "Navigation path:"
        for i in range(len(self.navigations)):
            navigation = self.navigations[i]
            print '\t' + str(i) + ':\t' + navigation.toStr()
            
    def getLength(self):
        return len(self.navigations)

class Navigation(object):
    # A navigation is a tuple representing one programmer navigation through the
    # code. fromFileNav represents the where the programmer navigated from and 
    # toFileNav represents where the programmer navigated to. Both of these
    # parameters should be FileNavigation objects.
    def __init__(self, fromFileNav, toFileNav):
        self.fromFileNav = fromFileNav
        self.toFileNav = toFileNav
        
    def isToSameMethod(self):
        if self.fromFileNav is not None and self.toFileNav is not None:
            if self.fromFileNav.methodFqn is not None and self.toFileNav.methodFqn is not None:
                return self.fromFileNav.methodFqn == self.toFileNav.methodFqn
        return False
    
    def isFromUnknown(self):
        if self.fromFileNav is not None and self.fromFileNav.methodFqn is not None:
            return False
        return True
    
    def isToUnknown(self):
        if self.toFileNav is not None and self.toFileNav.methodFqn is not None:
            return False
        return True
    
    def clone(self):
        return Navigation(self.fromFileNav.clone(), self.toFileNav.clone())
        
    def toStr(self):
        fromLoc = None
        toLoc = None
        
        if self.fromFileNav is not None:
            fromLoc = self.fromFileNav.toStr()
        if self.toFileNav is not None:
            toLoc = self.toFileNav.toStr()
            
        return str(fromLoc) + ' --> ' + str(toLoc)
        
class FileNavigation(object):
    # A file navigation represents the Text selection offset data that was 
    # captured by PFIG. The Text selection offset occurs any time a programmer's
    # text cursor position changes. If we determine that the text cursor is in a
    # method that the programmer has knowledge of then, methodFqn has that info.
    # If methodFqn is none, then this was a navigation to an 'unknown location'
    def __init__(self, timestamp, filePath, offset):
        self.timestamp = timestamp
        self.filePath = filePath;
        self.offset = offset
        self.methodFqn = None
        
    def clone(self):
        fileNavClone = FileNavigation(self.timestamp, self.filePath, self.offset)
        fileNavClone.methodFqn = self.methodFqn
        return fileNavClone
        
    def toStr(self):
        if self.methodFqn is not None:
            return self.methodFqn
        return str(self.filePath) + ' at ' + str(self.offset)
        