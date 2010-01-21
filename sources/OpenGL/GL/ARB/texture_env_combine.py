'''OpenGL extension ARB.texture_env_combine

This module customises the behaviour of the 
OpenGL.raw.GL.ARB.texture_env_combine to provide a more 
Python-friendly API
'''
from OpenGL import platform, constants, constant, arrays
from OpenGL import extensions, wrapper
from OpenGL.GL import glget
import ctypes
from OpenGL.raw.GL.ARB.texture_env_combine import *
### END AUTOGENERATED SECTION