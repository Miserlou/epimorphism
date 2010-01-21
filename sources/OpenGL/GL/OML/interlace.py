'''OpenGL extension OML.interlace

This module customises the behaviour of the 
OpenGL.raw.GL.OML.interlace to provide a more 
Python-friendly API
'''
from OpenGL import platform, constants, constant, arrays
from OpenGL import extensions, wrapper
from OpenGL.GL import glget
import ctypes
from OpenGL.raw.GL.OML.interlace import *
### END AUTOGENERATED SECTION