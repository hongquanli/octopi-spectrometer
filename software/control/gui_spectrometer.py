# set QT_API environment variable
import os 
os.environ["QT_API"] = "pyqt5"
import qtpy

# qt libraries
from qtpy.QtCore import *
from qtpy.QtWidgets import *
from qtpy.QtGui import *

# app specific libraries
import control.widgets as widgets
import control.camera as camera
import control.camera_TIS as camera_tis
import control.core as core
import control.microcontroller as microcontroller
import pyqtgraph.dockarea as dock

class OctopiGUI(QMainWindow):

	# variables
	fps_software_trigger = 100

	def __init__(self, is_simulation=False, *args, **kwargs):
		super().__init__(*args, **kwargs)

		# load objects
		if is_simulation:
			self.camera_spectrometer = camera_tis.Camera_Simulation(sn=12814458)
			self.camera_widefield = camera.Camera_Simulation()
			self.microcontroller = microcontroller.Microcontroller_Simulation()
		else:
			self.camera_spectrometer = camera_tis.Camera(sn=12814458)
			self.camera_widefield = camera.Camera()
			self.microcontroller = microcontroller.Microcontroller_Simulation()
		
		self.streamHandler = core.StreamHandler()
		self.configurationManager = core.ConfigurationManager()
		self.configurationManager_widefield = core.ConfigurationManager()
		self.liveController = core.LiveController(self.camera_spectrometer,self.microcontroller,self.configurationManager)
		self.imageSaver = core.ImageSaver()
		self.imageDisplay = core.ImageDisplay()

		self.streamHandler_widefield = core.StreamHandler()
		self.liveController_widefield = core.LiveController(self.camera_widefield,self.microcontroller,self.configurationManager_widefield)
		self.imageSaver_widefield = core.ImageSaver()
		self.imageDisplay_widefield = core.ImageDisplay()

		self.spectrumExtractor = core.SpectrumExtractor()
		self.spectrumROIManager = core.SpectrumROIManager(self.camera_spectrometer,self.liveController,self.spectrumExtractor)
		
		'''
		# thread
		self.thread_multiPoint = QThread()
		self.thread_multiPoint.start()
		self.multipointController.moveToThread(self.thread_multiPoint)
		'''

		# open the camera
		# camera start streaming
		self.camera_spectrometer.open()
		self.camera_spectrometer.set_software_triggered_acquisition()
		self.camera_spectrometer.set_callback(self.streamHandler.on_new_frame)
		self.camera_spectrometer.enable_callback()

		self.camera_widefield.open()
		self.camera_widefield.set_software_triggered_acquisition()
		self.camera_widefield.set_callback(self.streamHandler_widefield.on_new_frame)
		self.camera_widefield.enable_callback()

		# load widgets
		self.camera_spectrometerSettingWidget = widgets.CameraSettingsWidget(self.camera_spectrometer,self.liveController)
		self.liveControlWidget = widgets.LiveControlWidget(self.streamHandler,self.liveController,self.configurationManager)
		self.recordingControlWidget = widgets.RecordingWidget(self.streamHandler,self.imageSaver)

		self.cameraSettingWidget_widefield = widgets.CameraSettingsWidget(self.camera_widefield,self.liveController_widefield)
		self.liveControlWidget_widefield = widgets.LiveControlWidget(self.streamHandler_widefield,self.liveController_widefield,self.configurationManager_widefield)
		self.recordingControlWidget_widefield = widgets.RecordingWidget(self.streamHandler_widefield,self.imageSaver_widefield)

		self.spectrumROIManagerWidget = widgets.SpectrumROIManagerWidget(self.spectrumExtractor,self.spectrumROIManager, self.camera_spectrometer)

		self.brightfieldWidget = widgets.BrightfieldWidget(self.liveController)

		# layout widgets
		layout_spectrum_control = QVBoxLayout()
		layout_spectrum_control.addWidget(self.camera_spectrometerSettingWidget)
		layout_spectrum_control.addWidget(self.liveControlWidget)
		layout_spectrum_control.addWidget(self.spectrumROIManagerWidget)
		layout_spectrum_control.addWidget(self.recordingControlWidget)

		layout_widefield_control = QVBoxLayout()
		layout_widefield_control.addWidget(self.cameraSettingWidget_widefield)
		layout_widefield_control.addWidget(self.liveControlWidget_widefield)
		layout_widefield_control.addWidget(self.brightfieldWidget)
		layout_widefield_control.addWidget(self.recordingControlWidget_widefield)

		tab_spectrum_control = QWidget()
		tab_spectrum_control.setLayout(layout_spectrum_control)
		tab_widefield_control = QWidget()
		tab_widefield_control.setLayout(layout_widefield_control)

		controlTabWidget = QTabWidget()
		controlTabWidget.addTab(tab_widefield_control, "Widefield")
		controlTabWidget.addTab(tab_spectrum_control, "Spectrum")
		acquisitionTabWidget = QTabWidget()

		layout = QVBoxLayout()
		layout.addWidget(controlTabWidget)
		layout.addWidget(acquisitionTabWidget)

		# transfer the layout to the central widget
		self.centralWidget = QWidget()
		self.centralWidget.setLayout(layout)
		# self.setCentralWidget(self.centralWidget)

		# load window
		self.imageDisplayWindow_spectrum = core.ImageDisplayWindow()
		# self.imageDisplayWindow_spectrum.show()
		self.imageDisplayWindow_widefield = core.ImageDisplayWindow()
		# self.imageDisplayWindow_widefield.show()
		# load spectrum display window
		self.spectrumDisplayWindow = widgets.SpectrumDisplayWindow()
		# self.spectrumDisplayWindow.show()

		# dock windows
		dock_imageDisplay_widefield = dock.Dock('Widefield', autoOrientation = False)
		dock_imageDisplay_widefield.showTitleBar()
		dock_imageDisplay_widefield.addWidget(self.imageDisplayWindow_widefield.widget)
		dock_imageDisplay_widefield.setStretch(x=5,y=2)

		dock_imageDisplay_spectrum = dock.Dock('Spectrum', autoOrientation = False)
		dock_imageDisplay_spectrum.showTitleBar()
		dock_imageDisplay_spectrum.addWidget(self.imageDisplayWindow_spectrum.widget)
		dock_imageDisplay_spectrum.setStretch(x=5,y=1)

		dock_spectrumDisplay = dock.Dock('Extracted Spectrum', autoOrientation = False)
		dock_spectrumDisplay.showTitleBar()
		dock_spectrumDisplay.addWidget(self.spectrumDisplayWindow.plotWidget)
		dock_spectrumDisplay.setStretch(x=5,y=1)

		display_dockArea = dock.DockArea()
		display_dockArea.addDock(dock_imageDisplay_widefield)
		display_dockArea.addDock(dock_imageDisplay_spectrum,'right')
		display_dockArea.addDock(dock_spectrumDisplay,'bottom',dock_imageDisplay_spectrum)
		
		SINGLE_WINDOW = True # set to False if use separate windows for display and control
		if SINGLE_WINDOW:
			dock_controlPanel = dock.Dock('Controls', autoOrientation = False)
			# dock_controlPanel.showTitleBar()
			dock_controlPanel.addWidget(self.centralWidget)
			dock_controlPanel.setStretch(x=1,y=2)
			display_dockArea.addDock(dock_controlPanel,'right')
			self.setCentralWidget(display_dockArea)
		else:
			self.displayWindow = QMainWindow()
			# self.displayWindow.setWindowFlags(self.windowFlags() | Qt.CustomizeWindowHint)
			# self.displayWindow.setWindowFlags(self.windowFlags() & ~Qt.WindowCloseButtonHint)
			self.displayWindow.setCentralWidget(display_dockArea)
			self.displayWindow.setWindowTitle('Displays')
			self.displayWindow.show()
			# main window
			self.setCentralWidget(self.centralWidget)
	
		# make connections
		self.streamHandler.signal_new_frame_received.connect(self.liveController.on_new_frame)
		self.streamHandler.image_to_display.connect(self.imageDisplay.enqueue)
		self.streamHandler.packet_image_to_write.connect(self.imageSaver.enqueue)
		self.imageDisplay.image_to_display.connect(self.imageDisplayWindow_spectrum.display_image) # may connect streamHandler directly to imageDisplayWindow
		self.spectrumROIManager.ROI_coordinates.connect(self.streamHandler.set_ROIvisualization)
		

		self.brightfieldWidget.btn_calc_spot.clicked.connect(self.imageDisplayWindow_widefield.slot_calculate_centroid)
		self.brightfieldWidget.btn_show_circle.clicked.connect(self.imageDisplayWindow_widefield.toggle_circle_display)

		# route the new image (once it has arrived) to the spectrumExtractor
		self.streamHandler.image_to_spectrum_extraction.connect(self.spectrumExtractor.extract_and_display_the_spectrum)
		self.spectrumExtractor.packet_spectrum.connect(self.spectrumDisplayWindow.plotWidget.plot)

		self.streamHandler_widefield.signal_new_frame_received.connect(self.liveController_widefield.on_new_frame)
		self.streamHandler_widefield.image_to_display.connect(self.imageDisplay_widefield.enqueue)
		self.streamHandler_widefield.packet_image_to_write.connect(self.imageSaver_widefield.enqueue)
		self.imageDisplay_widefield.image_to_display.connect(self.imageDisplayWindow_widefield.display_image) # may connect streamHandler directly to imageDisplayWindow


	def closeEvent(self, event):
		event.accept()
		# self.softwareTriggerGenerator.stop() @@@ => 
		self.liveController.stop_live()
		self.camera_spectrometer.close()
		self.imageSaver.close()
		self.imageDisplay.close()
		self.imageDisplayWindow_spectrum.close()
		self.spectrumDisplayWindow.close()

		self.liveController_widefield.stop_live()
		self.camera_widefield.close()
		self.imageSaver_widefield.close()
		self.imageDisplay_widefield.close()
		self.imageDisplayWindow_widefield.close()
		self.displayWindow.close()
