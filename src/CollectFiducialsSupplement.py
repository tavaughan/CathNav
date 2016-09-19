from __main__ import vtk, qt, ctk, slicer
from slicer.ScriptedLoadableModule import *
import logging

#
# CollectFiducialsSupplement
#

class CollectFiducialsSupplement(ScriptedLoadableModule):
  def __init__(self, parent):
    parent.title = "CollectFiducialsSupplement"
    parent.categories = ["IGT"]
    parent.dependencies = []
    parent.contributors = ["Thomas Vaughan (Queen's)", "Gabor Fichtinger (Queen's)"]
    parent.helpText = """
    Collect fiducials at the origin of an observed transform automatically after some amount of movement.
    """
    parent.acknowledgementText = """
	This work is funded as a project in the Laboratory for Percutaneous Surgery, Queen's University, Kingston, Ontario. Thomas Vaughan is funded by an NSERC Postgraduate award. Gabor Fichtinger is funded as a Cancer Care Ontario (CCO) Chair.
	""" # replace with organization, grant and thanks.
    self.parent = parent

#
# CollectFiducialsSupplementWidget
#

class CollectFiducialsSupplementWidget(ScriptedLoadableModuleWidget):

  def setup(self):
    ScriptedLoadableModuleWidget.setup(self)
    # TODO: The following lines are strictly for debug purposes, should be removed when this module is done
    self.developerMode = True
    slicer.tmwidget = self
    
    self.logic = CollectFiducialsSupplementLogic()
    
    # private widget-specific things
    self.enableButtonState = 0;

    # Collapsible buttons
    self.parametersCollapsibleButton = ctk.ctkCollapsibleButton()
    self.parametersCollapsibleButton.text = "CollectFiducialsSupplement"
    self.layout.addWidget(self.parametersCollapsibleButton)

    # Layout within the collapsible button
    self.parametersFormLayout = qt.QFormLayout(self.parametersCollapsibleButton)
    
    # Transform Tool Tip To Reference combobox
    self.transformNodeSourceLabel = qt.QLabel()
    self.transformNodeSourceLabel.setText("Source transform node: ")
    self.transformNodeSourceSelector = slicer.qMRMLNodeComboBox()
    self.transformNodeSourceSelector.nodeTypes = ( ("vtkMRMLLinearTransformNode"), "" )
    self.transformNodeSourceSelector.noneEnabled = False
    self.transformNodeSourceSelector.addEnabled = False
    self.transformNodeSourceSelector.removeEnabled = False
    self.transformNodeSourceSelector.setMRMLScene( slicer.mrmlScene )
    self.transformNodeSourceSelector.setToolTip("Pick the transform for going from the tool's tip to the target coordinate system")
    self.parametersFormLayout.addRow(self.transformNodeSourceLabel, self.transformNodeSourceSelector)
    
    # Transform Target to Reference combobox
    self.transformNodeTargetLabel = qt.QLabel()
    self.transformNodeTargetLabel.setText("Target transform node: ")
    self.transformNodeTargetSelector = slicer.qMRMLNodeComboBox()
    self.transformNodeTargetSelector.nodeTypes = ( ("vtkMRMLLinearTransformNode"), "" )
    self.transformNodeTargetSelector.noneEnabled = False
    self.transformNodeTargetSelector.addEnabled = False
    self.transformNodeTargetSelector.removeEnabled = False
    self.transformNodeTargetSelector.setMRMLScene( slicer.mrmlScene )
    self.transformNodeTargetSelector.setToolTip("Pick the transform for going from the tool's tip to the target coordinate system")
    self.parametersFormLayout.addRow(self.transformNodeTargetLabel, self.transformNodeTargetSelector)
    
    # Point List combobox
    self.pointListLabel = qt.QLabel()
    self.pointListLabel.setText("Point list: ")
    self.pointListSelector = slicer.qMRMLNodeComboBox()
    self.pointListSelector.nodeTypes = ( ("vtkMRMLMarkupsFiducialNode"), "" )
    self.pointListSelector.noneEnabled = False
    self.pointListSelector.addEnabled = True
    self.pointListSelector.removeEnabled = False
    self.pointListSelector.setMRMLScene( slicer.mrmlScene )
    self.pointListSelector.setToolTip("Pick which fiducial list to store collected points in")
    self.parametersFormLayout.addRow(self.pointListLabel, self.pointListSelector)
    
    # Allow point removals
    self.allowPointRemovalsLabel = qt.QLabel()
    self.allowPointRemovalsLabel.setText("Allow point removals: ")
    self.allowPointRemovalsCheckbox = qt.QCheckBox()
    self.parametersFormLayout.addRow(self.allowPointRemovalsLabel, self.allowPointRemovalsCheckbox)
    
    # Force constant distance
    self.forceConstantPointDistanceLabel = qt.QLabel()
    self.forceConstantPointDistanceLabel.setText("Force constant point distance: ")
    self.forceConstantPointDistanceCheckbox = qt.QCheckBox()
    self.parametersFormLayout.addRow(self.forceConstantPointDistanceLabel, self.forceConstantPointDistanceCheckbox)
    
    # Point add distance
    minimumAddDistanceSliderMinMm        = 0
    minimumAddDistanceSliderMaxMm        = 50
    minimumAddDistanceSliderDefaultMm    = 10
    self.minimumAddDistanceLabel = qt.QLabel(qt.Qt.Horizontal,None)
    self.minimumAddDistanceLabel.text = "Minimum point add distance: "
    self.minimumAddDistanceSlider = slicer.qMRMLSliderWidget()
    self.minimumAddDistanceSlider.minimum = minimumAddDistanceSliderMinMm
    self.minimumAddDistanceSlider.maximum = minimumAddDistanceSliderMaxMm
    self.minimumAddDistanceSlider.value = minimumAddDistanceSliderDefaultMm
    self.parametersFormLayout.addRow(self.minimumAddDistanceLabel,self.minimumAddDistanceSlider)
    
    self.enableButton = qt.QPushButton()
    self.enableButton.text = "Enable Automatic Fiducial Collection"
    self.enableButton.setToolTip("Start the automatic collection of fiducials based on the settings")
    self.parametersFormLayout.addRow(self.enableButton)
    
    self.removeAllPointsButton = qt.QPushButton()
    self.removeAllPointsButton.text = "Remove All Points"
    self.removeAllPointsButton.setToolTip("Make the current fiducial list empty. This will delete all data in that list.")
    self.parametersFormLayout.addRow(self.removeAllPointsButton)

    # Add vertical spacer
    self.layout.addStretch(1)
    
    #Connections
    self.enableButton.connect('clicked()', self.enableButtonPressed)
    self.removeAllPointsButton.connect('clicked()', self.logic.removeAllPoints)
    self.minimumAddDistanceSlider.connect('valueChanged(double)', self.logic.setMinimumAddDistanceMm)
    self.allowPointRemovalsCheckbox.connect('clicked()', self.allowPointRemovalsCheckboxClicked)
    self.forceConstantPointDistanceCheckbox.connect('clicked()', self.forceConstantPointDistanceCheckboxClicked)
    
    # Add vertical spacer
    self.layout.addStretch(1)
  
  def allowPointRemovalsCheckboxClicked(self):
    logging.debug('allowPointRemovalCheckboxClicked')
    if (self.allowPointRemovalsCheckbox.isChecked()):
      self.logic.setAllowPointRemovalsTrue()
    else:
      self.logic.setAllowPointRemovalsFalse()
    
  def forceConstantPointDistanceCheckboxClicked(self):
    logging.debug('forceConstantPointDistanceClicked')
    if (self.forceConstantPointDistanceCheckbox.isChecked()):
      self.logic.setForceConstantPointDistanceTrue()
    else:
      self.logic.setForceConstantPointDistanceFalse()

  def enableButtonPressed(self):
    logging.debug('enableButtonPressed')
    if (self.enableButtonState == 0):
      self.logic.setTransformSourceNode(self.transformNodeSourceSelector.currentNode())
      self.logic.setTransformTargetNode(self.transformNodeTargetSelector.currentNode())
      self.logic.setMarkupsFiducialNode(self.pointListSelector.currentNode())
      self.logic.setMinimumAddDistanceMm(self.minimumAddDistanceSlider.value)
      self.logic.startCollection()
      self.transformNodeSourceSelector.enabled = False
      self.transformNodeTargetSelector.enabled = False
      self.pointListSelector.enabled = False
      self.enableButton.text = "Disable Automatic Fiducial Collection"
      self.enableButtonState = 1
    else:
      self.logic.stopCollection()
      self.transformNodeSourceSelector.enabled = True
      self.transformNodeTargetSelector.enabled = True
      self.pointListSelector.enabled = True
      self.enableButton.text = "Enable Automatic Fiducial Collection"
      self.enableButtonState = 0
