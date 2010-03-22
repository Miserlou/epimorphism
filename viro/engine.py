from ctypes import *
from cuda.cuda_defs import *
from cuda.cuda_api import *

from viro.compiler import Compiler
from viro import compiler

import threading
import time
import Image

from common.log import *
set_log("ENGINE")

class Engine(object):
    ''' The Engine object is the applications interface, via cuda, to the graphics hardware.
        It is responsible for the setup and maintenence of the cuda environment and the graphics kernel.
        It communicates to out via a pbo  '''

    def __init__(self, profile):
        debug("Initializing Engine")

        self.profile = profile

        debug("Setting up CUDA")

        # get device
        self.cuda_device = c_int()
        cudaGetDevice(byref(self.cuda_device))

        # get/print properties
        self.cuda_properties = cudaDeviceProp()
        cudaGetDeviceProperties(self.cuda_properties, self.cuda_device)
        debug(str(self.cuda_properties))

        # create frame buffer
        self.channel_desc = cudaCreateChannelDesc(32, 32, 32, 32, cudaChannelFormatKindFloat)
        self.fb = cudaArray_p()
        cudaMallocArray(byref(self.fb), byref(self.channel_desc), self.profile.kernel_dim, self.profile.kernel_dim)

        # data = Image.open("image/input/" + name).convert("RGBA").tostring("raw", "RGBA", 0, -1)

        # create aux buffer
        self.aux_channel_desc = cudaCreateChannelDesc(32, 32, 32, 32, cudaChannelFormatKindFloat)
        self.aux = cudaArray_p()
        cudaMallocArray(byref(self.aux), byref(self.aux_channel_desc), self.profile.kernel_dim, self.profile.kernel_dim)

        # create output_2D
        self.output_2D, self.output_2D_pitch = c_void_p(), c_uint()
        cudaMallocPitch(byref(self.output_2D), byref(self.output_2D_pitch),
                        self.profile.kernel_dim * sizeof(float4), self.profile.kernel_dim)
        cudaMemset2D(self.output_2D, self.output_2D_pitch, 0, self.profile.kernel_dim * sizeof(float4),
                     self.profile.kernel_dim)

        # initialize timing info
        self.time_events = False
        self.frame_count = 0.0
        self.events = [cudaEvent_t() for i in range(4)]
        [cudaEventCreate(byref(event)) for event in self.events]
        self.event_accum_tmp = [0 for i in range(len(self.events) - 1)]
        self.event_accum = [0 for i in range(len(self.events) - 1)]
        self.time_accum = 0

        # set block & grid size
        self.block = dim3(8, 8, 1)
        self.grid = dim3(self.profile.kernel_dim / 8, self.profile.kernel_dim / 8, 1)

        # kernel vars
        self.kernel = None
        self.reset = None

        # malloc host array
        self.host_array = c_void_p()
        cudaMallocHost(byref(self.host_array), 4 * (self.profile.kernel_dim ** 2) * sizeof(c_ubyte))

        # flag to bind texture
        self.new_kernel = None

        # flag to enable aux_b
        self.aux_enabled = True

        # flag to main thread fb reset(reset on startup)
        self.do_reset_fb = True

        # data for main thread fb download
        self.do_get_fb = False
        self.fb_contents = None

        self.pbo = None

        # compiler config
        self.compiler_config = {}

        self.new_kernel_event = threading.Event()
        self.new_fb_event = threading.Event()


    def __del__(self):
        debug("Deleting Engine")

        self.new_kernel_event.set()
        self.new_fb_event.set()

        # clear cuda memory
        cudaFreeArray(self.fb)
        cudaFreeArray(self.aux)
        cudaFree(self.output_2D)
        cudaFree(self.host_array)

        # unregister pbo
        cudaGLUnregisterBufferObject(self.pbo)

        # delete events
        [cudaEventDestroy(event) for event in self.events]


    def sync(self, output):
        ''' Syncs output module with engine '''

        # generate pbo
        self.pbo = output.generate_pbo(self.profile.kernel_dim)

        # register_pbo
        self.pbo_ptr = c_void_p()
        status = cudaGLRegisterBufferObject(self.pbo)
        cudaGLMapBufferObject(byref(self.pbo_ptr), self.pbo)


    def record_event(self, idx):
        # record an event
        if(self.time_events):
            cudaEventRecord(self.events[idx], 0)


    def print_timings(self):
       if(self.time_events):
            # synchronize
            cudaEventSynchronize(self.events[-1])

            # get times
            times = [c_float() for i in range(len(self.events) - 1)]
            [cudaEventElapsedTime(byref(times[i]), self.events[i], self.events[i+1]) for i in range(len(times))]

            # set accumulators
            self.event_accum_tmp = [self.event_accum_tmp[i] + times[i].value for i in range(len(times))]
            self.event_accum = [self.event_accum[i] + times[i].value for i in range(len(times))]

            if(self.frame_count % self.profile.debug_freq == 0):
                # print times
                for i in range(len(times)):
                    print "event" + str(i) + "-" + str(i + 1) + ": " + str(self.event_accum_tmp[i] / self.profile.debug_freq) + "ms"
                    print "event" + str(i) + "-" + str(i + 1) + "~ " + str(self.event_accum[i] / self.frame_count) + "ms"

                # print totals
                print "total: " + str(sum(self.event_accum_tmp) / self.profile.debug_freq) + "ms"
                print "total~ " + str(sum(self.event_accum) / self.frame_count) + "ms"

                # reset tmp accumulator
                self.event_accum_tmp = [0 for i in range(len(self.events) - 1)]


    def get_fb_internal(self):
        ''' This is the internal function called by the main thread to grab the frame buffer '''

        info("Get fb internal")

        # map buffer
        cudaGLMapBufferObject(byref(self.pbo_ptr), self.pbo)

        # copy pbo to host
        res = cudaMemcpy2D(self.host_array, self.profile.kernel_dim * sizeof(c_ubyte) * 4, self.pbo_ptr,
                           self.profile.kernel_dim * sizeof(c_ubyte) * 4, self.profile.kernel_dim * sizeof(c_ubyte) * 4,
                           self.profile.kernel_dim, cudaMemcpyDeviceToHost)

        # return c_ubyte array
        self.fb_contents = (c_ubyte * (4 * (self.profile.kernel_dim ** 2))).from_address(self.host_array.value)
        self.new_fb_event.set()


    def set_new_kernel(self, name):
        ''' Compiler callback '''
        debug("Setting new kernel: %s" % name)

        self.new_kernel_event.set()
        self.new_kernel = name


    def switch_kernel(self):
        ''' Main thread callback to interface with a new kernel '''
        debug("Switching to kernel: %s", self.new_kernel)

        # get functions from kernel library
        (self.kernel, self.reset) = compiler.get_functions(self.new_kernel)
        self.new_kernel = None

        # create texture reference
        self.tex_ref = textureReference_p()
        cudaGetTextureReference(byref(self.tex_ref), "input_texture")

        # set texture parameters
        self.tex_ref.contents.normalized = True
        self.tex_ref.contents.filterMode = cudaFilterModeLinear
        self.tex_ref.contents.addressMode[0] = cudaAddressModeClamp
        self.tex_ref.contents.addressMode[1] = cudaAddressModeClamp

        # bind tex_ref to fb. copy output_2D to fb
        cudaBindTextureToArray(self.tex_ref, self.fb, byref(self.channel_desc))
        cudaMemcpy2DToArray(self.fb, 0, 0, self.output_2D, self.output_2D_pitch, self.profile.kernel_dim * sizeof(float4),
                            self.profile.kernel_dim, cudaMemcpyDeviceToDevice)

        # create aux texture reference
        self.aux_tex_ref = textureReference_p()
        cudaGetTextureReference(byref(self.aux_tex_ref), "aux_texture")

        # set aux texture parameters
        self.aux_tex_ref.contents.normalized = True
        self.aux_tex_ref.contents.filterMode = cudaFilterModeLinear
        self.aux_tex_ref.contents.addressMode[0] = cudaAddressModeClamp
        self.aux_tex_ref.contents.addressMode[1] = cudaAddressModeClamp

        # bind aux tex_ref to aux_b. # copy output_2D to fb
        cudaBindTextureToArray(self.aux_tex_ref, self.aux, byref(self.aux_channel_desc))


    def do(self):
        ''' Main event loop '''

        if(not self.pbo):
            critical("can't render without a pbo")
            import sys
            sys.exit()
            return

        # grab frame buffer
        if(self.do_get_fb):
            self.do_get_fb = False
            self.get_fb_internal()


        # idle until kernel found
        if(not self.kernel):
            self.new_kernel_event.wait()

        # switch kernel if necessary
        if(self.new_kernel) : self.switch_kernel()

        # begin
        self.record_event(0)
        self.frame_count += 1

        # copy constants to kernel
        for name, data in self.frame.items():

            # convert to ctypes
            if(data["type"] == "float"):
                val = c_float(data["val"])
            elif(data["type"] == "float_array"):
                val = (c_float * len(data["val"]))(*[p for p in data["val"]])
            elif(data["type"] == "int_array"):
                val = (c_int * len(data["val"]))(*[p for p in data["val"]])
            elif(data["type"] == "complex_array"):
                val = (float2 * len(data["val"]))(*[(z.real, z.imag) for z in data["val"]])

            # copy
            cudaMemcpyToSymbol(name, byref(val), sizeof(val), 0, cudaMemcpyHostToDevice)

        # call kernel
        cudaConfigureCall(self.grid, self.block, 0, 0)

        if(self.do_reset_fb):
            self.reset(self.output_2D, c_ulong(self.output_2D_pitch.value / sizeof(float4)))
            self.do_reset_fb = False

        else:
            self.kernel(self.output_2D, c_ulong(self.output_2D_pitch.value / sizeof(float4)), self.pbo_ptr,
                        self.profile.kernel_dim, 1.0 / self.profile.kernel_dim, 1.0001 / self.profile.kernel_dim,
                        1.0 / self.profile.FRACT ** 2, 2.0 / (self.profile.kernel_dim * (self.profile.FRACT - 1.0)))

        self.record_event(1)

        # copy data from output_2D
        cudaMemcpy2DToArray(self.fb, 0, 0, self.output_2D, self.output_2D_pitch, self.profile.kernel_dim * sizeof(float4),
                            self.profile.kernel_dim, cudaMemcpyDeviceToDevice)
        self.record_event(2)

        # unmap pbo
        cudaGLUnmapBufferObject(self.pbo)
        self.record_event(3)

        # compute and print timings
        self.print_timings()

        # utility - DON'T REMOVE
        #fb = self.get_fb()
        #r = self.profile.kernel_dim - 5
        #c = self.profile.kernel_dim - 5
        #if(self.frame_count % 20 == 0):
        #    print fb[4 * (r * self.profile.kernel_dim + c) + 0], fb[4 * (r * self.profile.kernel_dim + c) + 1], fb[4 * (r * self.profile.kernel_dim + c) + 2], fb[4 * (r * self.profile.kernel_dim + c) + 3]



    ######################################### PUBLIC ##################################################

    def start(self, compiler_options):
        ''' Start engine '''
        info("Starting engine")

        self.compile(compiler_options)

    def compile(self, compiler_config):
        # compile engine kernel - this needs to be generalized
        debug("Compiling kernel")

        self.compiler_config.update(compiler_config)
        Compiler(self.set_new_kernel, self.compiler_config).start()


    def get_fb(self):
        ''' This function returns an copy of the the current pbo.
            The return value is a dim ** 2 array of 4 * c_ubyte '''
        debug("Retreiving frame buffer")

        # set flag and wait
        self.do_get_fb = True
        self.new_fb_event.clear()
        self.new_fb_event.wait()

        # return contents
        return self.fb_contents


    def pixel_at(self, x, y):
        ''' Utility function which returns the pixel currently at coordinates (x,y) in fb '''

        i = 4 * (y * self.profile.kernel_dim + x)
        buf = self.get_fb()
        return [buf[i], buf[i + 1], buf[i + 2], buf[i + 3]]


    def set_fb(self, data, is_char):
        ''' This manually sets the framebuffer.
            data is a dim ** 2 array of [format]4
            where format = (is_char ? ubyte : float) '''
        debug("Uploading frame buffer")

        if(is_char):
            empty = (c_float * (sizeof(float4) * self.profile.kernel_dim ** 2))(0.0)

            for i in range(0, 4 * self.profile.kernel_dim ** 2):
                empty[i] = c_float(ord(data[i]) / 256.0);

            data = empty

        cudaMemcpyToArray(self.fb, 0, 0, data, sizeof(float4) * self.profile.kernel_dim ** 2, cudaMemcpyHostToDevice)
        # ???copy data to fb???


    def set_aux(self, data, is_char, is_2D):
        ''' This manually sets the auxillary.
            data is a dim ** 2 array of [format]4
            where format = (is_char ? ubyte : float) '''
        debug("Uploading aux buffer")

        if(is_char):
            #empty = (c_float * (sizeof(float4) * self.profile.kernel_dim ** 2))()

            for i in range(0, 4 * self.profile.kernel_dim ** 2):
                self.host_array[i] = c_float(ord(data[i]) / 256.0)

            data = self.host_array#empty

        if(is_2D):
            cudaMemcpy2DToArray(self.fb, 0, 0, data, self.profile.kernel_dim * sizeof(float4),
                                self.profile.kernel_dim * sizeof(float4), self.profile.kernel_dim,
                                cudaMemcpyHostToDevice)
        else:
            cudaMemcpyToArray(self.aux, 0, 0, data, sizeof(float4) * self.profile.kernel_dim ** 2, cudaMemcpyHostToDevice)


    def reset_fb(self):
        ''' This funcion resets the framebuffer to solid black '''
        debug("Resetting frame buffer")

        self.do_reset_fb = True
