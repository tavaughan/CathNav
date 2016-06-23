from __main__ import vtk, qt, ctk, slicer
from slicer.ScriptedLoadableModule import *

#
# InsertionGridPlanner
#

class InsertionGridPlanner(ScriptedLoadableModule):
  def __init__(self, parent):
    parent.title = "InsertionGridPlanner"
    parent.categories = ["IGT"]
    parent.dependencies = []
    parent.contributors = ["Thomas Vaughan (Queen's)", "Gabor Fichtinger (Queen's)"]
    parent.helpText = """
    Plan a grid of needle insertions.
    """
    parent.acknowledgementText = """
	This work is funded as a project in the Laboratory for Percutaneous Surgery, Queen's University, Kingston, Ontario. Thomas Vaughan is funded by an NSERC Postgraduate award. Gabor Fichtinger is funded as a Cancer Care Ontario (CCO) Chair.
	""" # replace with organization, grant and thanks.
    self.parent = parent

#
# InsertionGridPlannerWidget
#

class InsertionGridPlannerWidget(ScriptedLoadableModuleWidget):
    
  def setup(self):
    ScriptedLoadableModuleWidget.setup(self)
    
    # TODO: The following lines are strictly for debug purposes, should be removed when this module is done
    self.developerMode = True
    slicer.igwidget = self
    
    self.logic = InsertionGridPlannerLogic()

    # Collapsible buttons
    self.parametersCollapsibleButton = ctk.ctkCollapsibleButton()
    self.parametersCollapsibleButton.text = "InsertionGridPlanner"
    self.layout.addWidget(self.parametersCollapsibleButton)

    # Layout within the collapsible button
    self.parametersFormLayout = qt.QFormLayout(self.parametersCollapsibleButton)
    
    # Transform Tool Tip To Reference combobox
    self.transformNodeGridToTargetLabel = qt.QLabel()
    self.transformNodeGridToTargetLabel.setText("Grid to Target Transform: ")
    self.transformNodeGridToTargetSelector = slicer.qMRMLNodeComboBox()
    self.transformNodeGridToTargetSelector.nodeTypes = ( ("vtkMRMLLinearTransformNode"), "" )
    self.transformNodeGridToTargetSelector.noneEnabled = False
    self.transformNodeGridToTargetSelector.addEnabled = False
    self.transformNodeGridToTargetSelector.removeEnabled = False
    self.transformNodeGridToTargetSelector.setMRMLScene( slicer.mrmlScene )
    self.transformNodeGridToTargetSelector.setToolTip("Pick the transform for going from the grid's coordinate system to the target (reference) coordinate system")
    self.parametersFormLayout.addRow(self.transformNodeGridToTargetLabel, self.transformNodeGridToTargetSelector)
    
    # Grid type
    self.gridPatternRectangularLabel = qt.QLabel(qt.Qt.Horizontal,None)
    self.gridPatternRectangularLabel.setText("Rectangular Grid")
    self.gridPatternRectangularRadioButton = qt.QRadioButton()
    self.gridPatternRectangularRadioButton.setToolTip("Make the grid rectangular")
    self.gridPatternRectangularRadioButton.setChecked(True)
    self.parametersFormLayout.addRow(self.gridPatternRectangularLabel,self.gridPatternRectangularRadioButton)
    
    self.gridPatternTriangularLabel = qt.QLabel(qt.Qt.Horizontal,None)
    self.gridPatternTriangularLabel.setText("Triangular Grid")
    self.gridPatternTriangularRadioButton = qt.QRadioButton()
    self.gridPatternTriangularRadioButton.setToolTip("Make the grid triangular")
    self.parametersFormLayout.addRow(self.gridPatternTriangularLabel,self.gridPatternTriangularRadioButton)

    # Grid size
    self.gridSizeLeftLabel = qt.QLabel()
    self.gridSizeLeftLabel.setText("Extent left (mm): ")
    self.gridSizeLeftSlider = slicer.qMRMLSliderWidget()
    self.gridSizeLeftSlider.minimum = 0 # mm
    self.gridSizeLeftSlider.maximum = 150 # mm
    self.gridSizeLeftSlider.value = 0 # mm
    self.gridSizeLeftSlider.setToolTip("Adjust the size of the grid")
    self.parametersFormLayout.addRow(self.gridSizeLeftLabel, self.gridSizeLeftSlider)
    
    self.gridSizeRightLabel = qt.QLabel()
    self.gridSizeRightLabel.setText("Extent right (mm): ")
    self.gridSizeRightSlider = slicer.qMRMLSliderWidget()
    self.gridSizeRightSlider.minimum = 0 # mm
    self.gridSizeRightSlider.maximum = 150 # mm
    self.gridSizeRightSlider.value = 0 # mm
    self.gridSizeRightSlider.setToolTip("Adjust the size of the grid")
    self.parametersFormLayout.addRow(self.gridSizeRightLabel, self.gridSizeRightSlider)
    
    self.gridSizeUpLabel = qt.QLabel()
    self.gridSizeUpLabel.setText("Extent up (mm): ")
    self.gridSizeUpSlider = slicer.qMRMLSliderWidget()
    self.gridSizeUpSlider.minimum = 0 # mm
    self.gridSizeUpSlider.maximum = 150 # mm
    self.gridSizeUpSlider.value = 0 # mm
    self.gridSizeUpSlider.setToolTip("Adjust the size of the grid")
    self.parametersFormLayout.addRow(self.gridSizeUpLabel, self.gridSizeUpSlider)
    
    self.gridSizeDownLabel = qt.QLabel()
    self.gridSizeDownLabel.setText("Extent down (mm): ")
    self.gridSizeDownSlider = slicer.qMRMLSliderWidget()
    self.gridSizeDownSlider.minimum = 0 # mm
    self.gridSizeDownSlider.maximum = 150 # mm
    self.gridSizeDownSlider.value = 0 # mm
    self.gridSizeDownSlider.setToolTip("Adjust the size of the grid")
    self.parametersFormLayout.addRow(self.gridSizeDownLabel, self.gridSizeDownSlider)
    
    # Grid spacing
    self.gridSpacingHorizontalLabel = qt.QLabel(qt.Qt.Horizontal,None)
    self.gridSpacingHorizontalLabel.text = "Horizontal Spacing (mm): "
    self.gridSpacingHorizontalSlider = slicer.qMRMLSliderWidget()
    self.gridSpacingHorizontalSlider.minimum = 1 # mm
    self.gridSpacingHorizontalSlider.maximum = 50 # mm
    self.gridSpacingHorizontalSlider.value = 10 # mm
    self.parametersFormLayout.addRow(self.gridSpacingHorizontalLabel,self.gridSpacingHorizontalSlider)
    
    self.gridSpacingVerticalLabel = qt.QLabel(qt.Qt.Horizontal,None)
    self.gridSpacingVerticalLabel.text = "Vertical Spacing (mm): "
    self.gridSpacingVerticalSlider = slicer.qMRMLSliderWidget()
    self.gridSpacingVerticalSlider.minimum = 1 # mm
    self.gridSpacingVerticalSlider.maximum = 50 # mm
    self.gridSpacingVerticalSlider.value = 10 # mm
    self.parametersFormLayout.addRow(self.gridSpacingVerticalLabel,self.gridSpacingVerticalSlider)
    
    # Grid creation
    self.createGridButton = qt.QPushButton()
    self.createGridButton.text = "Create Grid"
    self.createGridButton.setToolTip("Create the virtual grid guide.")
    self.parametersFormLayout.addRow(self.createGridButton)
    
    self.deleteGridButton = qt.QPushButton()
    self.deleteGridButton.text = "Delete Grid"
    self.deleteGridButton.setToolTip("Delete the virtual grid guide.")
    self.parametersFormLayout.addRow(self.deleteGridButton)

    # Add vertical spacer
    self.layout.addStretch(1)
    
    #Connections
    self.createGridButton.connect('clicked()', self.createGridButtonPressed)
    self.deleteGridButton.connect('clicked()', self.logic.deleteGrid)

  def createGridButtonPressed(self):
    print "Create grid pressed"
    self.logic.setTransformGridToTargetNode(self.transformNodeGridToTargetSelector.currentNode())
    if (self.gridPatternRectangularRadioButton.checked):
      self.logic.setGridPatternToRectangular()
    elif (self.gridPatternTriangularRadioButton.checked):
      self.logic.setGridPatternToTriangular()
    self.logic.setGridSizeLeftMm(self.gridSizeLeftSlider.value)
    self.logic.setGridSizeRightMm(self.gridSizeRightSlider.value)
    self.logic.setGridSizeUpMm(self.gridSizeUpSlider.value)
    self.logic.setGridSizeDownMm(self.gridSizeDownSlider.value)
    self.logic.setGridSpacingHorizontalMm(self.gridSpacingHorizontalSlider.value)
    self.logic.setGridSpacingVerticalMm(self.gridSpacingVerticalSlider.value)
    self.logic.createGrid()