#
# CollectFiducialsSupplementLogic
#

class CollectFiducialsSupplementLogic(ScriptedLoadableModuleLogic):
  def __init__(self):
    self.transformSourceNode = None
    self.transformTargetNode = None
    self.markupsFiducialNode = None
    self.minimumAddDistanceMm = 5;
    self.currentlyCollecting = False
    self.allowPointRemovals = False
    self.forceConstantPointDistance = False
    self.currentPositionMm = [0,0,0]
    self.currentDistanceFromPointNMinus2Mm = 0 # Relative to second last point, N refers to the size of the markups list
    self.currentDistanceFromPointNMinus3Mm = 0 # Relative to third last point
    self.transformNodeObserverTags = []

  def addObservers(self): # mostly copied from PositionErrorMapping.py in PLUS
    logging.debug('addObservers')
    transformModifiedEvent = 15000
    transformSourceNode = self.transformSourceNode
    while transformSourceNode:
      print "Add observer to {0}".format(transformSourceNode.GetName())
      self.transformNodeObserverTags.append([transformSourceNode, transformSourceNode.AddObserver(transformModifiedEvent, self.onTransformModified)])
      transformSourceNode = transformSourceNode.GetParentTransformNode()
    transformTargetNode = self.transformTargetNode
    while transformTargetNode:
      print "Add observer to {0}".format(transformTargetNode.GetName())
      self.transformNodeObserverTags.append([transformTargetNode, transformTargetNode.AddObserver(transformModifiedEvent, self.onTransformModified)])
      transformTargetNode = transformTargetNode.GetParentTransformNode()
      # TODO: What should it do if a transform node already exists in the list?
    print "Done adding observers"

  def removeObservers(self):
    print "Removing observers..."
    for nodeTagPair in self.transformNodeObserverTags:
      nodeTagPair[0].RemoveObserver(nodeTagPair[1])
    print "Done removing observers"

  def setMinimumAddDistanceMm(self,newValueMm):
    logging.debug('setMinimumAddDistanceMm')
    self.minimumAddDistanceMm = newValueMm
    
  def setTransformSourceNode(self,node):
    logging.debug('setTransformSourceNode')
    self.transformSourceNode = node
    
  def setTransformTargetNode(self,node):
    logging.debug('setTransformSourceNode')
    self.transformTargetNode = node
    
  def setMarkupsFiducialNode(self,node):
    logging.debug('setTransformSourceNode')
    self.markupsFiducialNode = node
    
  def setAllowPointRemovalsTrue(self):
    logging.debug('setAllowPointRemovalsTrue')
    self.allowPointRemovals = True
    
  def setAllowPointRemovalsFalse(self):
    logging.debug('setAllowPointRemovalsFalse')
    self.allowPointRemovals = False
    
  def setForceConstantPointDistanceTrue(self):
    logging.debug('setForceConstantPointDistanceTrue')
    self.forceConstantPointDistance = True
    
  def setForceConstantPointDistanceFalse(self):
    logging.debug('setForceConstantPointDistanceFalse')
    self.forceConstantPointDistance = False
    
  def startCollection(self):
    logging.debug('startCollection')
    if (self.transformSourceNode and self.transformSourceNode and self.markupsFiducialNode):
      self.currentlyCollecting = True
      self.addObservers()
    else:
      print "A node is missing. Nothing will happen until the comboboxes have items selected."
    
  def stopCollection(self):
    logging.debug('stopCollection')
    self.currentlyCollecting = False
    self.removeObservers();

  def onTransformModified(self, observer, eventid):
    # no logging here - it slows Slicer down a *lot*
    self.updateCurrentPosition()
    if (self.addPointConditions() == True):
      self.addPoint()
    elif (self.removePointConditions() == True):
      self.removePoint()
    self.moveLastPoint()
    
  def updateCurrentPosition(self):
    matrixSourceToTarget = vtk.vtkMatrix4x4()
    self.transformSourceNode.GetMatrixTransformToNode(self.transformTargetNode,matrixSourceToTarget)
    transformSourceToTarget = vtk.vtkTransform()
    transformSourceToTarget.SetMatrix(matrixSourceToTarget)
    transformSourceToTarget.GetPosition(self.currentPositionMm)
    
    # determine self.currentDistanceFromPointNMinus2Mm
    if (self.markupsFiducialNode.GetNumberOfFiducials() >= 2):
      pointNMinus2Mm = [0,0,0]
      self.markupsFiducialNode.GetNthFiducialPosition(self.markupsFiducialNode.GetNumberOfFiducials() - 2, pointNMinus2Mm)
      positionRelativeToPointNMinus2Mm = [0,0,0]
      vtk.vtkMath.Subtract(self.currentPositionMm,pointNMinus2Mm,positionRelativeToPointNMinus2Mm)
      self.currentDistanceFromPointNMinus2Mm = vtk.vtkMath.Norm(positionRelativeToPointNMinus2Mm)
    else:
      self.currentDistanceFromPointNMinus2Mm = 0
    
    # determine self.currentDistanceFromPointNMinus3Mm
    if (self.markupsFiducialNode.GetNumberOfFiducials() >= 3):
      pointNMinus3Mm = [0,0,0] # second last point
      self.markupsFiducialNode.GetNthFiducialPosition(self.markupsFiducialNode.GetNumberOfFiducials() - 3, pointNMinus3Mm)
      positionRelativeToPointNMinus3Mm = [0,0,0]
      vtk.vtkMath.Subtract(self.currentPositionMm,pointNMinus3Mm,positionRelativeToPointNMinus3Mm)
      self.currentDistanceFromPointNMinus3Mm = vtk.vtkMath.Norm(positionRelativeToPointNMinus3Mm)
    else:
      self.currentDistanceFromPointNMinus3Mm = 0

  def addPointConditions(self):
    if (self.markupsFiducialNode.GetNumberOfFiducials() < 2): # currentDistanceFromPointNMinus2Mm couldn't be computed
      return True
    if (self.currentDistanceFromPointNMinus2Mm >= self.minimumAddDistanceMm):
      return True
    return False
    
  def removePointConditions(self):
    if (self.allowPointRemovals == False):
      return False
    if (self.markupsFiducialNode.GetNumberOfFiducials() < 3): # currentDistanceFromPointNMinus3Mm couldn't be computed
      return False
    if (self.currentDistanceFromPointNMinus3Mm < self.minimumAddDistanceMm):
      return True
    return False
    
  def addPoint(self):
    # Two tasks: 1. Move the last point to boundary of the sphere around pointNMinus2
    #            2. Add a new point at the current position
    # print "Add Point"
    # task 1
    if (self.forceConstantPointDistance == True and self.markupsFiducialNode.GetNumberOfFiducials() >= 2):
      pointNMinus1Index = self.markupsFiducialNode.GetNumberOfFiducials() - 1
      pointNMinus1Mm = [0,0,0]
      self.markupsFiducialNode.GetNthFiducialPosition(pointNMinus1Index, pointNMinus1Mm)
      
      pointNMinus2Index = self.markupsFiducialNode.GetNumberOfFiducials() - 2
      pointNMinus2Mm = [0,0,0]
      self.markupsFiducialNode.GetNthFiducialPosition(pointNMinus2Index, pointNMinus2Mm)
      
      # calculate the vector that moves pointNMinus1Mm from pointNMinus2Mm to the sphere boundary
      trajectory = [0,0,0]
      vtk.vtkMath.Subtract(pointNMinus1Mm,pointNMinus2Mm,trajectory)
      vtk.vtkMath.Normalize(trajectory)
      vtk.vtkMath.MultiplyScalar(trajectory,self.minimumAddDistanceMm)

      # apply the vector and find the new pointNMinus1Mm
      newPointNMinus1Mm = [0,0,0]
      vtk.vtkMath.Add(pointNMinus2Mm,trajectory,newPointNMinus1Mm)
      self.markupsFiducialNode.SetMarkupPointFromArray(pointNMinus1Index,0,newPointNMinus1Mm)
      
    # task 2
    self.markupsFiducialNode.AddFiducialFromArray(self.currentPositionMm)
  
  def removePoint(self):
    self.markupsFiducialNode.RemoveMarkup(self.markupsFiducialNode.GetNumberOfFiducials() - 1)
    
  def moveLastPoint(self):
    if (self.markupsFiducialNode.GetNumberOfFiducials() >= 1):
      pointNMinus1Index = self.markupsFiducialNode.GetNumberOfFiducials() - 1
      self.markupsFiducialNode.SetMarkupPointFromArray(pointNMinus1Index,0,self.currentPositionMm)
  
  def removeAllPoints(self):
    if (self.markupsFiducialNode):
      while (self.markupsFiducialNode.GetNumberOfFiducials() > 0):
        indexOfLastPoint = self.markupsFiducialNode.GetNumberOfFiducials() - 1;
        self.markupsFiducialNode.RemoveMarkup(indexOfLastPoint)
