"""Desktop GUI for the Medical Imaging Archive Toolkit.

A thin Tkinter front-end over ``mia_core``. Workers run on a background thread
and report progress across a queue that the Tk event loop drains; the UI thread
never blocks and only the UI thread touches widgets.
"""
