'''OpenGL extension ARB.depth_texture

This module customises the behaviour of the 
OpenGL.raw.GL.ARB.depth_texture to provide a more 
Python-friendly API
'''
from OpenGL import platform, constants, constant, arrays
from OpenGL import extensions, wrapper
from OpenGL.GL import glget
import ctypes
from OpenGL.raw.GL.ARB.depth_texture import *
### END AUTOGENERATED SECTION