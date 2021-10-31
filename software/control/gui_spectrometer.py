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
from pathlib import Path

SINGLE_WINDOW = True # set to False if use separate windows for display and control

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
		
		self.streamHandler_spectrum = core.StreamHandler()
		self.configurationManager_spectrum = core.ConfigurationManager(str(Path.home()) + "/configurations_spectrometer_spectrum.xml",channel='Spectrum')
		self.configurationManager_widefield = core.ConfigurationManager(str(Path.home()) + "/configurations_spectrometer_widefield.xml",channel='Widefield')
		self.liveController = core.LiveController(self.camera_spectrometer,self.microcontroller,self.configurationManager_spectrum)
		self.imageSaver = core.ImageSaver()
		self.imageDisplay = core.ImageDisplay()

		self.streamHandler_widefield = core.StreamHandler()
		self.liveController_widefield = core.LiveController(self.camera_widefield,self.microcontroller,self.configurationManager_widefield)
		self.imageSaver_widefield = core.ImageSaver()
		self.imageDisplay_widefield = core.ImageDisplay()

		self.spectrumExtractor = core.SpectrumExtractor()
		self.spectrumROIManager = core.SpectrumROIManager(self.camera_spectrometer,self.liveController,self.spectrumExtractor)
		
		self.navigationController = core.NavigationController(self.microcontroller)
		self.autofocusController = core.AutoFocusController(self.camera_widefield,self.navigationController,self.liveController_widefield)
		self.multipointController = core.MultiPointController(self.camera_widefield,self.navigationController,self.liveController_widefield,self.autofocusController,self.configurationManager_widefield)

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
		self.camera_spectrometer.set_callback(self.streamHandler_spectrum.on_new_frame)
		self.camera_spectrometer.enable_callback()

		self.camera_widefield.open()
		self.camera_widefield.set_software_triggered_acquisition()
		self.camera_widefield.set_callback(self.streamHandler_widefield.on_new_frame)
		self.camera_widefield.enable_callback()

		# load widgets
		self.cameraSettingWidget_spectrum = widgets.CameraSettingsWidget(self.camera_spectrometer,include_gain_exposure_time=False)
		self.liveControlWidget_spectrum = widgets.LiveControlWidget(self.streamHandler_spectrum,self.liveController,self.configurationManager_spectrum)
		self.recordingControlWidget_spectrum = widgets.RecordingWidget(self.streamHandler_spectrum,self.imageSaver)

		self.cameraSettingWidget_widefield = widgets.CameraSettingsWidget(self.camera_widefield,include_gain_exposure_time=False)
		self.liveControlWidget_widefield = widgets.LiveControlWidget(self.streamHandler_widefield,self.liveController_widefield,self.configurationManager_widefield)
		self.recordingControlWidget_widefield = widgets.RecordingWidget(self.streamHandler_widefield,self.imageSaver_widefield)

		self.spectrumROIManagerWidget = widgets.SpectrumROIManagerWidget(self.spectrumExtractor,self.spectrumROIManager, self.camera_spectrometer)
		self.brightfieldWidget = widgets.BrightfieldWidget(self.liveController)

		self.navigationWidget = widgets.NavigationWidget(self.navigationController)
		self.dacControlWidget = widgets.DACControWidget(self.microcontroller)
		self.autofocusWidget = widgets.AutoFocusWidget(self.autofocusController)
		self.multiPointWidget = widgets.MultiPointWidget(self.multipointController,self.configurationManager_widefield)

		# layout widgets
		layout_spectrum_control = QVBoxLayout()
		layout_spectrum_control.addWidget(self.cameraSettingWidget_spectrum)
		layout_spectrum_control.addWidget(self.liveControlWidget_spectrum)
		layout_spectrum_control.addWidget(self.spectrumROIManagerWidget)
		layout_spectrum_control.addWidget(self.recordingControlWidget_spectrum)

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
		acquisitionTabWidget.addTab(self.multiPointWidget, "Multipoint")
		acquisitionTabWidget.addTab(self.recordingControlWidget_spectrum, "Recording - Spectrum")
		acquisitionTabWidget.addTab(self.recordingControlWidget_widefield, "Recording - Widefield")

		layout = QVBoxLayout()
		layout.addWidget(controlTabWidget)
		layout.addWidget(self.navigationWidget)
		layout.addWidget(self.dacControlWidget)
		layout.addWidget(self.autofocusWidget)
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
		self.streamHandler_spectrum.signal_new_frame_received.connect(self.liveController.on_new_frame)
		self.streamHandler_spectrum.image_to_display.connect(self.imageDisplay.enqueue)
		self.streamHandler_spectrum.packet_image_to_write.connect(self.imageSaver.enqueue)
		self.imageDisplay.image_to_display.connect(self.imageDisplayWindow_spectrum.display_image) # may connect streamHandler directly to imageDisplayWindow
		self.spectrumROIManager.ROI_coordinates.connect(self.streamHandler_spectrum.set_ROIvisualization)

		self.brightfieldWidget.btn_calc_spot.clicked.connect(self.imageDisplayWindow_widefield.slot_calculate_centroid)
		self.brightfieldWidget.btn_show_circle.clicked.connect(self.imageDisplayWindow_widefield.toggle_circle_display)

		# route the new image (once it has arrived) to the spectrumExtractor
		self.streamHandler_spectrum.image_to_spectrum_extraction.connect(self.spectrumExtractor.extract_and_display_the_spectrum)
		self.spectrumExtractor.packet_spectrum.connect(self.spectrumDisplayWindow.plotWidget.plot)

		self.streamHandler_widefield.signal_new_frame_received.connect(self.liveController_widefield.on_new_frame)
		self.streamHandler_widefield.image_to_display.connect(self.imageDisplay_widefield.enqueue)
		self.streamHandler_widefield.packet_image_to_write.connect(self.imageSaver_widefield.enqueue)
		self.imageDisplay_widefield.image_to_display.connect(self.imageDisplayWindow_widefield.display_image) # may connect streamHandler directly to imageDisplayWindow

		self.navigationController.xPos.connect(self.navigationWidget.label_Xpos.setNum)
		self.navigationController.yPos.connect(self.navigationWidget.label_Ypos.setNum)
		self.navigationController.zPos.connect(self.navigationWidget.label_Zpos.setNum)
		self.autofocusController.image_to_display.connect(self.imageDisplayWindow_widefield.display_image)
		# self.multipointController.image_to_display.connect(self.imageDisplayWindow_widefield.display_image)
		self.multipointController.signal_current_configuration.connect(self.liveControlWidget_spectrum.set_microscope_mode)
		# self.multipointController.image_to_display_multi.connect(self.imageArrayDisplayWindow.display_image)
		self.liveControlWidget_spectrum.signal_newExposureTime.connect(self.cameraSettingWidget_spectrum.set_exposure_time)
		self.liveControlWidget_spectrum.signal_newAnalogGain.connect(self.cameraSettingWidget_spectrum.set_analog_gain)
		self.liveControlWidget_spectrum.update_camera_settings()
		self.liveControlWidget_widefield.signal_newExposureTime.connect(self.cameraSettingWidget_widefield.set_exposure_time)
		self.liveControlWidget_widefield.signal_newAnalogGain.connect(self.cameraSettingWidget_widefield.set_analog_gain)
		self.liveControlWidget_widefield.update_camera_settings()

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
		if SINGLE_WINDOW == False:
			self.displayWindow.close()

		self.microcontroller.close()
