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

class OctopiGUI(QMainWindow):

	# variables
	fps_software_trigger = 100

	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)

		# load objects
		self.camera_spectrometer = camera_tis.Camera_Simulation(sn=12814458)
		self.camera_widefield = camera.Camera_Simulation()
		self.microcontroller = microcontroller.Microcontroller_Simulation()
		
		self.streamHandler = core.StreamHandler()
		self.liveController = core.LiveController(self.camera_spectrometer,self.microcontroller)
		self.imageSaver = core.ImageSaver()
		self.imageDisplay = core.ImageDisplay()

		self.streamHandler_widefield = core.StreamHandler()
		self.liveController_widefield = core.LiveController(self.camera_widefield,self.microcontroller)
		self.imageSaver_widefield = core.ImageSaver()
		self.imageDisplay_widefield = core.ImageDisplay()

		# instantiate an spectrum extractor object
		self.spectrumExtractor = core.SpectrumExtractor() 
		
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
		self.liveControlWidget = widgets.LiveControlWidget(self.streamHandler,self.liveController)
		self.recordingControlWidget = widgets.RecordingWidget(self.streamHandler,self.imageSaver)

		self.cameraSettingWidget_widefield = widgets.CameraSettingsWidget(self.camera_widefield,self.liveController_widefield)
		self.liveControlWidget_widefield = widgets.LiveControlWidget(self.streamHandler_widefield,self.liveController_widefield)
		self.recordingControlWidget_widefield = widgets.RecordingWidget(self.streamHandler_widefield,self.imageSaver_widefield)

		self.spectrumROIManagerWidget = widgets.SpectrumROIManager(self.spectrumExtractor)

		# layout widgets
		layout = QGridLayout() #layout = QStackedLayout()
		layout.addWidget(self.camera_spectrometerSettingWidget,0,0)
		layout.addWidget(self.liveControlWidget,1,0)
		layout.addWidget(self.spectrumROIManagerWidget,2,0)
		layout.addWidget(self.recordingControlWidget,3,0)

		layout.addWidget(self.cameraSettingWidget_widefield,4,0)
		layout.addWidget(self.liveControlWidget_widefield,5,0)
		layout.addWidget(self.recordingControlWidget_widefield,6,0)

		
		# transfer the layout to the central widget
		self.centralWidget = QWidget()
		self.centralWidget.setLayout(layout)
		self.setCentralWidget(self.centralWidget)

		# load window
		self.imageDisplayWindow = core.ImageDisplayWindow()
		self.imageDisplayWindow.show()

		self.imageDisplayWindow_widefield = core.ImageDisplayWindow()
		self.imageDisplayWindow_widefield.show()
		
		# load spectrum display window
		self.spectrumDisplayWindow = widgets.SpectrumDisplayWindow()
		self.spectrumDisplayWindow.show()

		# make connections
		self.streamHandler.signal_new_frame_received.connect(self.liveController.on_new_frame)
		self.streamHandler.image_to_display.connect(self.imageDisplay.enqueue)
		self.streamHandler.packet_image_to_write.connect(self.imageSaver.enqueue)
		self.imageDisplay.image_to_display.connect(self.imageDisplayWindow.display_image) # may connect streamHandler directly to imageDisplayWindow
		# route the new image (once it has arrived) to the spectrumExtractor
		self.streamHandler.image_to_display.connect(self.spectrumExtractor.extract_and_display_the_spectrum)
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
		self.imageDisplayWindow.close()
		self.spectrumDisplayWindow.close()

		self.liveController_widefield.stop_live()
		self.camera_widefield.close()
		self.imageSaver_widefield.close()
		self.imageDisplay_widefield.close()
		self.imageDisplayWindow_widefield.close()
