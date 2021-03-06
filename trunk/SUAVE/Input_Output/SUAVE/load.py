# Input_Output.SUAVE.load.py
#
# Created By:   Trent Jan 2015

""" Load a native SUAVE file """

# ----------------------------------------------------------------------
#  Imports
# ----------------------------------------------------------------------

from SUAVE.Core.Input_Output import load_data


# ----------------------------------------------------------------------
#  Method
# ----------------------------------------------------------------------

def load(filename):
    """ load data from file """
    
    data = load_data(filename,file_format='pickle')
    
    return data