from config.migration import *
from phenom.path import *
from phenom.program import *

import re
import os

from common.log import *
set_log("DictObj")


class MidiList(list):
    ''' This is an internal class to add midi synchronization to
        changes in parameters. '''

    def __init__(self, vals):
        self.midi_echo = True
        list.__init__(self, vals)

    # maintain copy of origonal setter
    old_set = list.__setitem__

    def __setitem__(self, key, val):
        # set value
        self.old_set(key, val)

        if(self.midi_echo and hasattr(self, "midi")):
            self.midi.mirror(self, key)


def load_nested_dict(type, name, extension):
    # open file & extract contents
    try:
        file = "config/" + "/".join(type) + "/" + name + "." + extension
        file = open(file)

        results = file.read().replace("\n", "")
        file.close()

        results = eval(results)

        # evaluate nested fields
        for k in results:
            if(k[0] == "_"):
                results[k] = eval(k[1:].capitalize())(results[k])
            
        return results
    except:
        critical("couldn't read %s" % name)
        return None  


class DictObj(object):
    ''' A Dictionary Object is simply an object used solely as a
        dictionary for ease of use '''

    def __init__(self, type, name="default"):
        self.type, self.name = type, name

        if(not self.__dict__.has_key("extension")):
            self.extension = "obj" 

        self.path = "config/" + "/".join(self.type) + "/"

        self.top_type = self.type[-1]
            
        data = load_nested_dict(self.type, "default", self.extension)

        if(self.name and self.name != "default"):
            data.update(load_nested_dict(self.type, self.name, self.extension))

        self.__dict__.update(data)


    def children(self):
        return [k for k in self.__dict__ if k[0] == '_']


    def has_key(self, key):
        return self.__dict__.has_key(key) or any([self.__dict__[child].__dict__.has_key(key) for child in self.children()])


    def __setattr__(self, key, val):        
        if(key == 'name' and self.__dict__.has_key('name') and self.name != val):
            self.__dict__ = eval(self.top_type.capitalize())(val).__dict__
        else:
            if(key == "__dict__"):
                object.__setattr__(self, key, val)                          
            for child in self.children():
                if(self.__dict__[child].has_key(key)):
                    object.__setattr__(self.__dict__[child], key, val)
                    return
            object.__setattr__(self, key, val)


    def __dir__(self):
        return ["children", "has_key", "merge", "save", "rm"]

  
    def __getattribute__(self, key):
        if(key == "__dict__"  or key in dir(self) or self.__dict__.has_key(key)):
            return object.__getattribute__(self, key)
        else:
            for child in self.children():
                val = getattr(self.__dict__[child], key)
                if(val):
                    return val 

        return None
                 

    def save(self, name=None):
        ''' Dumps an object to a file.  Adds newlines after commas for legibility '''

        # save children
        for child in self.children():
            new_name = self.__dict__[child].save(name)
            object.__setattr__(self, child, new_name)

        if(not name):
            # ex: dir contains "state_0.est, state_1.est, ..., state_n.est], this returns n + 1
            i = max([-1] + [int(file[(len(self.top_type) + 1):(-1 - len(self.extension))]) for file in os.listdir(self.path) if re.compile(self.top_type + '_').match(file)]) + 1
            name = "%s_%d" % (self.top_type, i)

        object.__setattr__(self, 'name', name)

        loc = self.path + "%s.%s" % (self.name, self.extension)

        # copy object
        obj = copy.copy(self.__dict__)

        # hack for state
        if(self.top_type == "state"):
            obj['par'] = list(reduce(lambda s,t: s + t, zip(obj['par_names'], obj['par']), ()))
            del(obj['par_names'])

        # open file & dump repr(obj)
        file = open(loc, "w")
        file.write(repr(obj).replace(",", ",\n"))
        file.close()

        info("saved %s as: %s" % (self.type, self.name))
        return name


    def rm(self):
        ''' Deletes an object and all of its children from disk '''

        # delete children
        for child in self.children():
            self.__dict__[child].rm()

        loc = self.path + "%s.%s" % (self.name, self.extension)

        os.system("rm " + loc)
            
        debug("Deleted " + loc)
        

    def merge(self, dict_obj):
        self.__dict__.update(dict_obj.__dict__)


class App(DictObj):
    ''' Configuration settings for the application. '''

    def __init__(self, name="default"):
        self.extension = "app"
        DictObj.__init__(self, ['app'], name)


class Profile(DictObj):
    ''' Configuration settings for the Engine. '''

    def __init__(self, name="default"):
        self.extension = "prf"
        DictObj.__init__(self, ['app', 'profile'], name)


class Context(DictObj):
    ''' Configuration settings for the Interface. '''

    def __init__(self, name="default"):
        self.extension = "ctx"
        DictObj.__init__(self, ['app', 'context'], name)


class State(DictObj):
    ''' Configuration parameters for generating Frames. '''

    def __init__(self, name="default"):
        self.extension = "est"
        DictObj.__init__(self, ['app', 'state'], name)

        # process pars & names
        self.par_names = self.par[::2]
        self.par = self.par[1::2]

        # perform migration
        self.__dict__ = migrate(self.__dict__)

        # make midi lists
        self.zn  = MidiList(self.zn)
        self.par = MidiList(self.par)

        # set path phases
        for path in self.paths:
            path.phase = self.time
