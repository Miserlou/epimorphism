from common.globals import *

from compiler import *

import sys, gc
import itertools
import time
import threading

# import Image

from common.log import *
set_log("ENGINE")

block_size = 16

from ctypes import *
from opencl import *
openCL = PyDLL("libOpenCL.so")
gl = PyDLL("libGL.so.1")

class Engine(object):
    ''' The Engine object is the applications interface, via cuda, to the graphics hardware.
        It is responsible for the setup and maintenence of the cuda environment and the graphics kernel.
        It communicates to out via a pbo  '''

    def init(self):
        debug("Initializing Engine")
        Globals().load(self)

        # self.print_opencl_info()

        # timing vars
        num_time_events = 3
        self.time_events = False
        self.event_accum_tmp = [0 for i in xrange(num_time_events)]
        self.event_accum = [0 for i in xrange(num_time_events)]
        self.last_frame_time = 0
        self.frame_num = 0

        # fb download vars
        self.new_fb_event = threading.Event()
        self.do_get_fb = False    

        self.do_flash_fb = False
        self.program = None
        self.cl_initialized = False

        return True


    def __del__(self):
        debug("Deleting Engine")    
        self.new_fb_event.set()
        self.pbo = None


    def catch_cl(self, err_num, msg):
        if(err_num != 0):
            error(msg + ": " + ERROR_CODES[err_num])
            sys.exit(0)

    
    def initCL(self):
        debug("Setting up OpenCL")        

        num_platforms = create_string_buffer(4)
        err_num = openCL.clGetPlatformIDs(0, None, num_platforms)
        self.catch_cl(err_num, "counting platforms")
        num_platforms = cast(num_platforms, POINTER(c_int)).contents.value

        platforms = create_string_buffer(4 * num_platforms)
        err_num = openCL.clGetPlatformIDs (num_platforms, platforms, None)
        self.catch_cl(err_num, "getting platforms")
        self.platform = cast(platforms, POINTER(c_int))[0]

        num_devices = create_string_buffer(4)
        err_num = openCL.clGetDeviceIDs(self.platform, DEVICE_TYPE_GPU, 0, None, num_devices);
        self.catch_cl(err_num, "counting devices")
        num_devices = cast(num_devices, POINTER(c_int)).contents.value

        devices = create_string_buffer(4 * num_devices)
        err_num = openCL.clGetDeviceIDs(self.platform, DEVICE_TYPE_GPU, num_devices, devices, None);
        self.catch_cl(err_num, "getting devices")
        self.device = cast(devices, POINTER(c_int))[0]

        self.current_display = gl.glXGetCurrentDisplay()
        self.current_context = gl.glXGetCurrentContext()
        properties = (c_long * 7)(GL_CONTEXT_KHR, self.current_context, GLX_DISPLAY_KHR, self.current_display, CONTEXT_PLATFORM, self.platform, 0)
        err_num = create_string_buffer(4)
        self.ctx = openCL.clCreateContext(properties, 1, (c_int * 1)(self.device), None, None, err_num);
        err_num = cast(err_num, POINTER(c_int)).contents.value
        self.catch_cl(err_num, "creating context")

        err_num = create_string_buffer(4)
        self.queue = openCL.clCreateCommandQueue(self.ctx, self.device, 0, err_num);
        err_num = cast(err_num, POINTER(c_int)).contents.value
        self.catch_cl(err_num, "creating queue")

        # create buffers
        format = (c_uint * 2)(BGRA, FLOAT)

        if(self.app.feedback_buffer):
            # create fb
            err_num = create_string_buffer(4)
            self.fb = openCL.clCreateImage2D(self.ctx, MEM_READ_WRITE, format, self.app.kernel_dim, self.app.kernel_dim, None, None, err_num)
            err_num = cast(err_num, POINTER(c_int)).contents.value
            self.catch_cl(err_num, "creating fb")

            # creat out
            err_num = create_string_buffer(4)
            self.out = openCL.clCreateImage2D(self.ctx, MEM_READ_WRITE, format, self.app.kernel_dim, self.app.kernel_dim, None, None, err_num)
            err_num = cast(err_num, POINTER(c_int)).contents.value
            self.catch_cl(err_num, "creating out")

        # create auxiliary buffer
        err_num = create_string_buffer(4)
        self.aux = openCL.clCreateImage2D(self.ctx, MEM_READ_WRITE, format, self.app.kernel_dim, self.app.kernel_dim, None, None, err_num)
        err_num = cast(err_num, POINTER(c_int)).contents.value
        self.catch_cl(err_num, "creating aux")

        # create pbo
        err_num = create_string_buffer(4)
        self.pbo_ptr = self.interface.renderer.generate_pbo(self.app.kernel_dim)
        self.pbo = openCL.clCreateFromGLBuffer(self.ctx, MEM_WRITE_ONLY, self.pbo_ptr, err_num)
        err_num = cast(err_num, POINTER(c_int)).contents.value
        self.catch_cl(err_num, "create_pbo")
    
        # create compiler & misc data
        self.compiler = Compiler(self.device, self.ctx, self.compiler_callback)
        self.empty = cast(create_string_buffer(16 * self.app.kernel_dim ** 2), POINTER(c_float))
        self.buffers = {}
        self.cl_initialized = True
        self.fb_contents = cast(create_string_buffer(16 * self.app.kernel_dim ** 2), POINTER(c_float))


    def compiler_callback(self, program):

        self.program = program

        err_num = create_string_buffer(4)        
        self.main_kernel = openCL.clCreateKernel(self.program, self.app.kernel, err_num)
        err_num = cast(err_num, POINTER(c_int)).contents.value
        self.catch_cl(err_num, "creating main kernel")        

        #err_num = create_string_buffer(4)        
        #self.post_process = openCL.clCreateKernel(self.program, "post_process", err_num)
        #err_num = cast(err_num, POINTER(c_int)).contents.value
        #self.catch_cl(err_num, "creating post process kernel")


    def do(self):
        ''' Main event loop '''          
        #debug("start do")

        if(not self.cl_initialized):
            self.initCL()
            self.compiler.compile()
        
        self.timings = [time.time()]

        # acquire pbo
        event = create_string_buffer(8)
        err_num = openCL.clEnqueueAcquireGLObjects(self.queue, 1, (c_int * 1)(self.pbo), None, None, event)
        self.catch_cl(err_num, "enque acquire pbo")
        err_num = openCL.clWaitForEvents(1, event)
        self.catch_cl(err_num, "waiting to acquire pbo")
        
        # create args
        if(self.app.feedback_buffer):
            args = [(byref(cast(self.fb, c_void_p)), 8), (byref(cast(self.out, c_void_p)), 8), (byref(cast(self.pbo, c_void_p)), 8)]    
        else:
            args = [(byref(cast(self.pbo, c_void_p)), 8)]    
        
        for data in self.frame:
            if(data["type"] == "float"):
                args.append((byref(c_float(data["val"])), 4))
            elif(data["type"] == "float_array"):
                if(not self.buffers.has_key(data["name"])):
                    err_num = create_string_buffer(4)
                    self.buffers[data["name"]] = openCL.clCreateBuffer(self.ctx, MEM_READ_ONLY, 4 * len(data["val"]), None, err_num)
                    err_num = cast(err_num, POINTER(c_int)).contents.value
                    self.catch_cl(err_num, "create buf")

                err_num = openCL.clEnqueueWriteBuffer(self.queue, self.buffers[data["name"]], TRUE, 0, 4 * len(data["val"]), (c_float * len(data["val"]))(*data["val"]), None, None, None)
                self.catch_cl(err_num, "write buf")

                args.append((byref(cast(self.buffers[data["name"]], c_void_p)), 8))
            elif(data["type"] == "complex_array"):
                if(not self.buffers.has_key(data["name"])):
                    err_num = create_string_buffer(4)
                    self.buffers[data["name"]] = openCL.clCreateBuffer(self.ctx, MEM_READ_ONLY, 4 * len(data["val"]) * 2, None, err_num)
                    err_num = cast(err_num, POINTER(c_int)).contents.value
                    self.catch_cl(err_num, "create buf")

                err_num = openCL.clEnqueueWriteBuffer(self.queue, self.buffers[data["name"]], TRUE, 0, 4 * len(data["val"]) * 2, 
                                                      (c_float * (len(data["val"]) * 2))(*list(itertools.chain(*[(z.real, z.imag) for z in data["val"]]))), None, None, None)
                self.catch_cl(err_num, "write buf")

                args.append((byref(cast(self.buffers[data["name"]], c_void_p)), 8))
                
        for i in xrange(len(args)):
            err_num = openCL.clSetKernelArg(self.main_kernel, i, args[i][1], args[i][0])
            self.catch_cl(err_num, "creating argument %d" % i)

        # execute kernel
        self.timings.append(time.time())
        event = create_string_buffer(8)
        err_num = openCL.clEnqueueNDRangeKernel(self.queue, self.main_kernel, 2, None, 
                                                (c_long * 2)(self.app.kernel_dim, self.app.kernel_dim), 
                                                (c_long * 2)(block_size, block_size), 
                                                None, None, event)
        # DO NOT MOVE THE gc.collect() LINE!  IT **MUST** BE BELOW THE KERNEL EXECUTION LINE!
        gc.collect()

        self.catch_cl(err_num, "enque execute kernel")
        err_num = openCL.clWaitForEvents(1, event)
        self.catch_cl(err_num, "waiting to execute kernel")
        self.timings.append(time.time())

        if(self.app.feedback_buffer):
            # copy out to fb
            event = create_string_buffer(8)
            err_num = openCL.clEnqueueCopyImage(self.queue, self.out, self.fb, (c_long * 3)(0, 0, 0), (c_long * 3)(0, 0, 0), (c_long * 3)(self.app.kernel_dim, self.app.kernel_dim, 1), None, None, event)
            self.catch_cl(err_num, "enque copy fb")
            err_num = openCL.clWaitForEvents(1, event)        
            self.catch_cl(err_num, "waiting to copy fb")

            self.timings.append(time.time())


        # post processing
