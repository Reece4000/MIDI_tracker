from setuptools import setup
from Cython.Build import cythonize

setup(
    name="c_utils",
    ext_modules = cythonize("src/cython/c_utils.pyx")
)