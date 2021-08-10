# set QT_API environment variable
import os 
import argparse
os.environ["QT_API"] = "pyqt5"
import qtpy

# qt libraries
from qtpy.QtCore import *
from qtpy.QtWidgets import *
from qtpy.QtGui import *

parser = argparse.ArgumentParser()
parser.add_argument("--simulation", help="Run the GUI with simulated image streams.", action = 'store_true')
args = parser.parse_args()

# app specific libraries
import control.gui_spectrometer as gui
#import control.gui_2cameras_async as gui
#import control.gui_tiscamera as gui

if __name__ == "__main__":

    app = QApplication([])
    if(args.simulation):
        win = gui.OctopiGUI(is_simulation=True)
    else:
        win = gui.OctopiGUI(is_simulation=False)
    win.show()
    app.exec_() #sys.exit(app.exec_())
