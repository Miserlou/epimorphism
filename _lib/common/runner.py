import threading


class Runner(threading.Thread):
    ''' A runner object spawns a new thread to call a function '''

    def __init__(self, func):
        self.func = func

        # init thread
        threading.Thread.__init__(self)


    def run(self):

        # call func
        self.func()


def async(func):

    # create and start thread
    t = Runner(func)
    t.start()
    return t

