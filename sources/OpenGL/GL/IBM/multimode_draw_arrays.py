'''OpenGL extension IBM.multimode_draw_arrays

This module customises the behaviour of the 
OpenGL.raw.GL.IBM.multimode_draw_arrays to provide a more 
Python-friendly API
'''
from OpenGL import platform, constants, constant, arrays
from OpenGL import extensions, wrapper
from OpenGL.GL import glget
import ctypes
from OpenGL.raw.GL.IBM.multimode_draw_arrays import *
### END AUTOGENERATED SECTION