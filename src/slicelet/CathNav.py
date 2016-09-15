import os
from __main__ import vtk, qt, ctk, slicer

from Guidelet import GuideletLoadable, GuideletLogic, GuideletTest, GuideletWidget
from Guidelet import Guidelet
import logging
import time
import numpy
import threading

#
# CathNav ###
#

class CathNav(GuideletLoadable):
  """Uses GuideletLoadable class, available at:
  """

  def __init__(self, parent):
    GuideletLoadable.__init__(self, parent)
    self.parent.title = "HDR Catheter Navigation"
    self.parent.categories = ["IGT"]
    self.parent.dependencies = []
    self.parent.contributors = ["Tamas Ungi (Perk Lab), Thomas Vaughan (Perk Lab)"]
    self.parent.helpText = """
    This is an example of scripted loadable module bundled in an extension.
    """
    self.parent.acknowledgementText = """
    This file was originally developed by Jean-Christophe Fillion-Robin, Kitware Inc.
    and Steve Pieper, Isomics, Inc. and was partially funded by NIH grant 3P41RR013218-12S1.
""" # replace with organization, grant and thanks.    

#
# CathNavWidget
#

class CathNavWidget(GuideletWidget):
  """Uses GuideletWidget base class, available at:
  """

  def __init__(self, parent = None):
    GuideletWidget.__init__(self, parent)
    
  def setup(self):
    GuideletWidget.setup(self)
    
  def addLauncherWidgets(self):  
    GuideletWidget.addLauncherWidgets(self)
    
  def onConfigurationChanged(self, selectedConfigurationName):
    self.selectedConfigurationName = selectedConfigurationName
    settings = slicer.app.userSettings() 
    settings.setValue(self.moduleName + '/MostRecentConfiguration', selectedConfigurationName)
  
  def createGuideletInstance(self):
    return CathNavGuidelet(None, self.guideletLogic, self.selectedConfigurationName)

  def createGuideletLogic(self):
    return CathNavLogic()

#
# CathNavLogic ###
#

class CathNavLogic(GuideletLogic):
  """Uses GuideletLogic base class, available at:
  """ #TODO add path

  def __init__(self, parent = None):
    GuideletLogic.__init__(self, parent)

  def addValuesToDefaultConfiguration(self):
    GuideletLogic.addValuesToDefaultConfiguration(self)
    moduleDir = os.path.dirname(slicer.modules.cathnav.path)
    defaultSavePathOfCathNav = os.path.join(moduleDir, 'SavedScenes')
    settingList = {'TipToSurfaceDistanceCrossHair' : 'True',
                   'TipToSurfaceDistanceText' : 'True',
                   'TipToSurfaceDistanceTrajectory' : 'True',
                   'NeedleModelToNeedleTip' : '0 1 0 0 0 0 1 0 1 0 0 0 0 0 0 1',
                   'CauteryModelToCauteryTip' : '0 0 1 0 0 -1 0 0 1 0 0 0 0 0 0 1',
                   'PivotCalibrationErrorThresholdMm' :  '0.9',
                   'PivotCalibrationDurationSec' : '15',
                   'FixedPointCalibrationErrorThresholdMm' :  '5.0',
                   'FixedPointCalibrationDurationSec' : '5',
                   'TestMode' : 'False',
                   'RecordingFilenamePrefix' : 'CathNavRecording-',
                   'SavedScenesDirectory': defaultSavePathOfCathNav,#overwrites the default setting param of base
                   'LiveUltrasoundNodeName': 'Image_Chest',
                   }
    self.updateSettings(settingList, 'Default')
#
# CathNavTest ###
#

class CathNavTest(GuideletTest):
  """This is the test case for your scripted module.
  """
  
  def runTest(self):
    """Run as few or as many tests as needed here.
    """
    GuideletTest.runTest(self)
    #self.test_CathNav1() #add applet specific tests here

