'''OpenGL extension ARB.transpose_matrix

Overview (from the spec)
	
	New functions and tokens are added allowing application matrices
	stored in row major order rather than column major order to be
	transferred to the OpenGL implementation.  This allows an application
	to use standard C-language 2-dimensional arrays (m[row][col]) and
	have the array indices match the expected matrix row and column indexes.
	These arrays are referred to as transpose matrices since they are
	the transpose of the standard matrices passed to OpenGL.
	
	This extension adds an interface for transfering data to and from the
	OpenGL pipeline, it does not change any OpenGL processing or imply any
	changes in state representation.

The official definition of this extension is available here:
	http://oss.sgi.com/projects/ogl-sample/registry/ARB/transpose_matrix.txt

Automatically generated by the get_gl_extensions script, do not edit!
'''
from OpenGL import platform, constants, constant, arrays
from OpenGL import extensions
from OpenGL.GL import glget
import ctypes
EXTENSION_NAME = 'GL_ARB_transpose_matrix'
GL_TRANSPOSE_MODELVIEW_MATRIX_ARB = constant.Constant( 'GL_TRANSPOSE_MODELVIEW_MATRIX_ARB', 0x84E3 )
glget.addGLGetConstant( GL_TRANSPOSE_MODELVIEW_MATRIX_ARB, (4,4) )
GL_TRANSPOSE_PROJECTION_MATRIX_ARB = constant.Constant( 'GL_TRANSPOSE_PROJECTION_MATRIX_ARB', 0x84E4 )
glget.addGLGetConstant( GL_TRANSPOSE_PROJECTION_MATRIX_ARB, (4,4) )
GL_TRANSPOSE_TEXTURE_MATRIX_ARB = constant.Constant( 'GL_TRANSPOSE_TEXTURE_MATRIX_ARB', 0x84E5 )
glget.addGLGetConstant( GL_TRANSPOSE_TEXTURE_MATRIX_ARB, (4,4) )
GL_TRANSPOSE_COLOR_MATRIX_ARB = constant.Constant( 'GL_TRANSPOSE_COLOR_MATRIX_ARB', 0x84E6 )
glget.addGLGetConstant( GL_TRANSPOSE_COLOR_MATRIX_ARB, (4,4) )
glLoadTransposeMatrixfARB = platform.createExtensionFunction( 
	'glLoadTransposeMatrixfARB', dll=platform.GL,
	extension=EXTENSION_NAME,
	resultType=None, 
	argTypes=(arrays.GLfloatArray,),
	doc = 'glLoadTransposeMatrixfARB( GLfloatArray(m) ) -> None',
	argNames = ('m',),
)

glLoadTransposeMatrixdARB = platform.createExtensionFunction( 
	'glLoadTransposeMatrixdARB', dll=platform.GL,
	extension=EXTENSION_NAME,
	resultType=None, 
	argTypes=(arrays.GLdoubleArray,),
	doc = 'glLoadTransposeMatrixdARB( GLdoubleArray(m) ) -> None',
	argNames = ('m',),
)

glMultTransposeMatrixfARB = platform.createExtensionFunction( 
	'glMultTransposeMatrixfARB', dll=platform.GL,
	extension=EXTENSION_NAME,
	resultType=None, 
	argTypes=(arrays.GLfloatArray,),
	doc = 'glMultTransposeMatrixfARB( GLfloatArray(m) ) -> None',
	argNames = ('m',),
)

glMultTransposeMatrixdARB = platform.createExtensionFunction( 
	'glMultTransposeMatrixdARB', dll=platform.GL,
	extension=EXTENSION_NAME,
	resultType=None, 
	argTypes=(arrays.GLdoubleArray,),
	doc = 'glMultTransposeMatrixdARB( GLdoubleArray(m) ) -> None',
	argNames = ('m',),
)


def glInitTransposeMatrixARB():
	'''Return boolean indicating whether this extension is available'''
	return extensions.hasGLExtension( EXTENSION_NAME )
