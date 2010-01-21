'''OpenGL extension NV.register_combiners

This module customises the behaviour of the 
OpenGL.raw.GL.NV.register_combiners to provide a more 
Python-friendly API
'''
from OpenGL import platform, constants, constant, arrays
from OpenGL import extensions, wrapper
from OpenGL.GL import glget
import ctypes
from OpenGL.raw.GL.NV.register_combiners import *
### END AUTOGENERATED SECTION