#
# InsertionGridPlannerLogic
#

class InsertionGridPlannerLogic(ScriptedLoadableModuleLogic):
  def __init__(self):
    # constants - DO NOT CHANGE THESE
    self.gridPatternRectangular = 0
    self.gridPatternTriangular = 1
    
    # inputs
    self.transformGridToTargetNode = None
    self.gridPattern = self.gridPatternRectangular
    self.gridSizeLeftMm = 0
    self.gridSizeRightMm = 0
    self.gridSizeUpMm = 0
    self.gridSizeDownMm = 0
    self.gridSpacingHorizontalMm = 10
    self.gridSpacingVerticalMm = 10
    
    # outputs
    self.outputModelNode = None
    self.outputDisplayNode = None
      
  def setTransformGridToTargetNode(self,node):
    print "setTransformGridToTargetNode"
    self.transformGridToTargetNode = node
    
  def setGridPatternToRectangular(self):
    print "setPatternToRectangular"
    self.gridPattern = self.gridPatternRectangular
  
  def setGridPatternToTriangular(self):
    print "setPatternToTriangular"
    self.gridPattern = self.gridPatternTriangular
    
  def setGridSizeLeftMm(self,sizeMm):
    print "setGridSizeLeftMm"
    self.gridSizeLeftMm = sizeMm
      
  def setGridSizeRightMm(self,sizeMm):
    print "setGridSizeRightMm"
    self.gridSizeRightMm = sizeMm
      
  def setGridSizeUpMm(self,sizeMm):
    print "setGridSizeUpMm"
    self.gridSizeUpMm = sizeMm
      
  def setGridSizeDownMm(self,sizeMm):
    print "setGridSizeDownMm"
    self.gridSizeDownMm = sizeMm
    
  def setGridSpacingHorizontalMm(self,spacingMm):
    print "setGridSpacingHorizontalMm"
    self.gridSpacingHorizontalMm = spacingMm
    
  def setGridSpacingVerticalMm(self,spacingMm):
    print "setGridSpacingVerticalMm"
    self.gridSpacingVerticalMm = spacingMm
    
  def createGrid(self):
    print "createGrid"
    self.deleteGrid()
    self.generateGridModel()
    
  def generateGridModel(self):
    print "generateGridModel"
    polyData = vtk.vtkPolyData()
    if (self.gridPattern == self.gridPatternRectangular):
      polyData = self.generateGridPolyDataRectangular()
    elif (self.gridPattern == self.gridPatternTriangular):
      polyData = self.generateGridPolyDataTriangular()
    self.addPolyDataToScene(polyData,"Grid")
    
  def evaluateLowerHorizontalBoundMm(self):
    return -(self.gridSizeLeftMm // self.gridSpacingHorizontalMm) * self.gridSpacingHorizontalMm
    
  def evaluateUpperHorizontalBoundMm(self):
    return (self.gridSizeRightMm // self.gridSpacingHorizontalMm) * self.gridSpacingHorizontalMm
    
  def evaluateLowerVerticalBoundMm(self):
    return -(self.gridSizeDownMm // self.gridSpacingVerticalMm) * self.gridSpacingVerticalMm
    
  def evaluateUpperVerticalBoundMm(self):
    return (self.gridSizeUpMm // self.gridSpacingVerticalMm) * self.gridSpacingVerticalMm
    
  def generateGridPolyDataRectangular(self):
    polyDataCombiner = vtk.vtkAppendPolyData()
    
    lowerHorizontalBoundMm = self.evaluateLowerHorizontalBoundMm()
    upperHorizontalBoundMm = self.evaluateUpperHorizontalBoundMm()
    
    lowerVerticalBoundMm = self.evaluateLowerVerticalBoundMm()
    upperVerticalBoundMm = self.evaluateUpperVerticalBoundMm()

    # traditional 'for' loops would be very nice here... :-/
    yMm = lowerVerticalBoundMm
    while (yMm <= upperVerticalBoundMm):
      xMm = lowerHorizontalBoundMm    
      while (xMm <= upperHorizontalBoundMm):
        cylinderPolyData = self.generateCylinderPolyData(xMm,yMm)
        polyDataCombiner.AddInputData(cylinderPolyData)
        xMm = xMm + self.gridSpacingHorizontalMm
      yMm = yMm + self.gridSpacingVerticalMm
      
    polyDataCombiner.Update()
    gridPolyData = polyDataCombiner.GetOutput()
    return gridPolyData
    
  def generateGridPolyDataTriangular(self):
    polyDataCombiner = vtk.vtkAppendPolyData()
    
    lowerHorizontalBoundMm = self.evaluateLowerHorizontalBoundMm()
    upperHorizontalBoundMm = self.evaluateUpperHorizontalBoundMm()
    
    lowerVerticalBoundMm = self.evaluateLowerVerticalBoundMm()
    upperVerticalBoundMm = self.evaluateUpperVerticalBoundMm()

    # traditional 'for' loops would be very nice here... :-/
    yMm = lowerVerticalBoundMm
    while (yMm <= upperVerticalBoundMm):
      # determine whether to offset in horizontal axis -
      # this makes the triangular pattern if done on odd rows only
      offsetMm = 0
      oddRow = (round(yMm / self.gridSpacingVerticalMm) % 2 == 1)
      if oddRow:
        offsetMm = self.gridSpacingHorizontalMm / 2.0
      xMm = lowerHorizontalBoundMm + offsetMm
      while (xMm <= upperHorizontalBoundMm):
        cylinderPolyData = self.generateCylinderPolyData(xMm,yMm)
        polyDataCombiner.AddInputData(cylinderPolyData)
        xMm = xMm + self.gridSpacingHorizontalMm
      yMm = yMm + self.gridSpacingVerticalMm
      
    polyDataCombiner.Update()
    gridPolyData = polyDataCombiner.GetOutput()
    return gridPolyData
    
  def generateCylinderPolyData(self,x,y):
    cylinderHeightMm = 80
    cylinderRadiusMm = 1
    cylinderSource = vtk.vtkCylinderSource()
    cylinderSource.SetHeight(cylinderHeightMm)
    cylinderSource.SetRadius(cylinderRadiusMm)
    renderDepthMm = -cylinderHeightMm # negative because in graphics, negative is depth, positive goes toward the user
    transform = vtk.vtkTransform()
    transform.Translate(x,y,renderDepthMm)
    transform.RotateX(90) # rotate so that the cylinder follows the z axis
    transformFilter = vtk.vtkTransformFilter()
    transformFilter.SetTransform(transform)
    transformFilter.SetInputConnection(cylinderSource.GetOutputPort(0))
    transformFilter.Update()
    polyData = transformFilter.GetOutput()
    return polyData
    
  def addPolyDataToScene(self,polyData,name):
    print "addPolyDataToScene"
    self.outputDisplayNode = slicer.vtkMRMLModelDisplayNode()
    self.outputDisplayNode.SetName(name+"Display")
    self.outputDisplayNode.SetColor(0,0,1.0)
    self.outputDisplayNode.SetOpacity(0.5)
    slicer.mrmlScene.AddNode(self.outputDisplayNode)
    self.outputModelNode = slicer.vtkMRMLModelNode()
    self.outputModelNode.SetAndObservePolyData(polyData)
    self.outputModelNode.SetAndObserveDisplayNodeID(self.outputDisplayNode.GetID())
    if (self.transformGridToTargetNode):
      self.outputModelNode.SetAndObserveTransformNodeID(self.transformGridToTargetNode.GetID())
    self.outputModelNode.SetName(name)
    slicer.mrmlScene.AddNode(self.outputModelNode)
      
  def deleteGrid(self):
    print "deleteGrid"
    if self.outputModelNode:
      slicer.mrmlScene.RemoveNode(self.outputModelNode)
      self.outputModelNode = None
    if self.outputDisplayNode:
      slicer.mrmlScene.RemoveNode(self.outputDisplayNode)
      self.outputDisplayNode = None