class CathNavGuidelet(Guidelet):

  # Camera control
  cameraZoomScaleMaxLogarithmic = 5
  cameraZoomScaleMinLogarithmic = 0
  cameraZoomScaleDefaultLogarithmic = 2
  cameraZoomScaleLogarithmic = cameraZoomScaleDefaultLogarithmic
  cameraZoomScaleChangeMagnitudeLogarithmic = 0.25
  cameraTranslationXMaxMm = 100
  cameraTranslationXMinMm = -100
  cameraTranslationXDefaultMm = 0
  cameraTranslationXMm = cameraTranslationXDefaultMm
  cameraTranslationYMaxMm = 100
  cameraTranslationYMinMm = -100
  cameraTranslationYDefaultMm = 0
  cameraTranslationYMm = cameraTranslationYDefaultMm
  cameraTranslationZMaxMm = 100
  cameraTranslationZMinMm = -100
  cameraTranslationZDefaultMm = 100
  cameraTranslationZMm = cameraTranslationZDefaultMm
  cameraTranslationChangeMagnitudeMm = 5;
  
  # Grid control
  gridSizeLeftNumPoints = 2
  gridSizeRightNumPoints = 2
  gridSizeUpNumPoints = 2
  gridSizeDownNumPoints = 2
  gridSpacingHorizontalMm = 10
  gridSpacingVerticalMm = 10
  
  # Calibration
  currentCalibration = 0
  currentCalibration_PIVOT = 0
  currentCalibration_FIXED_POINT = 1
  fixedPointCalibrationMarkups = None
  fixedPointCalibrationTargetTransformNode = None
  fixedPointCalibrationTargetTransformName = None

  def __init__(self, parent, logic, configurationName='Default'):
    logging.debug('CathNavGuidelet.__init__')
    Guidelet.__init__(self, parent, logic, configurationName)
    moduleDirectoryPath = slicer.modules.cathnav.path.replace('CathNav.py', '')

    # Set up main frame.
    self.sliceletDockWidget.setObjectName('CathNavPanel')
    self.sliceletDockWidget.setWindowTitle('CathNav')
    self.mainWindow.setWindowTitle('HDR Catheter navigation')
    self.mainWindow.windowIcon = qt.QIcon(moduleDirectoryPath + '/Resources/Icons/CathNav.png')
    
    self.tumorMarkups_NeedleObserver = None
    self.chestwallMarkups_ChestObserver = None
    self.wirePoints_NeedleObserver = None
    self.pathCount = 0
    self.reconstructionThread = None

    self.setupScene()

    # Setting button open on startup.
    self.calibrationCollapsibleButton.setProperty('collapsed', False)

  def __del__(self):#common
    self.cleanup()

  # Clean up when slicelet is closed
  def cleanup(self):#common
    Guidelet.cleanup(self)
    logging.debug('cleanup')
    if self.tumorMarkups_NeedleObserver:
      self.tumorMarkups_Needle.RemoveObserver(self.tumorMarkups_NeedleObserver)
    if self.chestwallMarkups_Chest:
      self.chestwallMarkups_Chest.RemoveObserver(self.chestwallMarkups_ChestObserver)
    
  def setupScene(self): #applet specific
    logging.debug('setupScene')

    logging.debug('Setup 3D View')
    view = slicer.util.getNode("View1")
    view.SetBoxVisible(False)
    view.SetAxisLabelsVisible(False)
    
    logging.debug('Setup Transforms')
    self.guideTipToGuide = self.initializeLinearTransform('GuideTipToGuide')
    self.loadLinearTransformFromSettings(self.guideTipToGuide)
    self.needleTipToNeedle = self.initializeLinearTransform('NeedleTipToNeedle')
    self.loadLinearTransformFromSettings(self.needleTipToNeedle)
    self.guideModelToGuideTip = self.initializeLinearTransform('GuideModelToGuideTip')
    guideModelToGuideTipMatrix = [ 0, 1, 0, 0,
                                   0, 0, 1, 0,
                                   1, 0, 0, 0,
                                   0, 0, 0, 1 ]
    self.setLinearTransform(self.guideModelToGuideTip, guideModelToGuideTipMatrix)
    self.guideCameraToGuideModel = self.initializeLinearTransform('GuideCameraToGuideModel')
    guideCameraToGuideModelMatrix = [ 0, 1, 0, 0,
                                      1, 0, 0, 0,
                                      0, 0,-1, 0,
                                      0, 0, 0, 1 ]
    self.setLinearTransform(self.guideCameraToGuideModel, guideCameraToGuideModelMatrix)      
    self.needleModelToNeedleTip = self.initializeLinearTransform('NeedleModelToNeedleTip')
    needleModelToNeedleTipMatrix = [ 0, 1, 0, 0,
                                     0, 0, 1, 0,
                                     1, 0, 0, 0,
                                     0, 0, 0, 1 ]
    self.setLinearTransform(self.needleModelToNeedleTip, needleModelToNeedleTipMatrix)
    self.referenceToRas = self.initializeLinearTransform('ChestToRas')
    self.needleToGuide = self.initializeLinearTransform('NeedleToGuide')
    self.planToNeedle = self.initializeLinearTransform('PlanToNeedle')
    self.gridToPlan = self.initializeLinearTransform('GridToPlan')
    self.gridCameraToGrid = self.initializeLinearTransform('GridCameraToGrid')
    self.guideToNeedle = self.initializeLinearTransform('GuideToNeedle')
    self.needleToGuide = self.initializeLinearTransform('NeedleToGuide')
    self.guideToChest = self.initializeLinearTransform('GuideToChest')
    self.wireToChest = self.initializeLinearTransform('WireToChest')
    self.needleToChest = self.initializeLinearTransform('NeedleToChest')

    logging.debug('Setup Models')
    self.guideModel_GuideTip = slicer.util.getNode('GuideModel')
    if not self.guideModel_GuideTip:
      moduleDirectoryPath = slicer.modules.cathnav.path.replace('CathNav.py', '')
      slicer.util.loadModel(qt.QDir.toNativeSeparators(moduleDirectoryPath + 'models/catheterGuide.stl'))
      self.guideModel_GuideTip=slicer.util.getNode(pattern="catheterGuide")
      self.guideModel_GuideTip.GetDisplayNode().SetColor(1.0, 1.0, 0)
      self.guideModel_GuideTip.SetName("GuideModel")
    self.needleModel_NeedleTip = slicer.util.getNode('NeedleModel')
    if not self.needleModel_NeedleTip:
      slicer.modules.createmodels.logic().CreateNeedle(80,0.5,0,0)
      self.needleModel_NeedleTip=slicer.util.getNode(pattern="NeedleModel")
      self.needleModel_NeedleTip.GetDisplayNode().SetColor(0.333333, 1.0, 1.0)
      self.needleModel_NeedleTip.SetName("NeedleModel")
      self.needleModel_NeedleTip.GetDisplayNode().SliceIntersectionVisibilityOn()
    self.wireModel_Wire = slicer.util.getNode('WireModel')
    if not self.wireModel_Wire:
      slicer.modules.createmodels.logic().CreateSphere(0.75)
      self.wireModel_Wire=slicer.util.getNode(pattern="SphereModel")
      self.wireModel_Wire.GetDisplayNode().SetColor(1.0, 0.5, 0.25)
      self.wireModel_Wire.SetName("WireModel")
      self.wireModel_Wire.GetDisplayNode().SliceIntersectionVisibilityOn()
    
    logging.debug('Setup Guidelet')
    Guidelet.setupScene(self)
    
    logging.debug('Setup Calibration')
    self.needleTipMarkups_Guide = self.initializeFiducialList('NeedleTipMarkups_Guide')

    logging.debug('Setup Model Making - Seroma')
    self.tumorMarkups_Needle = self.initializeFiducialList('SeromaMarkups_Needle')
    self.tumorMarkups_NeedleObserver = self.setAndObserveNode(self.tumorMarkups_Needle, self.tumorMarkups_NeedleObserver, self.onTumorMarkupsNodeModified)
    self.tumorModel_Needle = slicer.util.getNode('SeromaModel')
    if not self.tumorModel_Needle:
      self.tumorModel_Needle = slicer.vtkMRMLModelNode()
      self.tumorModel_Needle.SetName("SeromaModel")
      slicer.mrmlScene.AddNode(self.tumorModel_Needle)
      modelDisplayNode = slicer.vtkMRMLModelDisplayNode()
      modelDisplayNode.SetColor(1,0,0) # Red
      modelDisplayNode.BackfaceCullingOff()
      modelDisplayNode.SliceIntersectionVisibilityOn()
      modelDisplayNode.SetSliceIntersectionThickness(4)
      modelDisplayNode.SetOpacity(0.3)
      slicer.mrmlScene.AddNode(modelDisplayNode)
      self.tumorModel_Needle.SetAndObserveDisplayNodeID(modelDisplayNode.GetID())
    logging.debug('Setup Model Making - Chestwall')
    self.chestwallMarkups_Chest = self.initializeFiducialList('ChestwallMarkups_Chest')
    self.chestwallMarkups_ChestObserver = self.setAndObserveNode(self.chestwallMarkups_Chest, self.chestwallMarkups_ChestObserver, self.onChestwallMarkupsNodeModified)
    self.chestwallModel_Chest = slicer.util.getNode('ChestWallModel')
    if not self.chestwallModel_Chest:
      self.chestwallModel_Chest = slicer.vtkMRMLModelNode()
      self.chestwallModel_Chest.SetName("ChestWallModel")
      slicer.mrmlScene.AddNode(self.chestwallModel_Chest)
      modelDisplayNode = slicer.vtkMRMLModelDisplayNode()
      modelDisplayNode.SetColor(0.75,0.75,0.75) # Grey
      modelDisplayNode.BackfaceCullingOff()
      modelDisplayNode.SliceIntersectionVisibilityOn()
      modelDisplayNode.SetSliceIntersectionThickness(4)
      modelDisplayNode.SetOpacity(0.3)
      slicer.mrmlScene.AddNode(modelDisplayNode)
      self.chestwallModel_Chest.SetAndObserveDisplayNodeID(modelDisplayNode.GetID())
    
    logging.debug('Setup Catheter Path Reconstruction')
    self.wirePoints_Needle = self.initializeFiducialList('WirePoints_Needle')
    self.pathCount = 0

    logging.debug('Setup Transform Tree')
    # Guidelet assumes that the top transform in the hierarchy is called referenceToRas.
    # for all intents and purposes, chest == reference
    # so this is effectively "chestToRas"
    self.wireToChest.SetAndObserveTransformNodeID(self.referenceToRas.GetID())
    self.wireModel_Wire.SetAndObserveTransformNodeID(self.wireToChest.GetID())
    self.guideToChest.SetAndObserveTransformNodeID(self.referenceToRas.GetID())
    self.guideTipToGuide.SetAndObserveTransformNodeID(self.guideToChest.GetID())
    self.guideModelToGuideTip.SetAndObserveTransformNodeID(self.guideTipToGuide.GetID())
    self.guideCameraToGuideModel.SetAndObserveTransformNodeID(self.guideModelToGuideTip.GetID())
    self.guideModel_GuideTip.SetAndObserveTransformNodeID(self.guideModelToGuideTip.GetID())
    self.needleToChest.SetAndObserveTransformNodeID(self.referenceToRas.GetID())
    self.needleTipToNeedle.SetAndObserveTransformNodeID(self.needleToChest.GetID())
    self.needleModelToNeedleTip.SetAndObserveTransformNodeID(self.needleTipToNeedle.GetID())
    self.needleModel_NeedleTip.SetAndObserveTransformNodeID(self.needleModelToNeedleTip.GetID())
    self.planToNeedle.SetAndObserveTransformNodeID(self.needleToChest.GetID())
    self.gridToPlan.SetAndObserveTransformNodeID(self.planToNeedle.GetID())
    self.gridCameraToGrid.SetAndObserveTransformNodeID(self.gridToPlan.GetID())
    self.tumorModel_Needle.SetAndObserveTransformNodeID(self.needleToChest.GetID())
    self.tumorMarkups_Needle.SetAndObserveTransformNodeID(self.needleToChest.GetID())
    self.chestwallModel_Chest.SetAndObserveTransformNodeID(self.referenceToRas.GetID())
    self.chestwallMarkups_Chest.SetAndObserveTransformNodeID(self.referenceToRas.GetID())

    # Hide slice view annotations (patient name, scale, color bar, etc.) as they
    # decrease reslicing performance by 20%-100%
    logging.debug('Setup - Hide slice view annotations')
    import DataProbe
    dataProbeUtil=DataProbe.DataProbeLib.DataProbeUtil()
    dataProbeParameterNode=dataProbeUtil.getParameterNode()
    dataProbeParameterNode.SetParameter('showSliceViewAnnotations', '0')

  def initializeLinearTransform(self,name):
    logging.debug('initializeLinearTransform')
    transform = slicer.util.getNode(name)
    if not transform:
      transform=slicer.vtkMRMLLinearTransformNode()
      transform.SetName(name)
      slicer.mrmlScene.AddNode(transform)
    return transform
    
  def setLinearTransform(self,node,values):
    logging.debug('setLinearTransform')
    # array indexing is as follows (row major):
    # [ 0,  1,  2,  3,
    #   4,  5,  6,  7,
    #   8,  9, 10, 11,
    #  12, 13, 14, 15 ]
    if not node:
      logging.error('No node provided to set linear transform.')
      return
    if len(values) != 16:
      logging.error('16 values are needed to set a linear transform.')
      return
    m = vtk.vtkMatrix4x4()
    m.SetElement( 0, 0, values[0] )
    m.SetElement( 0, 1, values[1] )
    m.SetElement( 0, 2, values[2] )
    m.SetElement( 0, 3, values[3] )
    m.SetElement( 1, 0, values[4] )
    m.SetElement( 1, 1, values[5] )
    m.SetElement( 1, 2, values[6] )
    m.SetElement( 1, 3, values[7] )
    m.SetElement( 2, 0, values[8] )
    m.SetElement( 2, 1, values[9] )
    m.SetElement( 2, 2, values[10] )
    m.SetElement( 2, 3, values[11] )
    m.SetElement( 3, 0, values[12] )
    m.SetElement( 3, 1, values[13] )
    m.SetElement( 3, 2, values[14] )
    m.SetElement( 3, 3, values[15] )
    node.SetMatrixTransformToParent(m)
    
  def loadLinearTransformFromSettings(self,node):
    logging.debug('loadLinearTransformFromSettings')
    if not node:
      logging.error('No node provided to set linear transform.')
      return
    m = self.logic.readTransformFromSettings(node.GetName(), self.configurationName)
    if m:
      node.SetMatrixTransformToParent(m)
    
  def initializeFiducialList(self,name):
    logging.debug('initializeFiducialList')
    fiducialList = slicer.util.getNode(name)
    if not fiducialList:
      fiducialList=slicer.vtkMRMLMarkupsFiducialNode()
      fiducialList.SetName(name)
      slicer.mrmlScene.AddNode(fiducialList)
      fiducialList.CreateDefaultDisplayNodes()
      fiducialList.GetDisplayNode().SetTextScale(0)
      fiducialList.SetDisplayVisibility(0)
    return fiducialList
    
  def copyFiducialsFromListToList(self,sourceList,targetList):
    targetList.RemoveAllMarkups()
    numSourceFiducials = sourceList.GetNumberOfFiducials()
    for i in xrange(0,numSourceFiducials):
      pointFromSource = [0.0,0.0,0.0]
      sourceList.GetNthFiducialPosition(i,pointFromSource)
      targetList.AddFiducial(pointFromSource[0],pointFromSource[1],pointFromSource[2])
  
  def createFeaturePanels(self):
    # Create GUI panels.

    self.setupCalibrationPanel()
    featurePanelList = Guidelet.createFeaturePanels(self) # for ultrasound
    self.setupUltrasoundPanel()
    self.setupGuidewirePanel()
    self.setupPlanningPanel()
    self.setupNavigationPanel()
    self.setupReconstructionPanel()

    featurePanelList[len(featurePanelList):] = [self.calibrationCollapsibleButton, self.guidewireCollapsibleButton, self.planningCollapsibleButton, self.navigationCollapsibleButton, self.reconstructionCollapsibleButton]

    return featurePanelList
      
  def setupCalibrationPanel(self):
    logging.debug('setupCalibrationPanel')

    self.calibrationCollapsibleButton = ctk.ctkCollapsibleButton()
    
    self.calibrationCollapsibleButton.setProperty('collapsedHeight', 20)
    self.calibrationCollapsibleButton.text = 'Tool calibration'
    self.sliceletPanelLayout.addWidget(self.calibrationCollapsibleButton)

    self.calibrationLayout = qt.QFormLayout(self.calibrationCollapsibleButton)
    self.calibrationLayout.setContentsMargins(12, 4, 4, 4)
    self.calibrationLayout.setSpacing(4)

    self.calibrationNeedleButton = qt.QPushButton('Start needle calibration')
    self.calibrationLayout.addRow(self.calibrationNeedleButton)

    self.calibrationGuideButton = qt.QPushButton('Start guide calibration')
    self.calibrationLayout.addRow(self.calibrationGuideButton)

    self.countdownLabel = qt.QLabel()
    self.calibrationLayout.addRow(self.countdownLabel)

    self.calibrationSamplingTimer = qt.QTimer()
    self.calibrationSamplingTimer.setInterval(500)
    self.calibrationSamplingTimer.setSingleShot(True)

  def setupUltrasoundPanel(self):
    logging.debug('setupUltrasoundPanel')

    self.ultrasoundCollapsibleButton.text = "Segmentation"

    self.tumorMarkupsPlaceButton = qt.QPushButton("Mark tumor")
    self.tumorMarkupsPlaceButton.setCheckable(True)
    self.tumorMarkupsPlaceButton.setIcon(qt.QIcon(":/Icons/MarkupsMouseModePlace.png"))
    self.ultrasoundLayout.addRow(self.tumorMarkupsPlaceButton)

    self.tumorMarkupsDeleteLastButton = qt.QPushButton("Delete last")
    self.tumorMarkupsDeleteLastButton.setIcon(qt.QIcon(":/Icons/MarkupsDelete.png"))
    self.tumorMarkupsDeleteLastButton.setEnabled(False)

    self.tumorMarkupsDeleteAllButton = qt.QPushButton("Delete all")
    self.tumorMarkupsDeleteAllButton.setIcon(qt.QIcon(":/Icons/MarkupsDeleteAllRows.png"))
    self.tumorMarkupsDeleteAllButton.setEnabled(False)

    tumorHbox = qt.QHBoxLayout()
    tumorHbox.addWidget(self.tumorMarkupsDeleteLastButton)
    tumorHbox.addWidget(self.tumorMarkupsDeleteAllButton)
    self.ultrasoundLayout.addRow(tumorHbox)

    self.chestwallMarkupsPlaceButton = qt.QPushButton("Mark chest wall")
    self.chestwallMarkupsPlaceButton.setCheckable(True)
    self.chestwallMarkupsPlaceButton.setIcon(qt.QIcon(":/Icons/MarkupsMouseModePlace.png"))
    self.ultrasoundLayout.addRow(self.chestwallMarkupsPlaceButton)

    self.chestwallMarkupsDeleteLastButton = qt.QPushButton("Delete last")
    self.chestwallMarkupsDeleteLastButton.setIcon(qt.QIcon(":/Icons/MarkupsDelete.png"))
    self.chestwallMarkupsDeleteLastButton.setEnabled(False)

    self.chestwallMarkupsDeleteAllButton = qt.QPushButton("Delete all")
    self.chestwallMarkupsDeleteAllButton.setIcon(qt.QIcon(":/Icons/MarkupsDeleteAllRows.png"))
    self.chestwallMarkupsDeleteAllButton.setEnabled(False)

    chestwallHbox = qt.QHBoxLayout()
    chestwallHbox.addWidget(self.chestwallMarkupsDeleteLastButton)
    chestwallHbox.addWidget(self.chestwallMarkupsDeleteAllButton)
    self.ultrasoundLayout.addRow(chestwallHbox)
    
  def setupGuidewirePanel(self):
    logging.debug('setupGuidewirePanel')

    self.guidewireCollapsibleButton = ctk.ctkCollapsibleButton()
  
    self.guidewireCollapsibleButton.setProperty('collapsedHeight', 20)
    self.guidewireCollapsibleButton.text = "Guidewire"
    self.sliceletPanelLayout.addWidget(self.guidewireCollapsibleButton)

    self.guidewireCollapsibleLayout = qt.QFormLayout(self.guidewireCollapsibleButton)
    self.guidewireCollapsibleLayout.setContentsMargins(12, 4, 4, 4)
    self.guidewireCollapsibleLayout.setSpacing(4)
    
    self.guidewireCameraButton = qt.QPushButton("Guidewire Camera")
    self.guidewireCameraButton.setCheckable(True)
    self.guidewireCollapsibleLayout.addRow(self.guidewireCameraButton)
    
    # "Camera Control" Collapsible
    self.guidewireCameraTranslationCollapsibleButton = ctk.ctkCollapsibleGroupBox()
    self.guidewireCameraTranslationCollapsibleButton.title = "Translation"
    self.guidewireCameraTranslationCollapsibleButton.collapsed=False
    self.guidewireCollapsibleLayout.addRow(self.guidewireCameraTranslationCollapsibleButton)

    # Layout within the collapsible button
    self.guidewireCameraTranslationFormLayout = qt.QFormLayout(self.guidewireCameraTranslationCollapsibleButton)

    self.guidewireCameraTranslationXLabel = qt.QLabel(qt.Qt.Horizontal,None)
    self.guidewireCameraTranslationXLabel.setText("Left/Right (mm): ")
    self.guidewireCameraTranslationFormLayout.addRow(self.guidewireCameraTranslationXLabel)
    self.guidewireCameraTranslationXIncreaseButton = qt.QPushButton("RIGHT")
    self.guidewireCameraTranslationXIncreaseButton.setEnabled(False)
    self.guidewireCameraTranslationXDecreaseButton = qt.QPushButton("LEFT")
    self.guidewireCameraTranslationXDecreaseButton.setEnabled(False)
    self.guidewireCameraTranslationXHBoxButtons = qt.QHBoxLayout()
    self.guidewireCameraTranslationXHBoxButtons.addWidget(self.guidewireCameraTranslationXDecreaseButton)
    self.guidewireCameraTranslationXHBoxButtons.addWidget(self.guidewireCameraTranslationXIncreaseButton)
    self.guidewireCameraTranslationFormLayout.addRow(self.guidewireCameraTranslationXHBoxButtons)

    self.guidewireCameraTranslationYLabel = qt.QLabel(qt.Qt.Horizontal,None)
    self.guidewireCameraTranslationYLabel.setText("Up/Down (mm): ")
    self.guidewireCameraTranslationFormLayout.addRow(self.guidewireCameraTranslationYLabel)
    self.guidewireCameraTranslationYIncreaseButton = qt.QPushButton("UP")
    self.guidewireCameraTranslationYIncreaseButton.setEnabled(False)
    self.guidewireCameraTranslationYDecreaseButton = qt.QPushButton("DOWN")
    self.guidewireCameraTranslationYDecreaseButton.setEnabled(False)
    self.guidewireCameraTranslationYHBoxButtons = qt.QHBoxLayout()
    self.guidewireCameraTranslationYHBoxButtons.addWidget(self.guidewireCameraTranslationYDecreaseButton)
    self.guidewireCameraTranslationYHBoxButtons.addWidget(self.guidewireCameraTranslationYIncreaseButton)
    self.guidewireCameraTranslationFormLayout.addRow(self.guidewireCameraTranslationYHBoxButtons)
    
    self.guidewireCameraTranslationZLabel = qt.QLabel(qt.Qt.Horizontal,None)
    self.guidewireCameraTranslationZLabel.setText("Forward/Back (mm): ")
    self.guidewireCameraTranslationFormLayout.addRow(self.guidewireCameraTranslationZLabel)
    self.guidewireCameraTranslationZIncreaseButton = qt.QPushButton("FORWARD")
    self.guidewireCameraTranslationZIncreaseButton.setEnabled(False)
    self.guidewireCameraTranslationZDecreaseButton = qt.QPushButton("BACK")
    self.guidewireCameraTranslationZDecreaseButton.setEnabled(False)
    self.guidewireCameraTranslationZHBoxButtons = qt.QHBoxLayout()
    self.guidewireCameraTranslationZHBoxButtons.addWidget(self.guidewireCameraTranslationZIncreaseButton)
    self.guidewireCameraTranslationZHBoxButtons.addWidget(self.guidewireCameraTranslationZDecreaseButton)
    self.guidewireCameraTranslationFormLayout.addRow(self.guidewireCameraTranslationZHBoxButtons)
    
    # "Camera Control" Collapsible
    self.guidewireZoomCollapsibleButton = ctk.ctkCollapsibleGroupBox()
    self.guidewireZoomCollapsibleButton.collapsed=False
    self.guidewireZoomCollapsibleButton.title = "Zoom"
    self.guidewireCollapsibleLayout.addRow(self.guidewireZoomCollapsibleButton)

    # Layout within the collapsible button
    self.guidewireZoomFormLayout = qt.QFormLayout(self.guidewireZoomCollapsibleButton)
    
    # Camera distance to focal point slider
    self.guidewireCameraZoomLabel = qt.QLabel(qt.Qt.Horizontal,None)
    self.guidewireCameraZoomLabel.setText("Zoom in/out (scale): ")
    self.guidewireZoomFormLayout.addRow(self.guidewireCameraZoomLabel)
    self.guidewireCameraZoomButtonIncrease = qt.QPushButton("+")
    self.guidewireCameraZoomButtonIncrease.setEnabled(False)
    self.guidewireCameraZoomButtonDecrease = qt.QPushButton("-")
    self.guidewireCameraZoomButtonDecrease.setEnabled(False)
    self.guidewireCameraZoomButtons = qt.QHBoxLayout()
    self.guidewireCameraZoomButtons.addWidget(self.guidewireCameraZoomButtonDecrease)
    self.guidewireCameraZoomButtons.addWidget(self.guidewireCameraZoomButtonIncrease)
    self.guidewireZoomFormLayout.addRow(self.guidewireCameraZoomButtons)
    
  def setupPlanningPanel(self):
    logging.debug('setupPlanningPanel')

    self.planningCollapsibleButton = ctk.ctkCollapsibleButton()
  
    self.planningCollapsibleButton.setProperty('collapsedHeight', 20)
    self.planningCollapsibleButton.text = "Planning"
    self.sliceletPanelLayout.addWidget(self.planningCollapsibleButton)

    self.planningCollapsibleLayout = qt.QFormLayout(self.planningCollapsibleButton)
    self.planningCollapsibleLayout.setContentsMargins(12, 4, 4, 4)
    self.planningCollapsibleLayout.setSpacing(4)
    
    # Load icons
    logging.debug('Loading grid icons')
    iconDirectoryPath = slicer.modules.cathnav.path.replace('CathNav.py', '/Resources/Icons/')
    iconGridAddRight    = qt.QIcon(iconDirectoryPath + "gridAddRight.png")
    iconGridRemoveRight = qt.QIcon(iconDirectoryPath + "gridRemoveRight.png")
    iconGridAddDown     = qt.QIcon(iconDirectoryPath + "gridAddDown.png")
    iconGridRemoveDown  = qt.QIcon(iconDirectoryPath + "gridRemoveDown.png")
    iconGridAddLeft     = qt.QIcon(iconDirectoryPath + "gridAddLeft.png")
    iconGridRemoveLeft  = qt.QIcon(iconDirectoryPath + "gridRemoveLeft.png")
    iconGridAddUp       = qt.QIcon(iconDirectoryPath + "gridAddUp.png")
    iconGridRemoveUp    = qt.QIcon(iconDirectoryPath + "gridRemoveUp.png")
    iconGridBuild       = qt.QIcon(iconDirectoryPath + "gridBuild.png")
    iconGridIncHorSpace = qt.QIcon(iconDirectoryPath + "gridSpaceHorizontalOut.png")
    iconGridDecHorSpace = qt.QIcon(iconDirectoryPath + "gridSpaceHorizontalIn.png")
    iconGridIncVerSpace = qt.QIcon(iconDirectoryPath + "gridSpaceVerticalOut.png")
    iconGridDecVerSpace = qt.QIcon(iconDirectoryPath + "gridSpaceVerticalIn.png")
    
    # Grid creation
    self.planningCreateGridButton = qt.QPushButton(iconGridBuild,"Create grid")
    self.planningCollapsibleLayout.addRow(self.planningCreateGridButton)
    
    # "Grid Parameters" Collapsible
    self.planningGridCollapsibleButton = ctk.ctkCollapsibleGroupBox()
    self.planningGridCollapsibleButton.collapsed=False
    self.planningGridCollapsibleButton.title = "Grid Parameters"
    self.planningCollapsibleLayout.addRow(self.planningGridCollapsibleButton)

    # Layout within the collapsible button
    self.planningFormLayout = qt.QFormLayout(self.planningGridCollapsibleButton)
    
    # Various grid settings
    self.planningGridSpacingHorizontalLabel = qt.QLabel(qt.Qt.Horizontal,None)
    self.planningGridSpacingHorizontalLabel.setText("Grid spacing (horizontal):")  
    self.planningFormLayout.addRow(self.planningGridSpacingHorizontalLabel)
    
    self.planningGridSpacingHorizontalIncrease = qt.QPushButton(iconGridIncHorSpace,"")
    self.planningGridSpacingHorizontalDecrease = qt.QPushButton(iconGridDecHorSpace,"")
    self.planningGridSpacingHorizontalButtons = qt.QHBoxLayout()
    self.planningGridSpacingHorizontalButtons.addWidget(self.planningGridSpacingHorizontalDecrease)
    self.planningGridSpacingHorizontalButtons.addWidget(self.planningGridSpacingHorizontalIncrease)
    self.planningFormLayout.addRow(self.planningGridSpacingHorizontalButtons)
    
    self.planningGridSpacingVerticalLabel = qt.QLabel(qt.Qt.Horizontal,None)
    self.planningGridSpacingVerticalLabel.setText("Grid spacing (vertical):")  
    self.planningFormLayout.addRow(self.planningGridSpacingVerticalLabel)
    
    self.planningGridSpacingVerticalIncrease = qt.QPushButton(iconGridIncVerSpace,"")
    self.planningGridSpacingVerticalDecrease = qt.QPushButton(iconGridDecVerSpace,"")
    self.planningGridSpacingVerticalButtons = qt.QVBoxLayout()
    self.planningGridSpacingVerticalButtons.addWidget(self.planningGridSpacingVerticalIncrease)
    self.planningGridSpacingVerticalButtons.addWidget(self.planningGridSpacingVerticalDecrease)
    self.planningFormLayout.addRow(self.planningGridSpacingVerticalButtons)

    self.planningGridSizeLabel = qt.QLabel(qt.Qt.Horizontal,None)
    self.planningGridSizeLabel.setText("Grid size:")  
    self.planningFormLayout.addRow(self.planningGridSizeLabel)
    
    self.planningGridSizeLeftIncrease = qt.QPushButton(iconGridAddLeft,"")
    self.planningGridSizeLeftDecrease = qt.QPushButton(iconGridRemoveLeft,"")
    self.planningGridSizeLeftButtons = qt.QHBoxLayout()
    self.planningGridSizeLeftButtons.addWidget(self.planningGridSizeLeftIncrease)
    self.planningGridSizeLeftButtons.addWidget(self.planningGridSizeLeftDecrease)
    
    self.planningGridSizeRightIncrease = qt.QPushButton(iconGridAddRight,"")
    self.planningGridSizeRightDecrease = qt.QPushButton(iconGridRemoveRight,"")
    self.planningGridSizeRightButtons = qt.QHBoxLayout()
    self.planningGridSizeRightButtons.addWidget(self.planningGridSizeRightDecrease)
    self.planningGridSizeRightButtons.addWidget(self.planningGridSizeRightIncrease)
    
    self.planningGridSizeUpIncrease = qt.QPushButton(iconGridAddUp,"")
    self.planningGridSizeUpDecrease = qt.QPushButton(iconGridRemoveUp,"")
    self.planningGridSizeUpButtons = qt.QVBoxLayout()
    self.planningGridSizeUpButtons.addWidget(self.planningGridSizeUpIncrease)
    self.planningGridSizeUpButtons.addWidget(self.planningGridSizeUpDecrease)
    
    self.planningGridSizeDownIncrease = qt.QPushButton(iconGridAddDown,"")
    self.planningGridSizeDownDecrease = qt.QPushButton(iconGridRemoveDown,"")
    self.planningGridSizeDownButtons = qt.QVBoxLayout()
    self.planningGridSizeDownButtons.addWidget(self.planningGridSizeDownDecrease)
    self.planningGridSizeDownButtons.addWidget(self.planningGridSizeDownIncrease)
    
    self.planningGridSizeButtonGrid = qt.QGridLayout()
    self.planningGridSizeButtonGrid.addLayout(self.planningGridSizeUpButtons,0,1)
    self.planningGridSizeButtonGrid.addLayout(self.planningGridSizeDownButtons,2,1)
    self.planningGridSizeButtonGrid.addLayout(self.planningGridSizeLeftButtons,1,0)
    self.planningGridSizeButtonGrid.addLayout(self.planningGridSizeRightButtons,1,2)
    self.planningFormLayout.addRow(self.planningGridSizeButtonGrid)
    
    self.gridRotationLabel = qt.QLabel(qt.Qt.Horizontal,None)
    self.gridRotationLabel.setText("Grid rotation (degrees): ")
    self.gridRotationSlider = slicer.qMRMLSliderWidget()
    self.gridRotationSlider.minimum = -180 # degrees
    self.gridRotationSlider.maximum = 180 # degrees
    self.gridRotationSlider.value = 0 # degrees
    self.planningFormLayout.addRow(self.gridRotationLabel,self.gridRotationSlider)

  def setupNavigationPanel(self):
    logging.debug('setupNavigationPanel')

    self.navigationCollapsibleButton = ctk.ctkCollapsibleButton()
  
    self.navigationCollapsibleButton.setProperty('collapsedHeight', 20)
    self.navigationCollapsibleButton.text = "Navigation"
    self.sliceletPanelLayout.addWidget(self.navigationCollapsibleButton)

    self.navigationCollapsibleLayout = qt.QFormLayout(self.navigationCollapsibleButton)
    self.navigationCollapsibleLayout.setContentsMargins(12, 4, 4, 4)
    self.navigationCollapsibleLayout.setSpacing(4)
    
    self.navigationCameraButton = qt.QPushButton("Navigation Camera")
    self.navigationCameraButton.setCheckable(True)
    self.navigationCollapsibleLayout.addRow(self.navigationCameraButton)
    
    # "Camera Control" Collapsible
    self.navigationCameraTranslationCollapsibleButton = ctk.ctkCollapsibleGroupBox()
    self.navigationCameraTranslationCollapsibleButton.title = "Translation"
    self.navigationCameraTranslationCollapsibleButton.collapsed=False
    self.navigationCollapsibleLayout.addRow(self.navigationCameraTranslationCollapsibleButton)

    # Layout within the collapsible button
    self.navigationCameraTranslationFormLayout = qt.QFormLayout(self.navigationCameraTranslationCollapsibleButton)

    self.navigationCameraTranslationXLabel = qt.QLabel(qt.Qt.Horizontal,None)
    self.navigationCameraTranslationXLabel.setText("Left/Right (mm): ")
    self.navigationCameraTranslationFormLayout.addRow(self.navigationCameraTranslationXLabel)
    self.navigationCameraTranslationXIncreaseButton = qt.QPushButton("RIGHT")
    self.navigationCameraTranslationXIncreaseButton.setEnabled(False)
    self.navigationCameraTranslationXDecreaseButton = qt.QPushButton("LEFT")
    self.navigationCameraTranslationXDecreaseButton.setEnabled(False)
    self.navigationCameraTranslationXHBoxButtons = qt.QHBoxLayout()
    self.navigationCameraTranslationXHBoxButtons.addWidget(self.navigationCameraTranslationXDecreaseButton)
    self.navigationCameraTranslationXHBoxButtons.addWidget(self.navigationCameraTranslationXIncreaseButton)
    self.navigationCameraTranslationFormLayout.addRow(self.navigationCameraTranslationXHBoxButtons)

    self.navigationCameraTranslationYLabel = qt.QLabel(qt.Qt.Horizontal,None)
    self.navigationCameraTranslationYLabel.setText("Up/Down (mm): ")
    self.navigationCameraTranslationFormLayout.addRow(self.navigationCameraTranslationYLabel)
    self.navigationCameraTranslationYIncreaseButton = qt.QPushButton("UP")
    self.navigationCameraTranslationYIncreaseButton.setEnabled(False)
    self.navigationCameraTranslationYDecreaseButton = qt.QPushButton("DOWN")
    self.navigationCameraTranslationYDecreaseButton.setEnabled(False)
    self.navigationCameraTranslationYHBoxButtons = qt.QHBoxLayout()
    self.navigationCameraTranslationYHBoxButtons.addWidget(self.navigationCameraTranslationYDecreaseButton)
    self.navigationCameraTranslationYHBoxButtons.addWidget(self.navigationCameraTranslationYIncreaseButton)
    self.navigationCameraTranslationFormLayout.addRow(self.navigationCameraTranslationYHBoxButtons)
    
    self.navigationCameraTranslationZLabel = qt.QLabel(qt.Qt.Horizontal,None)
    self.navigationCameraTranslationZLabel.setText("Forward/Back (mm): ")
    self.navigationCameraTranslationFormLayout.addRow(self.navigationCameraTranslationZLabel)
    self.navigationCameraTranslationZIncreaseButton = qt.QPushButton("BACK")
    self.navigationCameraTranslationZIncreaseButton.setEnabled(False)
    self.navigationCameraTranslationZDecreaseButton = qt.QPushButton("FORWARD")
    self.navigationCameraTranslationZDecreaseButton.setEnabled(False)
    self.navigationCameraTranslationZHBoxButtons = qt.QHBoxLayout()
    self.navigationCameraTranslationZHBoxButtons.addWidget(self.navigationCameraTranslationZIncreaseButton)
    self.navigationCameraTranslationZHBoxButtons.addWidget(self.navigationCameraTranslationZDecreaseButton)
    self.navigationCameraTranslationFormLayout.addRow(self.navigationCameraTranslationZHBoxButtons)
    
    # "Camera Control" Collapsible
    self.navigationZoomCollapsibleButton = ctk.ctkCollapsibleGroupBox()
    self.navigationZoomCollapsibleButton.collapsed=False
    self.navigationZoomCollapsibleButton.title = "Zoom"
    self.navigationCollapsibleLayout.addRow(self.navigationZoomCollapsibleButton)

    # Layout within the collapsible button
    self.navigationZoomFormLayout = qt.QFormLayout(self.navigationZoomCollapsibleButton)
    
    # Camera distance to focal point slider
    self.navigationCameraZoomLabel = qt.QLabel(qt.Qt.Horizontal,None)
    self.navigationCameraZoomLabel.setText("Zoom in/out (scale): ")
    self.navigationZoomFormLayout.addRow(self.navigationCameraZoomLabel)
    self.navigationCameraZoomButtonIncrease = qt.QPushButton("+")
    self.navigationCameraZoomButtonIncrease.setEnabled(False)
    self.navigationCameraZoomButtonDecrease = qt.QPushButton("-")
    self.navigationCameraZoomButtonDecrease.setEnabled(False)
    self.navigationCameraZoomButtons = qt.QHBoxLayout()
    self.navigationCameraZoomButtons.addWidget(self.navigationCameraZoomButtonDecrease)
    self.navigationCameraZoomButtons.addWidget(self.navigationCameraZoomButtonIncrease)
    self.navigationZoomFormLayout.addRow(self.navigationCameraZoomButtons)
    
  def setupReconstructionPanel(self):
    logging.debug('CathNav.setupReconstructionPanel()')
    self.reconstructionCollapsibleButton = ctk.ctkCollapsibleButton()
  
    self.reconstructionCollapsibleButton.setProperty('collapsedHeight', 20)
    self.reconstructionCollapsibleButton.text = "Reconstruction"
    self.sliceletPanelLayout.addWidget(self.reconstructionCollapsibleButton)

    self.reconstructionCollapsibleLayout = qt.QFormLayout(self.reconstructionCollapsibleButton)
    self.reconstructionCollapsibleLayout.setContentsMargins(12, 4, 4, 4)
    self.reconstructionCollapsibleLayout.setSpacing(4)
    
    self.reconstructionCollectPointsButton = qt.QPushButton("Collect Points")
    self.reconstructionCollectPointsButton.setCheckable(True)
    self.reconstructionCollapsibleLayout.addRow(self.reconstructionCollectPointsButton)
    
    self.reconstructionDeleteLastButton = qt.QPushButton("Delete Last Path")
    self.reconstructionDeleteLastButton.setCheckable(False)
    self.reconstructionCollapsibleLayout.addRow(self.reconstructionDeleteLastButton)
    
    self.reconstructionCameraButton = qt.QPushButton("Right Camera")
    self.reconstructionCameraButton.setCheckable(True)
    self.reconstructionCollapsibleLayout.addRow(self.reconstructionCameraButton)
    
  def setupConnections(self):
    logging.debug('CathNav.setupConnections()')
    Guidelet.setupConnections(self)

    self.calibrationCollapsibleButton.connect('toggled(bool)', self.onCalibrationPanelToggled)
    self.guidewireCollapsibleButton.connect('toggled(bool)', self.onCommon3DPanelToggled)
    self.planningCollapsibleButton.connect('toggled(bool)', self.onCommon3DPanelToggled)
    self.navigationCollapsibleButton.connect('toggled(bool)', self.onCommon3DPanelToggled)
    self.reconstructionCollapsibleButton.connect('toggled(bool)', self.onCommon3DPanelToggled)

    # calibration panel
    self.pivotCalibrationLogic=slicer.modules.pivotcalibration.logic()
    
    self.calibrationGuideButton.connect('clicked()', self.onCalibrationGuideClicked)
    self.calibrationNeedleButton.connect('clicked()', self.onCalibrationNeedleClicked)
    
    self.calibrationSamplingTimer.connect('timeout()',self.onCalibrationSamplingTimeout)
    
    import CollectFiducialsSupplement
    self.collectFiducialsSupplementLogic = CollectFiducialsSupplement.CollectFiducialsSupplementLogic()

    # ultrasound panel
    self.tumorMarkupsPlaceButton.connect('clicked(bool)', self.onTumorMarkupsPlaceClicked)
    self.tumorMarkupsDeleteLastButton.connect('clicked()', self.onTumorMarkupsDeleteLastClicked)
    self.tumorMarkupsDeleteAllButton.connect('clicked()', self.onTumorMarkupsDeleteAllClicked)

    self.chestwallMarkupsPlaceButton.connect('clicked(bool)', self.onChestwallMarkupsPlaceClicked)
    self.chestwallMarkupsDeleteLastButton.connect('clicked()', self.onChestwallMarkupsDeleteLastClicked)
    self.chestwallMarkupsDeleteAllButton.connect('clicked()', self.onChestwallMarkupsDeleteAllClicked)

    # guidewire panel
    import Viewpoint
    self.viewpointLogic = Viewpoint.ViewpointLogic()
    self.guidewireCameraZoomButtonIncrease.connect('clicked()', self.cameraZoomIncrease)
    self.guidewireCameraZoomButtonDecrease.connect('clicked()', self.cameraZoomDecrease)
    self.guidewireCameraTranslationXIncreaseButton.connect('clicked()', self.cameraTranslationXIncrease)
    self.guidewireCameraTranslationXDecreaseButton.connect('clicked()', self.cameraTranslationXDecrease)
    self.guidewireCameraTranslationYIncreaseButton.connect('clicked()', self.cameraTranslationYIncrease)
    self.guidewireCameraTranslationYDecreaseButton.connect('clicked()', self.cameraTranslationYDecrease)
    self.guidewireCameraTranslationZIncreaseButton.connect('clicked()', self.cameraTranslationZIncrease)
    self.guidewireCameraTranslationZDecreaseButton.connect('clicked()', self.cameraTranslationZDecrease)
    self.guidewireCameraButton.connect('clicked()', self.onGuidewireCameraButtonClicked)
    
    # planning panel
    import InsertionGridPlanner
    self.planningLogic = InsertionGridPlanner.InsertionGridPlannerLogic()
    self.planningCreateGridButton.connect('clicked()', self.onCreatePlanButtonClicked)
    self.planningGridSizeLeftIncrease.connect('clicked()', self.gridSizeLeftIncrease)
    self.planningGridSizeLeftDecrease.connect('clicked()', self.gridSizeLeftDecrease)
    self.planningGridSizeRightIncrease.connect('clicked()', self.gridSizeRightIncrease)
    self.planningGridSizeRightDecrease.connect('clicked()', self.gridSizeRightDecrease)
    self.planningGridSizeUpIncrease.connect('clicked()', self.gridSizeUpIncrease)
    self.planningGridSizeUpDecrease.connect('clicked()', self.gridSizeUpDecrease)
    self.planningGridSizeDownIncrease.connect('clicked()', self.gridSizeDownIncrease)
    self.planningGridSizeDownDecrease.connect('clicked()', self.gridSizeDownDecrease)
    self.planningGridSpacingHorizontalIncrease.connect('clicked()', self.gridSpacingHorizontalIncrease)
    self.planningGridSpacingHorizontalDecrease.connect('clicked()', self.gridSpacingHorizontalDecrease)
    self.planningGridSpacingVerticalIncrease.connect('clicked()', self.gridSpacingVerticalIncrease)
    self.planningGridSpacingVerticalDecrease.connect('clicked()', self.gridSpacingVerticalDecrease)
    self.gridRotationSlider.connect('valueChanged(double)', self.rotateGrid)
    
    # navigation
    self.navigationCameraZoomButtonIncrease.connect('clicked()', self.cameraZoomIncrease)
    self.navigationCameraZoomButtonDecrease.connect('clicked()', self.cameraZoomDecrease)
    self.navigationCameraTranslationXIncreaseButton.connect('clicked()', self.cameraTranslationXIncrease)
    self.navigationCameraTranslationXDecreaseButton.connect('clicked()', self.cameraTranslationXDecrease)
    self.navigationCameraTranslationYIncreaseButton.connect('clicked()', self.cameraTranslationYIncrease)
    self.navigationCameraTranslationYDecreaseButton.connect('clicked()', self.cameraTranslationYDecrease)
    self.navigationCameraTranslationZIncreaseButton.connect('clicked()', self.cameraTranslationZIncrease)
    self.navigationCameraButton.connect('clicked()', self.onNavigationCameraButtonClicked)
    
    # reconstruction panel
    self.MarkupsToModelClosedSurfaceNode = slicer.vtkMRMLMarkupsToModelNode()
    self.MarkupsToModelClosedSurfaceNode.SetModelType(self.MarkupsToModelClosedSurfaceNode.ClosedSurface)
    self.MarkupsToModelClosedSurfaceNode.SetCleanMarkups(True)
    self.MarkupsToModelClosedSurfaceNode.SetButterflySubdivision(True)
    self.MarkupsToModelClosedSurfaceNode.SetConvexHull(True)
    self.MarkupsToModelClosedSurfaceNode.SetDelaunayAlpha(0.0)
    self.MarkupsToModelClosedSurfaceNode.SetAutoUpdateOutput(False)
    self.MarkupsToModelClosedSurfaceNode.SetName('MarkupsToModel_ClosedSurfaces')
    slicer.mrmlScene.AddNode(self.MarkupsToModelClosedSurfaceNode)
    
    self.MarkupsToModelCurveNode = slicer.vtkMRMLMarkupsToModelNode()
    self.MarkupsToModelCurveNode.SetModelType(self.MarkupsToModelCurveNode.Curve)
    self.MarkupsToModelCurveNode.SetTubeRadius(1.0)
    self.MarkupsToModelCurveNode.SetTubeNumberOfSides(8)
    self.MarkupsToModelCurveNode.SetTubeSamplingFrequency(5)
    self.MarkupsToModelCurveNode.SetCleanMarkups(True)
    self.MarkupsToModelCurveNode.SetInterpolationType(self.MarkupsToModelCurveNode.Polynomial)
    self.MarkupsToModelCurveNode.SetPointParameterType(self.MarkupsToModelCurveNode.MinimumSpanningTree)
    self.MarkupsToModelCurveNode.SetPolynomialOrder(9)
    self.MarkupsToModelCurveNode.SetAutoUpdateOutput(False)
    self.MarkupsToModelCurveNode.SetName('MarkupsToModel_CatheterPaths')
    slicer.mrmlScene.AddNode(self.MarkupsToModelCurveNode)
    
    self.MarkupsToModelLogic = slicer.modules.markupstomodel.logic()
    
    self.reconstructionCameraButton.connect('clicked()', self.onReconstructionCameraButtonClicked)
    self.reconstructionCollectPointsButton.connect('clicked()', self.onReconstructionCollectPointsButtonClicked)
    self.reconstructionDeleteLastButton.connect('clicked()', self.onReconstructionDeleteLastButtonClicked)
    

  def disconnect(self):
    logging.debug('CathNav.disconnect()')
    Guidelet.disconnect(self)
      
    # Remove observer to old parameter node
    if self.tumorMarkups_Needle and self.tumorMarkups_NeedleObserver:
      self.tumorMarkups_Needle.RemoveObserver(self.tumorMarkups_NeedleObserver)
      self.tumorMarkups_NeedleObserver = None

    if self.chestwallMarkups_Chest and self.chestwallMarkups_ChestObserver:
      self.chestwallMarkups_Chest.RemoveObserver(self.chestwallMarkups_ChestObserver)
      self.chestwallMarkups_ChestObserver = None

    self.calibrationCollapsibleButton.disconnect('toggled(bool)', self.onCalibrationPanelToggled)
    self.navigationCollapsibleButton.disconnect('toggled(bool)', self.onNavigationPanelToggled)

    # calibration panel
    self.calibrationGuideButton.disconnect('clicked()', self.onCalibrationGuideClicked)
    self.calibrationNeedleButton.disconnect('clicked()', self.onCalibrationNeedleClicked)

    self.calibrationSamplingTimer.disconnect('timeout()',self.onCalibrationSamplingTimeout)
    
    # ultrasound panel
    self.tumorMarkupsDeleteLastButton.disconnect('clicked()', self.onTumorMarkupsDeleteLastClicked)
    self.tumorMarkupsDeleteAllButton.disconnect('clicked()', self.onTumorMarkupsDeleteAllClicked)
    self.tumorMarkupsPlaceButton.disconnect('clicked(bool)', self.onTumorMarkupsPlaceClicked)

    self.chestwallMarkupsPlaceButton.disconnect('clicked(bool)', self.onChestwallMarkupsPlaceClicked)
    self.chestwallMarkupsDeleteLastButton.disconnect('clicked()', self.onChestwallMarkupsDeleteLastClicked)
    self.chestwallMarkupsDeleteAllButton.disconnect('clicked()', self.onChestwallMarkupsDeleteAllClicked)

    # guidewire panel
    self.guidewireCameraZoomButtonIncrease.disconnect('clicked()', self.cameraZoomIncrease)
    self.guidewireCameraZoomButtonDecrease.disconnect('clicked()', self.cameraZoomDecrease)
    self.guidewireCameraTranslationXIncreaseButton.disconnect('clicked()', self.cameraTranslationXIncrease)
    self.guidewireCameraTranslationXDecreaseButton.disconnect('clicked()', self.cameraTranslationXDecrease)
    self.guidewireCameraTranslationYIncreaseButton.disconnect('clicked()', self.cameraTranslationYIncrease)
    self.guidewireCameraTranslationYDecreaseButton.disconnect('clicked()', self.cameraTranslationYDecrease)
    self.guidewireCameraTranslationZIncreaseButton.disconnect('clicked()', self.cameraTranslationZIncrease)
    self.guidewireCameraTranslationZDecreaseButton.disconnect('clicked()', self.cameraTranslationZDecrease)
    self.guidewireCameraButton.disconnect('clicked()', self.onGuidewireCameraButtonClicked)
    
    # planning panel
    self.planningCreateGridButton.disconnect('clicked()', self.onCreatePlanButtonClicked)
    self.gridRotationSlider.disconnect('valueChanged(double)', self.rotateGrid)
    
    # navigation panel
    self.navigationCameraZoomButtonIncrease.disconnect('clicked()', self.cameraZoomIncrease)
    self.navigationCameraZoomButtonDecrease.disconnect('clicked()', self.cameraZoomDecrease)
    self.navigationCameraTranslationXIncreaseButton.disconnect('clicked()', self.cameraTranslationXIncrease)
    self.navigationCameraTranslationXDecreaseButton.disconnect('clicked()', self.cameraTranslationXDecrease)
    self.navigationCameraTranslationYIncreaseButton.disconnect('clicked()', self.cameraTranslationYIncrease)
    self.navigationCameraTranslationYDecreaseButton.disconnect('clicked()', self.cameraTranslationYDecrease)
    self.navigationCameraTranslationZIncreaseButton.disconnect('clicked()', self.cameraTranslationZIncrease)
    self.navigationCameraTranslationZDecreaseButton.disconnect('clicked()', self.cameraTranslationZDecrease)
    self.navigationCameraButton.disconnect('clicked()', self.onNavigationCameraButtonClicked)
    
    # reconstruction panel
    self.reconstructionCameraButton.disconnect('clicked()', self.onReconstructionCameraButtonClicked)
    self.reconstructionCollectPointsButton.disconnect('clicked()', self.onReconstructionCollectPointsButtonClicked)
    self.reconstructionDeleteLastButton.disconnect('clicked()', self.onReconstructionDeleteLastButtonClicked)

  def onCalibrationPanelToggled(self, toggled):
    if toggled == False:
      return
    logging.debug('onCalibrationPanelToggled')
    self.onPanelToggledCommonTasks()
    self.selectView(self.VIEW_ULTRASOUND_3D) 

  def onUltrasoundPanelToggled(self, toggled):
    Guidelet.onUltrasoundPanelToggled(self, toggled)
    self.onPanelToggledCommonTasks()
    # The user may want to freeze the image (disconnect) to make contouring easier.
    # Disable automatic ultrasound image auto-fit when the user unfreezes (connect)
    # to avoid zooming out of the image.
    self.fitUltrasoundImageToViewOnConnect = not toggled

  def onCommon3DPanelToggled(self, toggled):
    if toggled == False:
      return
    logging.debug('onCommon3DPanelToggled')
    self.onPanelToggledCommonTasks()
    self.selectView(self.VIEW_3D)
    
  def onPanelToggledCommonTasks(self):
    self.resetSharedPanelStates()
  
  def resetSharedPanelStates(self):
    logging.debug('resetSharedPanelStates')
    self.setEnableGuidewireCameraControls(False)
    self.setEnableNavigationCameraControls(False)
    self.disableViewpoint()
    self.cameraTranslationXMm = self.cameraTranslationXDefaultMm
    self.cameraTranslationYMm = self.cameraTranslationYDefaultMm
    self.cameraTranslationZMm = self.cameraTranslationZDefaultMm
    self.cameraZoomScaleLogarithmic = self.cameraZoomScaleDefaultLogarithmic

  # ========== CALIBRATION PANEL FUNCTIONS ===========

  def onCalibrationNeedleClicked(self):
    logging.debug('onCalibrationNeedleClicked')
    self.startPivotCalibration('NeedleTipToNeedle', self.needleToGuide, self.needleTipToNeedle)
    
  def onCalibrationGuideClicked(self):
    logging.debug('onCalibrationGuideClicked')
    self.startFixedPointCalibration('GuideTipToGuide', self.needleTipToNeedle, self.guideToChest, self.needleTipMarkups_Guide, self.guideTipToGuide)
    
  def startPivotCalibration(self, toolToReferenceTransformName, toolToReferenceTransformNode, toolTipToToolTransformNode):
    logging.debug('startPivotCalibration')
    self.calibrationNeedleButton.setEnabled(False)
    self.calibrationGuideButton.setEnabled(False)
    self.pivotCalibrationResultTargetNode =  toolTipToToolTransformNode
    self.pivotCalibrationResultTargetName = toolToReferenceTransformName
    self.pivotCalibrationLogic.SetAndObserveTransformNode( toolToReferenceTransformNode );
    self.calibrationStopTime=time.time()+float(self.parameterNode.GetParameter('PivotCalibrationDurationSec'))
    self.pivotCalibrationLogic.SetRecordingState(True)
    self.onCalibrationSamplingTimeout()
    self.currentCalibration = self.currentCalibration_PIVOT
    
  def startFixedPointCalibration(self, toolPointToToolSensorTransformName, pointerTipTransformNode, toolSensorTransformNode, pointerTipMarkups_toolSensorNode, toolPointToToolSensorTransformNode):
    logging.debug('startFixedPointCalibration')
    self.calibrationNeedleButton.setEnabled(False)
    self.calibrationGuideButton.setEnabled(False)
    pointerTipMarkups_toolSensorNode.RemoveAllMarkups()
    self.collectFiducialsSupplementLogic.setMinimumAddDistanceMm(0)
    self.collectFiducialsSupplementLogic.setTransformSourceNode(pointerTipTransformNode)
    self.collectFiducialsSupplementLogic.setTransformTargetNode(toolSensorTransformNode)
    self.collectFiducialsSupplementLogic.setMarkupsFiducialNode(pointerTipMarkups_toolSensorNode)
    self.collectFiducialsSupplementLogic.setAllowPointRemovalsFalse()
    self.collectFiducialsSupplementLogic.setForceConstantPointDistanceFalse()
    self.collectFiducialsSupplementLogic.startCollection()
    self.calibrationStopTime=time.time()+float(self.parameterNode.GetParameter('FixedPointCalibrationDurationSec'))
    self.currentCalibration = self.currentCalibration_FIXED_POINT
    self.fixedPointCalibrationMarkups = pointerTipMarkups_toolSensorNode
    self.fixedPointCalibrationTargetTransformNode = toolPointToToolSensorTransformNode
    self.fixedPointCalibrationTargetTransformName = toolPointToToolSensorTransformName
    self.onCalibrationSamplingTimeout()
    
  def onCalibrationSamplingTimeout(self):
    self.countdownLabel.setText("Calibrating for {0:.0f} more seconds".format(self.calibrationStopTime-time.time())) 
    if(time.time()<self.calibrationStopTime):
      # continue
      self.calibrationSamplingTimer.start()
    else:
      # calibration completed
      if (self.currentCalibration == self.currentCalibration_FIXED_POINT):
        self.onStopFixedPointCalibration()
      elif (self.currentCalibration == self.currentCalibration_PIVOT):
        self.onStopPivotCalibration()
      else: # should never happen
        logging.error("Unrecognized current calibration type. Valid types are pivot (0) and fixed point (1). No calibration performed")
        self.countdownLabel.setText("An internal error occurred. No calibration performed")        

  def onStopPivotCalibration(self):
    logging.debug('onStopPivotCalibration')
    self.pivotCalibrationLogic.SetRecordingState(False)
    self.calibrationNeedleButton.setEnabled(True)
    self.calibrationGuideButton.setEnabled(True)
    self.pivotCalibrationLogic.ComputePivotCalibration()
    if(self.pivotCalibrationLogic.GetPivotRMSE() >= float(self.parameterNode.GetParameter('PivotCalibrationErrorThresholdMm'))):
      self.countdownLabel.setText("Calibration failed, error = %f mm, please calibrate again!"  % self.pivotCalibrationLogic.GetPivotRMSE())
      self.pivotCalibrationLogic.ClearToolToReferenceMatrices()
      return
    tooltipToToolMatrix = vtk.vtkMatrix4x4()
    self.pivotCalibrationLogic.GetToolTipToToolMatrix(tooltipToToolMatrix)
    self.pivotCalibrationLogic.ClearToolToReferenceMatrices()
    self.pivotCalibrationResultTargetNode.SetMatrixTransformToParent(tooltipToToolMatrix)
    self.logic.writeTransformToSettings(self.pivotCalibrationResultTargetName, tooltipToToolMatrix, self.configurationName)
    self.countdownLabel.setText("Calibration completed, error = %f mm" % self.pivotCalibrationLogic.GetPivotRMSE())
    logging.debug("Pivot calibration completed. Tool: {0}. RMSE = {1} mm".format(self.pivotCalibrationResultTargetNode.GetName(), self.pivotCalibrationLogic.GetPivotRMSE()))
    
  def onStopFixedPointCalibration(self):
    logging.debug('onStopFixedPointCalibration')
    self.collectFiducialsSupplementLogic.stopCollection()
    self.calibrationNeedleButton.setEnabled(True)
    self.calibrationGuideButton.setEnabled(True)
    vectorToolPointToToolSensorMm = self.computeAverageOfMarkups(self.fixedPointCalibrationMarkups)
    rmseToolSensorToToolPointMm = self.computeRMSEOfPointToMarkups(vectorToolPointToToolSensorMm,self.fixedPointCalibrationMarkups)
    if (rmseToolSensorToToolPointMm >= float(self.parameterNode.GetParameter('FixedPointCalibrationErrorThresholdMm'))):
      self.countdownLabel.setText("Calibration failed, error = %f mm, please calibrate again!"  % rmseToolSensorToToolPointMm)
      return
    toolPointToToolSensorMatrix = vtk.vtkMatrix4x4()
    toolPointToToolSensorMatrix.SetElement( 0, 3, vectorToolPointToToolSensorMm[0] )
    toolPointToToolSensorMatrix.SetElement( 1, 3, vectorToolPointToToolSensorMm[1] )
    toolPointToToolSensorMatrix.SetElement( 2, 3, vectorToolPointToToolSensorMm[2] )
    self.logic.writeTransformToSettings(self.fixedPointCalibrationTargetTransformName, toolPointToToolSensorMatrix, self.configurationName)
    self.fixedPointCalibrationTargetTransformNode.SetMatrixTransformToParent(toolPointToToolSensorMatrix)
    self.countdownLabel.setText("Calibration completed, error = %f mm" % rmseToolSensorToToolPointMm)
    logging.debug("Fixed point calibration completed. Tool: {0}. RMSE = {1} mm".format(self.fixedPointCalibrationTargetTransformNode.GetName(), rmseToolSensorToToolPointMm))
    
  def computeAverageOfMarkups(self, markupsFiducialNode):
    logging.debug('computeAverageOfMarkups')
    numberOfMarkups = markupsFiducialNode.GetNumberOfFiducials()
    logging.debug(numberOfMarkups)
    if (numberOfMarkups == 0):
      logging.error("Number of markups for fixed point calibration is 0. Returning [0,0,0]")
      pointMm = [0.0,0.0,0.0]
      return pointMm
    currentIndex = 0
    sumOfPointsMm = [0.0,0.0,0.0]
    while currentIndex < numberOfMarkups:
      pointMm = [0.0,0.0,0.0]
      markupsFiducialNode.GetNthFiducialPosition(currentIndex,pointMm)
      sumOfPointsMm[0] = sumOfPointsMm[0] + pointMm[0]
      sumOfPointsMm[1] = sumOfPointsMm[1] + pointMm[1]
      sumOfPointsMm[2] = sumOfPointsMm[2] + pointMm[2]
      currentIndex = currentIndex + 1
    avgOfPointsMm = sumOfPointsMm
    avgOfPointsMm[0] = float(avgOfPointsMm[0]) / float(numberOfMarkups)
    avgOfPointsMm[1] = float(avgOfPointsMm[1]) / float(numberOfMarkups)
    avgOfPointsMm[2] = float(avgOfPointsMm[2]) / float(numberOfMarkups)
    return avgOfPointsMm
    
  def computeRMSEOfPointToMarkups(self, toolPointMm, markupsFiducialNode):
    logging.debug('computeRMSEOfPointToMarkups')
    numberOfMarkups = markupsFiducialNode.GetNumberOfFiducials()
    if (numberOfMarkups == 0):
      logging.error("Number of markups for fixed point calibration is 0. Returning 1000 mm error.")
      errorMm = 1000.0
      return errorMm;
    currentIndex = 0
    sumSqDifferencesMm = 0.0
    while currentIndex < numberOfMarkups:
      markupPointMm = [0.0,0.0,0.0]
      markupsFiducialNode.GetNthFiducialPosition(currentIndex,markupPointMm)
      sqDifferenceMm = (toolPointMm[0] - markupPointMm[0])**2 + (toolPointMm[1] - markupPointMm[1])**2 + (toolPointMm[2] - markupPointMm[2])**2
      sumSqDifferencesMm = sumSqDifferencesMm + sqDifferenceMm
      currentIndex = currentIndex + 1
    meanSqDifferenceMm = float(sumSqDifferencesMm) / float(numberOfMarkups)
    rootMeanSqDifferenceMm = meanSqDifferenceMm ** (0.5)
    return rootMeanSqDifferenceMm
    
  # ========== ULTRASOUND PANEL FUNCTIONS ===========

  def onTumorMarkupsPlaceClicked(self, pushed):
    logging.debug('onTumorMarkupsPlaceClicked')
    interactionNode = slicer.app.applicationLogic().GetInteractionNode()
    if pushed:
      # activate placement mode
      selectionNode = slicer.app.applicationLogic().GetSelectionNode()
      selectionNode.SetReferenceActivePlaceNodeClassName("vtkMRMLMarkupsFiducialNode")
      selectionNode.SetActivePlaceNodeID(self.tumorMarkups_Needle.GetID())
      interactionNode.SetPlaceModePersistence(1)
      interactionNode.SetCurrentInteractionMode(interactionNode.Place)
      self.chestwallMarkupsPlaceButton.setChecked(0)
    else:
      # deactivate placement mode
      interactionNode.SetCurrentInteractionMode(interactionNode.ViewTransform)

  def onTumorMarkupsDeleteLastClicked(self):
    logging.debug('onTumorMarkupsDeleteLastClicked')
    numberOfPoints = self.tumorMarkups_Needle.GetNumberOfFiducials()
    self.tumorMarkups_Needle.RemoveMarkup(numberOfPoints-1)
    if numberOfPoints<=1:
      self.tumorMarkupsDeleteLastButton.setEnabled(False)
      self.tumorMarkupsDeleteAllButton.setEnabled(False)

  def onTumorMarkupsDeleteAllClicked(self):
    logging.debug('onTumorMarkupsDeleteAllClicked')
    self.tumorMarkups_Needle.RemoveAllMarkups()
    self.tumorMarkupsDeleteLastButton.setEnabled(False)
    self.tumorMarkupsDeleteAllButton.setEnabled(False)

  def onChestwallMarkupsPlaceClicked(self, pushed):
    logging.debug('onChestwallMarkupsPlaceClicked')
    interactionNode = slicer.app.applicationLogic().GetInteractionNode()
    if pushed:
      # activate placement mode
      selectionNode = slicer.app.applicationLogic().GetSelectionNode()
      selectionNode.SetReferenceActivePlaceNodeClassName("vtkMRMLMarkupsFiducialNode")
      selectionNode.SetActivePlaceNodeID(self.chestwallMarkups_Chest.GetID())
      interactionNode.SetPlaceModePersistence(1)
      interactionNode.SetCurrentInteractionMode(interactionNode.Place)
      self.tumorMarkupsPlaceButton.setChecked(0)
    else:
      # deactivate placement mode
      interactionNode.SetCurrentInteractionMode(interactionNode.ViewTransform)

  def onChestwallMarkupsDeleteLastClicked(self):
    logging.debug('onChestwallMarkupsDeleteLastClicked')
    numberOfPoints = self.chestwallMarkups_Chest.GetNumberOfFiducials()
    self.chestwallMarkups_Chest.RemoveMarkup(numberOfPoints-1)
    if numberOfPoints<=1:
      self.chestwallMarkupsDeleteLastButton.setEnabled(False)
      self.chestwallMarkupsDeleteAllButton.setEnabled(False)

  def onChestwallMarkupsDeleteAllClicked(self):
    logging.debug('onChestwallMarkupsDeleteAllClicked')
    self.chestwallMarkups_Chest.RemoveAllMarkups()
    self.chestwallMarkupsDeleteLastButton.setEnabled(False)
    self.chestwallMarkupsDeleteAllButton.setEnabled(False)

  def setAndObserveNode(self, node, existingMarkupsObserver, method):
    logging.debug('setAndObserveNode')
    if not node:
      logging.error('No markups node provided. No observer set.')
      return None
    # Remove observer to old parameter node
    if existingMarkupsObserver:
      node.RemoveObserver(existingMarkupsObserver)
    # Set and observe new parameter node
    newMarkupsObserver = node.AddObserver(vtk.vtkCommand.ModifiedEvent, method)
    return newMarkupsObserver

  def onTumorMarkupsNodeModified(self, observer, eventid):
    logging.debug('onTumorMarkupsNodeModified')
    self.MarkupsToModelClosedSurfaceNode.SetAndObserveMarkupsNodeID(self.tumorMarkups_Needle.GetID())
    self.MarkupsToModelClosedSurfaceNode.SetAndObserveModelNodeID(self.tumorModel_Needle.GetID())
    self.MarkupsToModelLogic.UpdateOutputModel(self.MarkupsToModelClosedSurfaceNode)

  def onChestwallMarkupsNodeModified(self, observer, eventid):
    logging.debug('onChestwallMarkupsNodeModified')
    self.MarkupsToModelClosedSurfaceNode.SetAndObserveMarkupsNodeID(self.chestwallMarkups_Chest.GetID())
    self.MarkupsToModelClosedSurfaceNode.SetAndObserveModelNodeID(self.chestwallModel_Chest.GetID())
    self.MarkupsToModelLogic.UpdateOutputModel(self.MarkupsToModelClosedSurfaceNode)


  # ========== GUIDE WIRE PANEL FUNCTIONS ===========
  
  def recordGuidePosition(self):
    logging.debug('recordGuidePosition')
    matrixPlanToNeedle = vtk.vtkMatrix4x4()
    needleTransformNode = self.needleToChest
    gridTransformNode = self.guideCameraToGuideModel # we take a snapshot of the guide's position
    gridTransformNode.GetMatrixTransformToNode(needleTransformNode,matrixPlanToNeedle)
    self.planToNeedle.SetMatrixTransformToParent(matrixPlanToNeedle)
    # =========== PLANNING PANEL FUNCTIONS ============
    
  def gridSpacingHorizontalIncrease(self):
    logging.debug('gridSpacingHorizontalIncrease')
    gridSpacingHorizontalMaxMm = 20
    if self.gridSpacingHorizontalMm < gridSpacingHorizontalMaxMm:
      self.gridSpacingHorizontalMm = self.gridSpacingHorizontalMm + 1
  
  def gridSpacingHorizontalDecrease(self):
    logging.debug('gridSpacingHorizontalDecrease')
    gridSpacingHorizontalMinMm = 1
    if self.gridSpacingHorizontalMm > gridSpacingHorizontalMinMm:
      self.gridSpacingHorizontalMm = self.gridSpacingHorizontalMm - 1
  
  def gridSpacingVerticalIncrease(self):
    logging.debug('gridSpacingVerticalIncrease')
    gridSpacingVerticalMaxMm = 20
    if self.gridSpacingVerticalMm < gridSpacingVerticalMaxMm:
      self.gridSpacingVerticalMm = self.gridSpacingVerticalMm + 1
  
  def gridSpacingVerticalDecrease(self):
    logging.debug('gridSpacingVerticalDecrease')
    gridSpacingVerticalMinMm = 1
    if self.gridSpacingVerticalMm > gridSpacingVerticalMinMm:
      self.gridSpacingVerticalMm = self.gridSpacingVerticalMm - 1
    
  def gridSizeLeftIncrease(self):
    logging.debug('gridSizeLeftIncrease')
    gridSizeLeftMaxNumPoints = 10
    if self.gridSizeLeftNumPoints < gridSizeLeftMaxNumPoints:
      self.gridSizeLeftNumPoints = self.gridSizeLeftNumPoints + 1
    
  def gridSizeLeftDecrease(self):
    logging.debug('gridSizeLeftDecrease')
    gridSizeLeftMinNumPoints = 0
    if self.gridSizeLeftNumPoints > gridSizeLeftMinNumPoints:
      self.gridSizeLeftNumPoints = self.gridSizeLeftNumPoints - 1
    
  def gridSizeRightIncrease(self):
    logging.debug('gridSizeRightIncrease')
    gridSizeRightMaxNumPoints = 10
    if self.gridSizeRightNumPoints < gridSizeRightMaxNumPoints:
      self.gridSizeRightNumPoints = self.gridSizeRightNumPoints + 1
    
  def gridSizeRightDecrease(self):
    logging.debug('gridSizeRightDecrease')
    gridSizeRightMinNumPoints = 0
    if self.gridSizeRightNumPoints > gridSizeRightMinNumPoints:
      self.gridSizeRightNumPoints = self.gridSizeRightNumPoints - 1
    
  def gridSizeUpIncrease(self):
    logging.debug('gridSizeUpIncrease')
    gridSizeUpMaxNumPoints = 10
    if self.gridSizeUpNumPoints < gridSizeUpMaxNumPoints:
      self.gridSizeUpNumPoints = self.gridSizeUpNumPoints + 1
    
  def gridSizeUpDecrease(self):
    logging.debug('gridSizeUpDecrease')
    gridSizeUpMinNumPoints = 0
    if self.gridSizeUpNumPoints > gridSizeUpMinNumPoints:
      self.gridSizeUpNumPoints = self.gridSizeUpNumPoints - 1
    
  def gridSizeDownIncrease(self):
    logging.debug('gridSizeDownIncrease')
    gridSizeDownMaxNumPoints = 10
    if self.gridSizeDownNumPoints < gridSizeDownMaxNumPoints:
      self.gridSizeDownNumPoints = self.gridSizeDownNumPoints + 1
    
  def gridSizeDownDecrease(self):
    logging.debug('gridSizeDownDecrease')
    gridSizeDownMinNumPoints = 0
    if self.gridSizeDownNumPoints > gridSizeDownMinNumPoints:
      self.gridSizeDownNumPoints = self.gridSizeDownNumPoints - 1
       
  def onCreatePlanButtonClicked(self):
    logging.debug("onCreatePlanButtonClicked")
    self.recordGuidePosition() #TODO: Move this function elsewhere?
    # update grid parameters
    gridSizeLeftMm = self.gridSizeLeftNumPoints * self.gridSpacingHorizontalMm
    gridSizeRightMm = self.gridSizeRightNumPoints * self.gridSpacingHorizontalMm
    gridSizeUpMm = self.gridSizeUpNumPoints * self.gridSpacingVerticalMm
    gridSizeDownMm = self.gridSizeDownNumPoints * self.gridSpacingVerticalMm
    self.planningLogic.setGridPatternToTriangular()
    self.planningLogic.setGridSpacingHorizontalMm(self.gridSpacingHorizontalMm)
    self.planningLogic.setGridSpacingVerticalMm(self.gridSpacingVerticalMm)
    self.planningLogic.setGridSizeLeftMm(gridSizeLeftMm)
    self.planningLogic.setGridSizeRightMm(gridSizeRightMm)
    self.planningLogic.setGridSizeUpMm(gridSizeUpMm)
    self.planningLogic.setGridSizeDownMm(gridSizeDownMm)
    self.planningLogic.setTransformGridToTargetNode(self.gridToPlan)
    # update/create the grid
    self.planningLogic.createGrid()
    
  def rotateGrid(self, value):
    logging.debug('rotateGrid')
    transformGridToPlan = vtk.vtkTransform()
    transformGridToPlan.RotateZ(value)
    matrixGridToPlan = transformGridToPlan.GetMatrix()
    self.gridToPlan.SetMatrixTransformToParent(matrixGridToPlan)
 
  # ========== NAVIGATION PANEL FUNCTIONS ===========
  
  def cameraZoomIncrease(self):
    logging.debug('cameraZoomIncrease')
    self.cameraZoomScaleLogarithmic = self.cameraZoomScaleLogarithmic + self.cameraZoomScaleChangeMagnitudeLogarithmic
    if self.cameraZoomScaleLogarithmic > self.cameraZoomScaleMaxLogarithmic:
      self.cameraZoomScaleLogarithmic = self.cameraZoomScaleMaxLogarithmic
    self.updateViewpointCameraParameters()
    
  def cameraZoomDecrease(self):
    logging.debug('cameraZoomDecrease')
    self.cameraZoomScaleLogarithmic = self.cameraZoomScaleLogarithmic - self.cameraZoomScaleChangeMagnitudeLogarithmic
    if self.cameraZoomScaleLogarithmic < self.cameraZoomScaleMinLogarithmic:
      self.cameraZoomScaleLogarithmic = self.cameraZoomScaleMinLogarithmic
    self.updateViewpointCameraParameters()
      
  def cameraTranslationXIncrease(self):
    logging.debug('cameraTranslationXIncrease')
    self.cameraTranslationXMm = self.cameraTranslationXMm + self.cameraTranslationChangeMagnitudeMm
    if self.cameraTranslationXMm > self.cameraTranslationXMaxMm:
      self.cameraTranslationXMm = self.cameraTranslationXMaxMm
    self.updateViewpointCameraParameters()

  def cameraTranslationXDecrease(self):
    logging.debug('cameraTranslationXDecrease')
    self.cameraTranslationXMm = self.cameraTranslationXMm - self.cameraTranslationChangeMagnitudeMm
    if self.cameraTranslationXMm < self.cameraTranslationXMinMm:
      self.cameraTranslationXMm = self.cameraTranslationXMinMm
    self.updateViewpointCameraParameters()
      
  def cameraTranslationYIncrease(self):
    logging.debug('cameraTranslationYIncrease')
    self.cameraTranslationYMm = self.cameraTranslationYMm + self.cameraTranslationChangeMagnitudeMm
    if self.cameraTranslationYMm > self.cameraTranslationYMaxMm:
      self.cameraTranslationYMm = self.cameraTranslationYMaxMm
    self.updateViewpointCameraParameters()

  def cameraTranslationYDecrease(self):
    logging.debug('cameraTranslationYDecrease')
    self.cameraTranslationYMm = self.cameraTranslationYMm - self.cameraTranslationChangeMagnitudeMm
    if self.cameraTranslationYMm < self.cameraTranslationYMinMm:
      self.cameraTranslationYMm = self.cameraTranslationYMinMm
    self.updateViewpointCameraParameters()
      
  def cameraTranslationZIncrease(self):
    logging.debug('cameraTranslationZIncrease')
    self.cameraTranslationZMm = self.cameraTranslationZMm + self.cameraTranslationChangeMagnitudeMm
    if self.cameraTranslationZMm > self.cameraTranslationZMaxMm:
      self.cameraTranslationZMm = self.cameraTranslationZMaxMm
    self.updateViewpointCameraParameters()

  def cameraTranslationZDecrease(self):
    logging.debug('cameraTranslationZDecrease')
    self.cameraTranslationZMm = self.cameraTranslationZMm - self.cameraTranslationChangeMagnitudeMm
    if self.cameraTranslationZMm < self.cameraTranslationZMinMm:
      self.cameraTranslationZMm = self.cameraTranslationZMinMm
    self.updateViewpointCameraParameters()

  def setEnableGuidewireCameraControls(self, enable):
    logging.debug('setEnableGuidewireCameraControls')
    self.guidewireCameraZoomButtonIncrease.setEnabled(enable)
    self.guidewireCameraZoomButtonDecrease.setEnabled(enable)
    self.guidewireCameraTranslationXIncreaseButton.setEnabled(enable)
    self.guidewireCameraTranslationXDecreaseButton.setEnabled(enable)
    self.guidewireCameraTranslationYIncreaseButton.setEnabled(enable)
    self.guidewireCameraTranslationYDecreaseButton.setEnabled(enable)
    self.guidewireCameraTranslationZIncreaseButton.setEnabled(enable)
    self.guidewireCameraTranslationZDecreaseButton.setEnabled(enable)

  def setEnableNavigationCameraControls(self, enable):
    logging.debug('setEnableNavigationCameraControls')
    self.navigationCameraZoomButtonIncrease.setEnabled(enable)
    self.navigationCameraZoomButtonDecrease.setEnabled(enable)
    self.navigationCameraTranslationXIncreaseButton.setEnabled(enable)
    self.navigationCameraTranslationXDecreaseButton.setEnabled(enable)
    self.navigationCameraTranslationYIncreaseButton.setEnabled(enable)
    self.navigationCameraTranslationYDecreaseButton.setEnabled(enable)
    self.navigationCameraTranslationZIncreaseButton.setEnabled(enable)
    self.navigationCameraTranslationZDecreaseButton.setEnabled(enable)

  def onGuidewireCameraButtonClicked(self):
    logging.debug("onGuidewireCameraButtonClicked {0}".format(self.guidewireCameraButton.isChecked()))
    if (self.guidewireCameraButton.isChecked() == True):
      self.setEnableGuidewireCameraControls(True)
      self.enableViewpoint(self.guideCameraToGuideModel)
    else:
      self.setEnableGuidewireCameraControls(False)
      self.disableViewpoint()
  
  def onNavigationCameraButtonClicked(self):
    logging.debug("onNavigationCameraButtonClicked {0}".format(self.navigationCameraButton.isChecked()))
    if (self.navigationCameraButton.isChecked() == True):
      self.setEnableNavigationCameraControls(True)
      self.enableViewpoint(self.gridCameraToGrid)
    else:
      self.setEnableNavigationCameraControls(False)
      self.disableViewpoint()
      
  def updateViewpointCameraParameters(self):
    logging.debug('updateViewpointCameraParameters')
    viewNode = self.getViewNode('View1')
    viewpointInstance = self.viewpointLogic.getViewpointForViewNode(viewNode)
    viewpointInstance.bullseyeSetCameraXPosMm(self.cameraTranslationXMm)
    viewpointInstance.bullseyeSetCameraYPosMm(self.cameraTranslationYMm)
    viewpointInstance.bullseyeSetCameraZPosMm(self.cameraTranslationZMm)
    cameraZoomScaleAbsolute = 10 ** self.cameraZoomScaleLogarithmic
    viewpointInstance.bullseyeSetCameraParallelScale(cameraZoomScaleAbsolute)
    
  def enableViewpoint(self, cameraToTargetNode):
    logging.debug('enableViewpoint')
    viewNode = self.getViewNode('View1')
    viewpointInstance = self.viewpointLogic.getViewpointForViewNode(viewNode)
    viewpointInstance.setViewNode(viewNode)
    viewpointInstance.bullseyeSetTransformNode(cameraToTargetNode)
    viewpointInstance.bullseyeSetCameraParallelProjection(True)
    viewpointInstance.bullseyeStart()
    self.updateViewpointCameraParameters()
    
  def disableViewpoint(self):
    logging.debug('disableViewpoint')
    viewNode = self.getViewNode('View1')
    viewpointInstance = self.viewpointLogic.getViewpointForViewNode(viewNode)
    if (viewpointInstance.isCurrentModeBullseye()):
      viewpointInstance.bullseyeStop()

  def getViewNode(self, viewName):
    """
    Get the view node for the selected 3D view
    """
    logging.debug("getViewNode")
    viewNode = slicer.util.getNode(viewName)
    return viewNode
    
  # ========== RECONSTRUCTION PANEL FUNCTIONS ===========
  
  def onReconstructionCameraButtonClicked(self):
    pass
  
  def startPointCollection(self):
    logging.debug('startPointCollection')
    self.collectFiducialsSupplementLogic.setMinimumAddDistanceMm(1) # collect points every 0.1 mm
    self.collectFiducialsSupplementLogic.setTransformSourceNode(self.wireToChest)
    self.collectFiducialsSupplementLogic.setTransformTargetNode(self.needleToChest)
    self.collectFiducialsSupplementLogic.setMarkupsFiducialNode(self.wirePoints_Needle)
    self.collectFiducialsSupplementLogic.setAllowPointRemovalsTrue()
    self.collectFiducialsSupplementLogic.setForceConstantPointDistanceFalse()
    self.collectFiducialsSupplementLogic.startCollection()
    self.wirePoints_Needle.RemoveAllMarkups()
    self.wirePoints_NeedleObserver = self.setAndObserveNode(self.wirePoints_Needle, self.wirePoints_NeedleObserver, self.onWireMarkupsNodeModified)
    self.pathCount = self.pathCount + 1
    logging.debug('startPointCollection end')
    
  def stopPointCollection(self):
    # Stop collection
    self.collectFiducialsSupplementLogic.stopCollection()
    if self.wirePoints_Needle and self.wirePoints_NeedleObserver:
      self.wirePoints_Needle.RemoveObserver(self.wirePoints_NeedleObserver)
      self.wirePoints_NeedleObserver = None
    
    # Create a copy of the list for data storage purposes
    if self.reconstructionThread:
      while self.reconstructionThread.isAlive():
        pass # wait until the thread terminates? TODO: Ask Andras if there is a safer way
    # Do one final reconstruction
    markupsNode = self.wirePoints_Needle
    self.MarkupsToModelCurveNode.SetAndObserveMarkupsNodeID(markupsNode.GetID())
    modelNode = self.getCatheterModelForPathNumber(self.pathCount)
    self.MarkupsToModelCurveNode.SetAndObserveModelNodeID(modelNode.GetID())
    self.MarkupsToModelLogic.UpdateOutputModel(self.MarkupsToModelCurveNode)
    
    # create a copy of the markups for analysis purposes
    storeRawFiducialsListName = 'WirePoints_Needle_RawPath' + str(self.pathCount)
    storeRawFiducialsList = self.initializeFiducialList(storeRawFiducialsListName)
    self.copyFiducialsFromListToList(self.wirePoints_Needle,storeRawFiducialsList)
    self.wirePoints_Needle.RemoveAllMarkups()
    self.pathCount = self.pathCount + 1
  
  def onWireMarkupsNodeModified(self, observer, eventid):
    if self.reconstructionThread:
      if self.reconstructionThread.isAlive():
        return
    markupsNode = self.wirePoints_Needle
    if markupsNode.GetNumberOfFiducials() <= 10:
      return
    self.MarkupsToModelCurveNode.SetAndObserveMarkupsNodeID(markupsNode.GetID())
    modelNode = self.getCatheterModelForPathNumber(self.pathCount)
    self.MarkupsToModelCurveNode.SetAndObserveModelNodeID(modelNode.GetID())
    self.reconstructionThread = ReconstructionThread(self.MarkupsToModelCurveNode)
    self.reconstructionThread.start()
    logging.debug('onWireMarkupsNodeModified - end')
    
  def getCatheterModelForPathNumber(self, pathNumber):
    nodeName = self.getCatheterModelNameForPathNumber(pathNumber)
    modelNode = slicer.util.getNode(nodeName)
    if not modelNode:
      modelNode = slicer.vtkMRMLModelNode()
      modelNode.SetName(nodeName)
      slicer.mrmlScene.AddNode(modelNode)
      # Add display node
      displayNode = slicer.vtkMRMLModelDisplayNode()
      displayNode.SetColor(0,1,0) # Green
      displayNode.BackfaceCullingOff()
      displayNode.SliceIntersectionVisibilityOn()
      displayNode.SetSliceIntersectionThickness(2)
      displayNode.SetOpacity(0.3) # Between 0-1, 1 being opaque
      slicer.mrmlScene.AddNode(displayNode)
      modelNode.SetAndObserveDisplayNodeID(displayNode.GetID())
    return modelNode
  
  def getCatheterModelNameForPathNumber(self, pathNumber):
    return ('Catheter' + str(pathNumber))

  def onReconstructionCollectPointsButtonClicked(self):
    logging.debug('onReconstructionCollectPointsButtonClicked')
    if (self.reconstructionCollectPointsButton.checked):
      self.startPointCollection()
    else:
      self.stopPointCollection()
  
  def onReconstructionDeleteLastButtonClicked(self):
    logging.debug('onReconstructionDeleteLastButtonClicked')
    
class ReconstructionThread (threading.Thread):
  def __init__(self, markupsToModelNode):
    threading.Thread.__init__(self)
    self.markupsToModelNode = markupsToModelNode
    self.MarkupsToModelLogic = slicer.modules.markupstomodel.logic()
    
  def run(self):
    logging.debug("ReconstructionThread.run()")
    self.MarkupsToModelLogic.UpdateOutputModel(self.markupsToModelNode)
  