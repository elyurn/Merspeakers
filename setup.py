#!/usr/bin/env python3
# -*- coding:utf-8 -*-

import sys
import os
from cx_Freeze import setup, Executable

script_dir = os.path.dirname(__file__)

base = None
if sys.platform == "win32":
    base = "Win32GUI"

build_exe_options = {"packages": ["os", "subprocess", "json", "PIL", "tkinter", "pygame" , "sys",   "ctypes"], 
                     "excludes": ["asyncio", "cffi", "concurrent", "curses", "distutils", "email", "html",  
                                  "http", "lib2to3", "multiprocessing", "numpy", "pkg_ressources", "psutils", 
				  "pycparser", "pydoc_data", "setuptools", "unittest", "win32com", "xmlrpc"]}

setup(
    name = "Merspeakers",
    version = "0.1",
    options = {"build_exe": build_exe_options},
    description = "Génération de bruits ambiants avec accès à Focusrite Control",
    executables = [Executable("Merspeakers.py",base=base,icon=os.path.join(script_dir, "logo", "icon.ico"))]
)
