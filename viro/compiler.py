from common.globals import *

import time
import os
import re
import hashlib
import threading
import time

from ctypes import *

from common.log import *
set_log("COMPILER")


def get_functions(name):
    ''' Creates & returns ctypes interfaces to the kernel .so '''
    debug("Getting functions from: %s" % name)

    # attempt to load kernel
    try:
        lib = cdll.LoadLibrary("kernels/%s.so" % name)#, RTLD_LOCAL)
    except:
        critical("Kernel not found")
        os._exit(0)

    # extract function - this could probably be done more smartly
    kernel = lib.__device_stub__Z9kernel_fbP6float4mP6uchar4iffff
    kernel.restype = None
    kernel.argtypes = [ c_void_p, c_ulong, c_void_p, c_int, c_float, c_float, c_float, c_float ]

    reset = lib.__device_stub__Z5resetP6float4m
    reset.restype = None
    reset.argtypes = [ c_void_p, c_ulong ]

    return (kernel, reset)


class Compiler(threading.Thread):
    ''' A Compiler object if responsible for asynchronously calling nvcc.
        The compilation can be restarted by a call to update. '''

    def __init__(self, callback):
        debug("Initializing Compiler")
        Globals().load(self)

        self.callback = callback

        self.substitutions = {}

        # init thread
        threading.Thread.__init__(self)


    def splice_components(self):
        ''' This method dynamicly generates the interpolated component switch
            statements that are spliced into the kernels '''
        debug("Splicing components")




        for component_name in self.cmdcenter.componentmanager.datamanager.component_names:
            component_list = self.cmdcenter.componentmanager.datamanager.components[component_name]

            idx = self.cmdcenter.componentmanager.datamanager.component_names.index(component_name)

            if(len(component_list) == 0):
                self.substitutions[component_name] = ""

            elif(len(component_list) == 1):
                self.substitutions[component_name] = "%s = %s;" % (component_name.lower(), component_list[0][0])

            else:

                clause1 = "switch(component_idx[%d][0]){\n" % idx
                for component in component_list:
                    name = component[0]
                    clause1 += "case %d: %s0 = %s;break;\n" % (component_list.index(component), component_name.lower(), name)
                clause1 += "}\n"

                clause2 = "switch(component_idx[%d][1]){\n" % idx
                for component in component_list:
                    name = component[0]
                    clause2 += "case %d: %s1 = %s;break;\n" % (component_list.index(component), component_name.lower(), name)
                clause2 += "}\n"

                interp = "if(internal[%d] != 0){\n" % idx
                interp += "intrp_t = min((_clock - internal[%d]) / switch_time, 1.0f);\n" % (idx)
#                interp += "intrp_t = 1.0f / (1.0f + expf(-1.0f * (12.0f * intrp_t - 6.0f)));\n"
                interp += "intrp_t = (1.0 + erff(4.0f * intrp_t - 2.0f)) / 2.0;\n"
                sub = "intrp_t"
                interp += "%s\n%s = ((1.0f - %s) * (%s0) + %s * (%s1));" % (clause2,  component_name.lower(), sub, component_name.lower(), sub, component_name.lower())
                interp += "\n}else{\n%s = %s0;\n}" % (component_name.lower(), component_name.lower())

                self.substitutions[component_name] = clause1 + interp

        return self


    def render_file(self, name):
        ''' Substitues escape sequences in a .ecu file with dynamic content '''
        debug("Rendering: %s", name)

        # open file & read contents
        file = open("aeon/" + name)
        contents = file.read()
        file.close()

        # cull mode
        if(self.env.cull_enabled):
            self.substitutions['CULL_ENABLED'] = "#define CULL_ENABLED"
        else:
            self.substitutions['CULL_ENABLED'] = ""

        # components
        if(self.env.splice_components):
            self.splice_components()
        else:
            for component_name in self.cmdcenter.componentmanager.datamanager.component_names:
                if(component_name in self.state.components):
                    self.substitutions[component_name] = "%s = %s;" % (component_name.lower(),  self.state.components[component_name])
                else:
                    self.substitutions[component_name] = ""

        # bind PAR_NAMES
        par_name_str = ""

        for i in xrange(len(self.state.par_names)):
            if(self.state.par_names[i] != ""):
                par_name_str += "#define %s par[%d]\n" % (self.state.par_names[i], i)

        self.substitutions["PAR_NAMES"] = par_name_str

        # replace variables
        for key in self.substitutions:
            contents = re.compile("\%" + key + "\%").sub(str(self.substitutions[key]), contents)

        # write file contents
        file = open("aeon/__%s" % (name.replace(".ecu", ".cu")), 'w')
        file.write(contents)
        file.close()


    def run(self):
        ''' Executes the main Compiler sequence '''
        debug("Executing")

        # remove emacs crap
        os.system("rm aeon/.#*")

        # render ecu files
        files = [file for file in os.listdir("aeon") if re.search("\.ecu$", file)]

        for file in files:
            self.render_file(file)

        # hash files
        files = [file for file in os.listdir("aeon") if re.search("\.cu$", file)]

        contents = ""
        for file in files:
            contents += open("aeon/" + file).read()

        # seed to force recompilation if necessary
        if(not self.env.splice_components): contents += str(time.clock())

        # hash
        hash = hashlib.sha1(contents).hexdigest()

        # make name
        if(self.env.splice_components):
            name = "kernel_spliced-%s" % hash
        else:
            os.system("rm kernels/kernels_nonspliced*")
            name = "kernel_nonspliced-%s" % hash

        # compile if library doesn't exist
        if(not os.path.exists("kernels/%s.so" % name)):
            info("Compiling kernel - %s" % name)

            os.system("/usr/local/cuda/bin/nvcc  --host-compilation=c -Xcompiler -fPIC -o kernels/%s.so --shared %s aeon/__kernel.cu" % (name, self.profile.ptxas_stats and "--ptxas-options=-v" or ""))

            # remove tmp files
            files = [file for file in os.listdir("aeon") if re.search("\.ecu$", file)]
            #for file in files:
            #    os.system("rm aeon/__%s" % (file.replace(".ecu", ".cu")))
            if(os.path.exists("__kernel.linkinfo")) : os.system("rm __kernel.linkinfo")

        # execute callback
        self.callback(name)

