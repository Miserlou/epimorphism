from globals import *

from aeon.datapath import *

from common.log import *
set_log("Path")

class Path(object):


    def __init__(self, type, obj, idx, phase, start, spd, data):
        self.type, self.obj, self.idx, self.phase, self.start, self.spd, self.data  = type, obj, idx, phase, start, spd, data
        Globals().load(self)


    def execute(self, t):
        (res, status) = eval(self.type)(self, self.phase + t, self.data)

        # set result
        if(self.obj):
            self.cmdcenter.set_val(res, self.obj, self.idx)

        return status


    def __repr__(self):
        return "Path('%s', %s, %s, %f, %f, %f, %s)" % (self.type, self.obj and ("'" + self.obj + "'") or "None", self.idx or "None", self.phase, self.start, self.spd, str(self.data))