#        if(self.state.get_par("_POST_PROCESSING") != 0.0):
#            post_args = [args[0], args[2], args[3], args[5]]
#            for i in xrange(len(post_args)):
#                err_num = openCL.clSetKernelArg(self.post_process, i, post_args[i][1], post_args[i][0])
#                self.catch_cl(err_num, "creating post argument %d" % i)
#            event = create_string_buffer(8)
#            err_num = openCL.clEnqueueNDRangeKernel(self.queue, self.post_process, 2, None, 
#                                                    (c_long * 2)(self.app.kernel_dim, self.app.kernel_dim), 
#                                                    (c_long * 2)(block_size, block_size), 
#                                                    None, None, event)
#            self.catch_cl(err_num, "enque post execute kernel")
#            err_num = openCL.clWaitForEvents(1, event)
#            self.catch_cl(err_num, "waiting to execute post kernel")

#            self.timings.append(time.time())

        # release pbo
        event = create_string_buffer(8)
        err_num = openCL.clEnqueueReleaseGLObjects(self.queue, 1, (c_int * 1)(self.pbo), None, None, event)
        self.catch_cl(err_num, "enque release pbo")
        err_num = openCL.clWaitForEvents(1, event)
        self.catch_cl(err_num, "waiting to release pbo")

        self.frame_num += 1
        self.print_timings()

        openCL.clFinish(self.queue)

        #debug("end do")


    def print_opencl_info(self):
        def print_info(obj, info_cls):
            for info_name in sorted(dir(info_cls)):
                if not info_name.startswith("_") and info_name != "to_string":
                    info = getattr(info_cls, info_name)
                    try:
                        info_value = obj.get_info(info)
                    except:
                        info_value = "<error>"

                    debug("%s: %s" % (info_name, info_value))

        for platform in cl.get_platforms():
            debug(75*"=")
            debug(platform)
            debug(75*"=")
            print_info(platform, cl.platform_info)

            for device in platform.get_devices():
                debug(75*"=")
                debug(platform)
                debug(75*"=")
                print_info(device, cl.device_info)


    def print_timings(self):
        if(self.time_events):
            if(self.frame_num % self.app.debug_freq == 0):
                # get times
                times = [1000 * (self.timings[i + 1] - self.timings[i]) for i in xrange(len(self.timings) - 1)]

                # set accumulators
                self.event_accum_tmp = [self.event_accum_tmp[i] + times[i] for i in xrange(len(times))]
                self.event_accum = [self.event_accum[i] + times[i] for i in xrange(len(times))]

                # print times
                for i in range(len(times)):
                    print "event" + str(i) + "-" + str(i + 1) + ": " + str(self.event_accum_tmp[i] / self.app.debug_freq) + "ms"
                    print "event" + str(i) + "-" + str(i + 1) + "~ " + str(self.event_accum[i] / self.frame_num) + "ms"

                # print totals
                print "total cuda:", str(sum(self.event_accum_tmp) / self.app.debug_freq) + "ms"
                print "total cuda~", str(sum(self.event_accum) / self.frame_num) + "ms"

                # print abs times
                abs = 1000 * ((time.time() - self.last_frame_time) % 1) / self.app.debug_freq
                print "python:", abs - sum(self.event_accum_tmp) / self.app.debug_freq
                print "abs:", abs

                # reset tmp accumulator
                self.event_accum_tmp = [0 for i in xrange(len(times))]

                self.last_frame_time = time.time()


    ######################################### PUBLIC ##################################################


    def start(self):
        ''' Start engine '''
        info("Starting engine")        

    
    def compile(self):
        self.compiler.compile()


    def upload_image(self, cl_image, data):
        ''' Upload an image to the DEVICE '''
        debug("Uploading image")

        err_num = openCL.clEnqueueWriteImage(self.queue, cl_image, TRUE, (c_long * 3)(0,0,0), (c_long * 3)(self.app.kernel_dim, self.app.kernel_dim, 1), 0, 0, cast(data, POINTER(c_float)), 0, None,None)
        self.catch_cl(err_num, "uploading image")