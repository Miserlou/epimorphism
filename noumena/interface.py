from noumena.renderer import *

from noumena.console import *
from noumena.keyboard import *
from noumena.mouse import *
from noumena.server import *
from noumena.midi import *

from common.log import *
set_log("INTERFACE")


class Interface(object):

    def __init__(self, context):
        debug("Initializing interface")

        # set variables
        self.context = context

        self.renderer = Renderer(context)


    def __del__(self):
        # self.renderer.__del__()
        # kill server
#        if(self.server):
 #           self.server.__del___()
        pass

    def sync(self, cmdcenter):
        debug("Syncing with CmdCenter")

        self.cmdcenter = cmdcenter

        # create input handlers
        self.mouse_handler = MouseHandler(self.cmdcenter, self.context)
        self.keyboard_handler = KeyboardHandler(self.cmdcenter, self.context)

        # create_console
        console = Console(self.cmdcenter)

        # register callbacks & console with Renderer
        self.renderer.register_callbacks(self.keyboard_handler.keyboard, self.mouse_handler.mouse, self.mouse_handler.motion)
        self.renderer.register_console_callbacks(console.render_console, console.console_keyboard)

        # register cmdcenter with renderer
        self.renderer.cmdcenter = cmdcenter

        # start server
        if(self.context.server):
            self.server = Server(self.cmdcenter)
            self.server.start()

        else:
            self.server = None

        # start midi
        if(self.context.midi):
            self.midi = MidiHandler(self.cmdcenter, self.context)

            if(self.context.midi):
                # sync midi lists to controller
                self.cmdcenter.state.zn.midi = self.midi
                self.cmdcenter.state.par.midi = self.midi
                self.midi.start()

        else:
            self.midi = None


    def do(self):
        self.renderer.do()
