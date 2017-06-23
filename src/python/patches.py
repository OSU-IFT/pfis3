import uuid
import sqlite3

# TODO: Can this class and the HeaderData class be replaced/merged with the
# FileNavigation class? They all seem to hold the same data...

class Patch(object):
    def __init__(self, fqn):
        self.fqn = fqn
        self.startOffset = -1
        self.length = -1
        self.uuid = uuid.uuid1()
        self.variantInfo = None
        self.patchType = None


class MethodPatch(Patch):

    def __init__(self, fqn):
        Patch.__init__(self, fqn)
        self.patchType = PatchType.SOURCE

    def isOffsetInMethod(self, offset):
        endOffset = self.startOffset + self.length
        if self.startOffset < 0 or self.length < 0:
            return False

        if offset >= self.startOffset and offset < endOffset:
            return True
        return False

    def __str__(self):
        return str(self.startOffset) + ' to ' + str(self.startOffset + self.length - 1) + ': ' + self.fqn

class ChangelogPatch(Patch):
    def __init__(self, fqn):
        Patch.__init__(self, fqn)
        self.patchType = PatchType.CHANGELOG

class OutputPatch(Patch):
    def __init__(self, fqn):
        Patch.__init__(self, fqn)
        self.content = None
        self.patchType = PatchType.OUTPUT

class PatchType(object):
    SOURCE = 'source_code'
    CHANGELOG = 'change_log'
    OUTPUT = 'output'
    FILE = 'file'

class FilePatch(Patch):
    def __init__(self, fqn):
        Patch.__init__(self, fqn)
        self.patchType = PatchType.FILE


class VariantInfo(object):
    def __init__(self, methodPath, startVariant, endVariant):
        self.methodPath = methodPath
        self.startVariant = startVariant
        self.endVariant = endVariant