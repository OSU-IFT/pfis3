import re
import os

class AbstractLanguageHelper:

    REGEX_FIX_SLASHES = re.compile(r'[\\/]+')
    REGEX_NORM_ECLIPSE = re.compile(r"L([^;]+);.*") #todo: why is this called eclipse?
    REGEX_PROJECT = re.compile(r"\/(.*)\/src/.*")


    def __init__(self, fileExtension, normalizedPathRegex, packageRegex):
        self.FileExtension = fileExtension
        self.REGEX_NORM_PATH = re.compile(normalizedPathRegex)
        self.REGEX_PACKAGE = re.compile(packageRegex)

    def fixSlashes(self, s):
        # Replaces '\' with '/'
        return AbstractLanguageHelper.REGEX_FIX_SLASHES.sub('/', s)


    def normalize(self, string):
        raise NotImplementedError("Normalize: Not implemented")

    def getOuterClass(self, loc):
        return loc

    def package(self, s):
        # Return the package. Empty string returned on fail.
        # Ex: Lorg/gjt/sp/jedit/gui/statusbar/LineSepWidgetFactory$LineSepWidget -->
        #     org/gjt/sp/jedit/gui/statusbar
        m = self.REGEX_PACKAGE.match(self.normalize(s))
        if m:
            return m.group(1)
        return ''

    def project(self, s):
        # Return the root folder in the given path. Empty string returned on fail.
        # In Eclipse, the root folder would be the project folder.
        # Ex: /jEdit/src/org/gjt/sp/jedit/search --> jEdit
        m = AbstractLanguageHelper.REGEX_PROJECT.match(self.fixSlashes(s))
        if m:
            return m.group(1)
        return ''
    
    def hasCorrectExtension(self, filePath):
        return filePath.lower().endswith(self.FileExtension)

    #==============================================================================#
    # Helper methods for initial weights on the graph                              #
    #==============================================================================#
    # Each of these mehtods define a different level of granularity for navigations
    # PFIS3 supports betwee-method, between-class and between-package navigations.
    # These functions are passed in as parameters and rely on the list of methods
    # generated by buildPaths

    def between_method(self, a, b):
        # A navigation between methods occurs when two consecutive FQNs do not match
        return a != b

    def between_class(self, a, b):
        # A navigation between classes occurs when two consecutive normalized class
        # paths do not match
        return self.normalize(a) != self.normalize(b)
    def between_package(self, a, b):
        # A navigation between packages occurs when two conscutive pacakes do not
        # match
        return self.package(a) != self.package(b)


    def getFileName(self, projectFolderPath, className, extn):
        return os.path.join(projectFolderPath, className + extn)

    def isMethodFqn(self, filePathOrFqn):
        if ';' in filePathOrFqn \
            and '.' in filePathOrFqn:
            return True
        return False