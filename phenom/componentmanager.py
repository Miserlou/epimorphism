from phenom.datamanager import *
from noumena.compiler import *

import time

COMPILE_TIME = 1.9

class ComponentManager(object):

    def __init__(self, cmdcenter, state, renderer, engine, context):
        self.cmdcenter, self.state, self.renderer, self.engine, self.context = cmdcenter, state, renderer, engine, context

        self.switching_component = False

        # start datamanager
        self.datamanager = DataManager()

        # init indices for components
        self.set_component_indices()


    def component_list(self):
        return self.datamanager.components


    def print_components(self):
        keys = self.datamanager.components

        for i in xrange(len(keys)) :
            component = getattr(self.state, keys[i])
            print i+1, ":", keys[i], "-", component, "-", self.datamanager.comment(keys[i], component)


    def set_component_indices(self):
        self.state.component_idx = [0 for i in xrange(20)]

        component_vals = [[items[0] for items in getattr(self.datamanager, component)] for component in self.datamanager.components]

        for component_name in self.datamanager.components:
            idx = self.datamanager.components.index(component_name)
            val =  getattr(self.state, component_name.upper())

            if(component_name == "T"):
                val = val.replace("(zn[2] * z + zn[3])", "(z)").replace("zn[0] * ", "").replace(" + zn[1]", "")
            elif(component_name == "T_SEED"):
                val = val.replace("(zn[10] * z + zn[11])", "(z)").replace("zn[8] * ", "").replace(" + zn[9]", "")

            print component_name, ":", val

            self.state.component_idx[2 * idx] = component_vals[idx].index(val)


    def set_kernel(self, name):
        self.new_kernel = True
        self.engine.new_kernel = name


    def inc_data(self, component_name, idx):
        if(self.switching_component):
            return

        # get components
        components = getattr(self.datamanager, component_name)

        # get and update index
        idx_idx = self.datamanager.components.index(component_name)

        val_idx = self.state.component_idx[2 * idx_idx]
        val_idx += idx
        val_idx %= len(components)

        # get component
        component = components[val_idx]

        self.switch_components({component_name: component[0]})


    def switch_components(self, data):

        updates = {}
        for component_name, val in data.items():
            idx_idx = self.datamanager.components.index(component_name)
            components = getattr(self.datamanager, component_name)
            component = [c for c in components if c[0] == val][0]
            val_idx = components.index(component)
            updates[component_name] = {"val":val, "component":component, "val_idx":val_idx, "idx_idx":idx_idx}

        # switch to component
        if(not self.context.splice_components):

            self.switching_component = True

            for component_name, update in updates.items():
                component = update["component"]
                val = update["val"]

                # initialize component
                for line in component[1]:
                    exec(line) in self.cmdcenter.env

                # cheat if t or t_seed
                if(component_name == "T"):
                    val = "zn[0] * %s + zn[1]" % val.replace("(z)", "(zn[2] * z + zn[3])")
                elif(component_name == "T_SEED"):
                    val = "zn[8] * %s + zn[9]" % val.replace("(z)", "(zn[10] * z + zn[11])")

                self.renderer.echo_string = "switching %s to: %s" % (component_name, val)

                setattr(self.state, component_name, val)

                print "switching %s" % component_name

            self.new_kernel = False
            Compiler(self.state.__dict__, self.set_kernel, self.context).start()

            while(not self.new_kernel and not self.context.exit) : time.sleep(0.1)
            if(self.context.exit) : exit()

            self.new_kernel = False

            print "done switching"

            self.switching_component = False

            self.set_component_indices()

            self.renderer.echo_string = None

        else:
            if(len(updates) == 1):
                self.renderer.flash_message("switching %s to: %s" % (updates.keys()[0], updates[updates.keys()[0]]["val"]))

            first_idx = None

            for component_name, update in updates.items():
                val_idx = update["val_idx"]
                idx_idx = update["idx_idx"]

                if(not first_idx):
                    first_idx = idx_idx

                self.state.component_idx[2 * idx_idx + 1] = val_idx
                self.state.internal[idx_idx] = time.clock() - self.engine.t_start

            while(time.clock() - self.engine.t_start - self.state.internal[first_idx] < self.context.component_switch_time):
                time.sleep(0.1)

            for component_name, update in updates.items():
                val_idx = update["val_idx"]
                idx_idx = update["idx_idx"]
                val = update["val"]

                setattr(self.state, component_name, val)
                self.state.internal[idx_idx] = 0
                self.state.component_idx[2 * idx_idx] = val_idx




