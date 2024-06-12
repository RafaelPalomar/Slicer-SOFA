import logging
import os
from typing import Annotated, Optional
import qt
import vtk
from vtk.util.numpy_support import numpy_to_vtk
import random
import time
import uuid
import numpy as np

# import Simulations.SOFASimulationMulti as multi

import slicer
from slicer.i18n import tr as _
from slicer.i18n import translate
from slicer.ScriptedLoadableModule import *
from slicer.util import VTKObservationMixin
from slicer.parameterNodeWrapper import (
    parameterNodeWrapper,
    WithinRange,
)

from slicer import vtkMRMLIGTLConnectorNode
from slicer import vtkMRMLMarkupsFiducialNode
from slicer import vtkMRMLMarkupsLineNode
from slicer import vtkMRMLMarkupsNode
from slicer import vtkMRMLMarkupsROINode
from slicer import vtkMRMLModelNode
from slicer import vtkMRMLSequenceBrowserNode
from slicer import vtkMRMLSequenceNode

from SofaSimulation import *

#
# SoftTissueSimulation
#


class SoftTissueSimulation(ScriptedLoadableModule):
    """Uses ScriptedLoadableModule base class, available at:
    https://github.com/Slicer/Slicer/blob/main/Base/Python/slicer/ScriptedLoadableModule.py
    """

    def __init__(self, parent):
        ScriptedLoadableModule.__init__(self, parent)
        self.parent.title = _("Soft Tissue Simulation")
        self.parent.categories = [translate("qSlicerAbstractCoreModule", "Examples")]
        self.parent.dependencies = []  # TODO: add here list of module names that this module requires
        self.parent.contributors = ["Rafael Palomar (Oslo University Hospital), Paul Baksic (INRIA), Steve Pieper (Isomics, inc.), Andras Lasso (Queen's University), Sam Horvath (Kitware, inc.)"]
        # TODO: update with short description of the module and a link to online module documentation
        # _() function marks text as translatable to other languages
        self.parent.helpText = _("""""")
        # TODO: replace with organization, grant and thanks
        self.parent.acknowledgementText = _("""""")

        # Additional initialization step after application startup is complete
        slicer.app.connect("startupCompleted()", registerSampleData)

#
# Register sample data sets in Sample Data module
#


def registerSampleData():
    """Add data sets to Sample Data module."""

    import SampleData

    iconsPath = os.path.join(os.path.dirname(__file__), "Resources/Icons")

    slicerSOFADataURL= 'https://github.com/rafaelpalomar/SlicerSOFATestingData/releases/download/'

    # To ensure that the source code repository remains small (can be downloaded and installed quickly)
    # it is recommended to store data sets that are larger than a few MB in a Github release.

    # Right lung low poly tetrahedral mesh dataset
    SampleData.SampleDataLogic.registerCustomSampleDataSource(
        category='SOFA',
        sampleName='RightLungLowTetra',
        thumbnailFileName=os.path.join(iconsPath, 'RightLungLowTetra.png'),
        uris=slicerSOFADataURL+ 'SHA256/a35ce6ca2ae565fe039010eca3bb23f5ef5f5de518b1c10257f12cb7ead05c5d',
        fileNames='RightLungLowTetra.vtk',
        checksums='SHA256:a35ce6ca2ae565fe039010eca3bb23f5ef5f5de518b1c10257f12cb7ead05c5d',
        nodeNames='RightLung',
        loadFileType='ModelFile'
    )

#
# SoftTissueSimulationParameterNode
#

@parameterNodeWrapper
class SoftTissueSimulationParameterNode:
    """
    The parameters needed by module.
    """
    #Simulation data
    modelNode: vtkMRMLModelNode
    boundaryROI: vtkMRMLMarkupsROINode
    gravityVector: vtkMRMLMarkupsLineNode
    gravityMagnitude: int
    movingPointNode: vtkMRMLMarkupsFiducialNode
    sequenceNode: vtkMRMLSequenceNode
    sequenceBrowserNode: vtkMRMLSequenceBrowserNode
    #Simulation control
    dt: float
    totalSteps: int
    currentStep: int

    def getBoundaryROI(self):

        if self.boundaryROI is None:
            return [0.0]*6

        center = [0]*3
        self.boundaryROI.GetCenter(center)
        size = self.boundaryROI.GetSize()

        # Calculate min and max RAS bounds from center and size
        R_min = center[0] - size[0] / 2
        R_max = center[0] + size[0] / 2
        A_min = center[1] - size[1] / 2
        A_max = center[1] + size[1] / 2
        S_min = center[2] - size[2] / 2
        S_max = center[2] + size[2] / 2

        # Return the two opposing bounds corners
        # First corner: (minL, minP, minS), Second corner: (maxL, maxP, maxS)
        return [R_min, A_min, S_min, R_max, A_max, S_max]

    def getGravityVector(self):

        if self.gravityVector is None:
            return [0.0]*3

        p1 = self.gravityVector.GetNthControlPointPosition(0)
        p2 = self.gravityVector.GetNthControlPointPosition(1)
        gravity_vector = np.array([p2[0]-p1[0], p2[1]-p1[1], p2[2]-p1[2]])
        magnitude = np.linalg.norm(gravity_vector)
        normalized_gravity_vector = gravity_vector / magnitude if magnitude != 0 else gravity_vector

        return normalized_gravity_vector*self.gravityMagnitude


    def getModelPointsArray(self):
        """
        Convert the point positions from the VTK model to a Python list.
        """
        # Get the unstructured grid from the model node
        unstructured_grid = self.modelNode.GetUnstructuredGrid()

        # Extract point data from the unstructured grid
        points = unstructured_grid.GetPoints()
        num_points = points.GetNumberOfPoints()

        # Convert the VTK points to a list
        point_coords = []
        for i in range(num_points):
            point_coords.append(points.GetPoint(i))

        return point_coords

    def getModelCellsArray(self):
        """
        Convert the cell connectivity from the VTK model to a Python list.
        """
        # Get the unstructured grid from the model node
        unstructured_grid = self.modelNode.GetUnstructuredGrid()

        # Extract cell data from the unstructured grid
        cells = unstructured_grid.GetCells()
        cell_array = vtk.util.numpy_support.vtk_to_numpy(cells.GetData())

        # The first integer in each cell entry is the number of points per cell (always 4 for tetrahedra)
        # Followed by the point indices
        num_cells = unstructured_grid.GetNumberOfCells()
        cell_connectivity = []

        # Fill the cell connectivity list
        idx = 0
        for i in range(num_cells):
            num_points = cell_array[idx]  # Should always be 4 for tetrahedra
            cell_connectivity.append(cell_array[idx+1:idx+1+num_points].tolist())
            idx += num_points + 1

        return cell_connectivity

#
# SoftTissueSimulationWidget
#

class SoftTissueSimulationWidget(ScriptedLoadableModuleWidget, VTKObservationMixin):
    """Uses ScriptedLoadableModuleWidget base class, available at:
    https://github.com/Slicer/Slicer/blob/main/Base/Python/slicer/ScriptedLoadableModule.py
    """

    def __init__(self, parent=None) -> None:
        """Called when the user opens the module the first time and the widget is initialized."""
        ScriptedLoadableModuleWidget.__init__(self, parent)
        VTKObservationMixin.__init__(self)  # needed for parameter node observation
        self.logic = None
        self.parameterNode = None
        self.parameterNodeGuiTag = None

        # These two variables are part of a workaround to solve a race condition
        # between the parameter node update and the gui update (e.g., (1) when a dynamic
        # property is defined in QT Designer and (2) a manual QT connect is defined and (3)
        # the corresponding slot function needs an updated parameter node). This workaround
        # uses a timer to make the slot function go last in the order of events.
        self.timer = qt.QTimer()
        self.timeout = False

    def setup(self) -> None:
        """Called when the user opens the module the first time and the widget is initialized."""
        ScriptedLoadableModuleWidget.setup(self)

        # Load widget from .ui file (created by Qt Designer).
        # Additional widgets can be instantiated manually and added to self.layout.
        uiWidget = slicer.util.loadUI(self.resourcePath("UI/SoftTissueSimulation.ui"))
        self.layout.addWidget(uiWidget)
        self.ui = slicer.util.childWidgetVariables(uiWidget)

        # Create logic class. Logic implements all computations that should be possible to run
        # in batch mode, without a graphical user interface.
        self.logic = SoftTissueSimulationLogic()

        # Set scene in MRML widgets. Make sure that in Qt designer the top-level qMRMLWidget's
        # "mrmlSceneChanged(vtkMRMLScene*)" signal in is connected to each MRML widget's.
        # "setMRMLScene(vtkMRMLScene*)" slot.
        uiWidget.setMRMLScene(slicer.mrmlScene)

        # Connections

        # These connections ensure that we update parameter node when scene is closed
        self.addObserver(slicer.mrmlScene, slicer.mrmlScene.StartCloseEvent, self.onSceneStartClose)
        self.addObserver(slicer.mrmlScene, slicer.mrmlScene.EndCloseEvent, self.onSceneEndClose)

        self.ui.startSimulationPushButton.connect("clicked()", self.logic.startSimulation)
        self.ui.addBoundaryROIPushButton.connect("clicked()", self.logic.addBoundaryROI)
        self.ui.addGravityVectorPushButton.connect("clicked()", self.logic.addGravityVector)
        self.ui.addMovingPointPushButton.connect("clicked()", self.logic.addMovingPoint)
        self.ui.addRecordingSequencePushButton.connect("clicked()", self.logic.addRecordingSequence)

        # Make sure parameter node is initialized (needed for module reload)
        self.initializeParameterNode()

        parameterNode = self.logic.getParameterNode()
        parameterNode.AddObserver(vtk.vtkCommand.ModifiedEvent, self.updateSimulationPushButtons)

    def cleanup(self) -> None:
        """Called when the application closes and the module widget is destroyed."""
        self.logic.cleanup()
        self.removeObservers()


    def enter(self) -> None:
        # """Called each time the user opens this module."""
        # # Make sure parameter node exists and observed
        # self.initializeParameterNode()
        pass

    def exit(self) -> None:
        """Called each time the user opens a different module."""
        # Do not react to parameter node changes (GUI will be updated when the user enters into the module)
        if self.parameterNode:
            self.parameterNode.disconnectGui(self.parameterNodeGuiTag)
            self.parameterNodeGuiTag = None

    def onSceneStartClose(self, caller, event) -> None:
        """Called just before the scene is closed."""
        # Parameter node will be reset, do not use it anymore
        self.setParameterNode(None)

    def onSceneEndClose(self, caller, event) -> None:
        """Called just after the scene is closed."""
        # If this module is shown while the scene is closed then recreate a new parameter node immediately
        if self.parent.isEntered:
            self.initializeParameterNode()

    def initializeParameterNode(self) -> None:
        # Parameter node stores all user choices in parameter values, node selections, etc.
        # so that when the scene is saved and reloaded, these settings are restored.

        self.setParameterNode(self.logic.getParameterNode())
        self.parameterNode.modelNode = None
        self.parameterNode.boundaryROI = None
        self.parameterNode.gravityVector = None
        self.parameterNode.sequenceNode = None
        self.parameterNode.sequenceBrowserNode = None
        self.parameterNode.dt = self.ui.dtSpinBox.value
        self.parameterNode.currentStep = self.ui.currentStepSpinBox.value
        self.parameterNode.totalSteps= self.ui.totalStepsSpinBox.value

    def setParameterNode(self, inputParameterNode: Optional[SoftTissueSimulationParameterNode]) -> None:
        """
        Set and observe parameter node.
        Observation is needed because when the parameter node is changed then the GUI must be updated immediately.
        """
        if self.parameterNode:
            self.parameterNode.disconnectGui(self.parameterNodeGuiTag)
        self.parameterNode = inputParameterNode
        if self.parameterNode:
            # Note: in the .ui file, a Qt dynamic property called "SlicerParameterName" is set on each
            # ui element that needs connection.
            self.parameterNodeGuiTag = self.parameterNode.connectGui(self.ui)

    def updateSimulationPushButtons(self, caller, event):
        """This enables/disables the simulation buttons according to the state of the parameter node"""

        modelNode = self.parameterNode.modelNode
        enableSimulationButton = True if None not in [modelNode] else False
        self.ui.startSimulationPushButton.setEnabled(enableSimulationButton)

#
# SoftTissueSimulationLogic
#

class SoftTissueSimulationLogic(ScriptedLoadableModuleLogic):
    """This class should implement all the actual
    computation done by your module.  The interface
    should be such that other python code can import
    this class and make use of the functionality without
    requiring an instance of the Widget.
    Uses ScriptedLoadableModuleLogic base class, available at:
    https://github.com/Slicer/Slicer/blob/main/Base/Python/slicer/ScriptedLoadableModule.py
    """

    def __init__(self) -> None:
        """Called when the logic class is instantiated. Can be used for initializing member variables."""
        ScriptedLoadableModuleLogic.__init__(self)
        self.connectionStatus = 0
        self.parameterNode = self.getParameterNode()
        self.simulationController = None

    def cleanup(self) -> None:
        print("Cleaning Simulation")
        self.simulationController.clean()

    def getParameterNode(self):
        return SoftTissueSimulationParameterNode(super().getParameterNode())

    def startSimulation(self) -> None:

        sequenceNode = self.parameterNode.sequenceNode
        browserNode = self.parameterNode.sequenceBrowserNode
        modelNode = self.parameterNode.modelNode
        movingPointNode = self.parameterNode.movingPointNode

        # Synchronize and set up the sequence browser node
        if None not in [sequenceNode, browserNode, modelNode]:
            browserNode.AddSynchronizedSequenceNodeID(sequenceNode.GetID())
            browserNode.AddProxyNode(modelNode, sequenceNode, False)
            browserNode.SetRecording(sequenceNode, True)
            browserNode.SetRecordingActive(True)

        if self.parameterNode.modelNode is not None:
            self.simulationController = SoftTissueSimulationController(self.parameterNode)
            self.simulationController.setupScene()
            self.simulationController.start()

    def onModelNodeModified(self, caller, event) -> None:
        if self.parameterNode.modelNode.GetUnstructuredGrid() is not None:
            self.parameterNode.modelNode.GetUnstructuredGrid().SetPoints(caller.GetPolyData().GetPoints())
        elif self.parameterNode.modelNode.GetPolyData() is not None:
            self.parameterNode.modelNode.GetPolyData().SetPoints(caller.GetPolyData().GetPoints())

    def addBoundaryROI(self) -> None:
        roiNode = slicer.vtkMRMLMarkupsROINode()
        mesh = None
        bounds = None

        if self.parameterNode.modelNode is not None:
            if self.parameterNode.modelNode.GetUnstructuredGrid() is not None:
                mesh = self.parameterNode.modelNode.GetUnstructuredGrid()
            elif self.parameterNode.modelNode.GetPolyData() is not None:
                mesh = self.parameterNode.modelNode.GetPolyData()

        if mesh is not None:
            bounds = mesh.GetBounds()
            center = [(bounds[0] + bounds[1])/2.0, (bounds[2] + bounds[3])/2.0, (bounds[4] + bounds[5])/2.0]
            size = [abs(bounds[1] - bounds[0])/2.0, abs(bounds[3] - bounds[2])/2.0, abs(bounds[5] - bounds[4])/2.0]
            roiNode.SetXYZ(center)
            roiNode.SetRadiusXYZ(size[0], size[1], size[2])

        roiNode = slicer.mrmlScene.AddNode(roiNode)
        if roiNode is not None:
            roiNode.CreateDefaultDisplayNodes()

    def addGravityVector(self) -> None:
        # Create a new line node for the gravity vector
        gravityVector = slicer.vtkMRMLMarkupsLineNode()
        gravityVector.SetName("Gravity")
        mesh = None

        # Check if there is a model node set in the parameter node and get its mesh
        if self.parameterNode.modelNode is not None:
            if self.parameterNode.modelNode.GetUnstructuredGrid() is not None:
                mesh = self.parameterNode.modelNode.GetUnstructuredGrid()
            elif self.parameterNode.modelNode.GetPolyData() is not None:
                mesh = self.parameterNode.modelNode.GetPolyData()

        # If a mesh is found, compute its bounding box and center
        if mesh is not None:
            bounds = mesh.GetBounds()

            # Calculate the center of the bounding box
            center = [(bounds[0] + bounds[1])/2.0, (bounds[2] + bounds[3])/2.0, (bounds[4] + bounds[5])/2.0]

            # Calculate the vector's start and end points along the Y-axis, centered on the bounding box
            startPoint = [center[0], bounds[2], center[2]]  # Start at the bottom of the bounding box
            endPoint = [center[0], bounds[3], center[2]]  # End at the top of the bounding box

            # Adjust the start and end points to center the vector in the bounding box
            vectorLength = endPoint[1] - startPoint[1]
            midPoint = startPoint[1] + vectorLength / 2.0
            startPoint[1] = midPoint - vectorLength / 2.0
            endPoint[1] = midPoint + vectorLength / 2.0

            # Add control points to define the line
            gravityVector.AddControlPoint(vtk.vtkVector3d(startPoint))
            gravityVector.AddControlPoint(vtk.vtkVector3d(endPoint))

        # Add the gravity vector line node to the scene
        gravityVector = slicer.mrmlScene.AddNode(gravityVector)
        if gravityVector is not None:
            gravityVector.CreateDefaultDisplayNodes()

    def addMovingPoint(self) -> None:

        cameraNode = slicer.util.getNode('Camera')
        if None not in [self.parameterNode.modelNode, cameraNode]:
            self.addFiducialToClosestPoint(self.parameterNode.modelNode, cameraNode)

    def addFiducialToClosestPoint(self, modelNode, cameraNode) -> None:
        # Obtain the camera's position
        camera = cameraNode.GetCamera()
        camPosition = camera.GetPosition()

        # Get the polydata from the model node
        modelData = None

        if self.parameterNode.modelNode.GetUnstructuredGrid() is not None:
            modelData = self.parameterNode.modelNode.GetUnstructuredGrid()
        elif self.parameterNode.modelNode.GetPolyData() is not None:
            modelData = self.parameterNode.modelNode.GetPolyData()

        # Set up the point locator
        pointLocator = vtk.vtkPointLocator()
        pointLocator.SetDataSet(modelData)
        pointLocator.BuildLocator()

        # Find the closest point on the model to the camera
        closestPointId = pointLocator.FindClosestPoint(camPosition)
        closestPoint = modelData.GetPoint(closestPointId)

        # Create a new fiducial node
        fiducialNode = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLMarkupsFiducialNode")
        fiducialNode.AddControlPointWorld(vtk.vtkVector3d(closestPoint))

        # Optionally, set the name and display properties
        fiducialNode.SetName("Closest Fiducial")
        displayNode = fiducialNode.GetDisplayNode()
        if displayNode:
            displayNode.SetSelectedColor(1, 0, 0)  # Red color for the selected fiducial

    def addRecordingSequence(self) -> None:

        browserNode = self.parameterNode.sequenceBrowserNode
        modelNode = self.parameterNode.modelNode

        # Ensure there is a sequence browser node; create if not present
        if browserNode is None:
            browserNode = slicer.mrmlScene.AddNewNodeByClass('vtkMRMLSequenceBrowserNode', "SOFA Simulation")
            browserNode.SetPlaybackActive(False)
            browserNode.SetRecordingActive(False)
            self.parameterNode.sequenceBrowserNode = browserNode  # Update the parameter node reference

        sequenceNode = slicer.vtkMRMLSequenceNode()

        # Configure the sequence node based on the proxy model node
        if modelNode is not None:
            sequenceNodeName = modelNode.GetName() + "-Sequence"
            sequenceNode.SetName(sequenceNodeName)

        # Now add the configured sequence node to the scene
        slicer.mrmlScene.AddNode(sequenceNode)

        self.parameterNode.sequenceNode = sequenceNode  # Update the parameter node reference

        # Configure index name and unit based on the master sequence node, if present
        masterSequenceNode = browserNode.GetMasterSequenceNode()
        if masterSequenceNode:
            sequenceNode.SetIndexName(masterSequenceNode.GetIndexName())
            sequenceNode.SetIndexUnit(masterSequenceNode.GetIndexUnit())

#
# SoftTissueSimulationTest
#


class SoftTissueSimulationTest(ScriptedLoadableModuleTest):
    """
    This is the test case for your scripted module.
    Uses ScriptedLoadableModuleTest base class, available at:
    https://github.com/Slicer/Slicer/blob/main/Base/Python/slicer/ScriptedLoadableModule.py
    """

    def setUp(self):
        """Do whatever is needed to reset the state - typically a scene clear will be enough."""
        slicer.mrmlScene.Clear()

    def runTest(self):
        """Run as few or as many tests as needed here."""
        pass


class SoftTissueSimulationController(SimulationController):

    def __init__(self, parameterNode, parent=None):

        super(SoftTissueSimulationController, self).__init__(parameterNode, parent)
        self.boxROI = None
        self.mouseInteractor = None

    def updateParameters(self) -> None:
        if self.parameterNode is not None:
            self.BoxROI.box = [self.parameterNode.getBoundaryROI()]
        if self.parameterNode.movingPointNode:
            self.mouseInteractor.position = [list(self.parameterNode.movingPointNode.GetNthControlPointPosition(0))*3]
        if self.parameterNode.gravityVector is not None:
            self.rootNode.gravity = self.parameterNode.getGravityVector()

    def updateScene(self) -> None:
        points_vtk = numpy_to_vtk(num_array=self.mechanicalObject.position.array(), deep=True, array_type=vtk.VTK_FLOAT)
        vtk_points = vtk.vtkPoints()
        vtk_points.SetData(points_vtk)
        self.parameterNode.modelNode.GetUnstructuredGrid().SetPoints(vtk_points)

    def createScene(self, parameterNode) -> Sofa.Core.Node:
        from stlib3.scene import MainHeader, ContactHeader
        from stlib3.solver import DefaultSolver
        from stlib3.physics.deformable import ElasticMaterialObject
        from stlib3.physics.rigid import Floor
        from splib3.numerics import Vec3

        rootNode = Sofa.Core.Node()

        MainHeader(rootNode, plugins=[
            "Sofa.Component.IO.Mesh",
            "Sofa.Component.LinearSolver.Direct",
            "Sofa.Component.LinearSolver.Iterative",
            "Sofa.Component.Mapping.Linear",
            "Sofa.Component.Mass",
            "Sofa.Component.ODESolver.Backward",
            "Sofa.Component.Setting",
            "Sofa.Component.SolidMechanics.FEM.Elastic",
            "Sofa.Component.StateContainer",
            "Sofa.Component.Topology.Container.Dynamic",
            "Sofa.Component.Visual",
            "Sofa.GL.Component.Rendering3D",
            "Sofa.Component.AnimationLoop",
            "Sofa.Component.Collision.Detection.Algorithm",
            "Sofa.Component.Collision.Detection.Intersection",
            "Sofa.Component.Collision.Geometry",
            "Sofa.Component.Collision.Response.Contact",
            "Sofa.Component.Constraint.Lagrangian.Solver",
            "Sofa.Component.Constraint.Lagrangian.Correction",
            "Sofa.Component.LinearSystem",
            "Sofa.Component.MechanicalLoad",
            "MultiThreading",
            "Sofa.Component.SolidMechanics.Spring",
            "Sofa.Component.Constraint.Lagrangian.Model",
            "Sofa.Component.Mapping.NonLinear",
            "Sofa.Component.Topology.Container.Constant",
            "Sofa.Component.Topology.Mapping",
            "Sofa.Component.Topology.Container.Dynamic",
            "Sofa.Component.Engine.Select",
            "Sofa.Component.Constraint.Projective",
            "SofaIGTLink"
        ])

        rootNode.addObject('FreeMotionAnimationLoop', parallelODESolving=True, parallelCollisionDetectionAndFreeMotion=True)
        rootNode.addObject('GenericConstraintSolver', maxIterations=10, multithreading=True, tolerance=1.0e-3)
        slicer.modules.rootNode = rootNode

        femNode = rootNode.addChild('FEM')
        femNode.addObject('EulerImplicitSolver', firstOrder=False, rayleighMass=0.1, rayleighStiffness=0.1)
        femNode.addObject('SparseLDLSolver', name="precond", template="CompressedRowSparseMatrixd", parallelInverseProduct=True)

        self.container = femNode.addObject('TetrahedronSetTopologyContainer', name="Container")
        self.container.position = parameterNode.getModelPointsArray()
        self.container.tetrahedra = parameterNode.getModelCellsArray()

        femNode.addObject('TetrahedronSetTopologyModifier', name="Modifier")
        femNode.addObject('MechanicalObject', name="mstate", template="Vec3d")
        femNode.addObject('TetrahedronFEMForceField', name="FEM", youngModulus=1.5, poissonRatio=0.45, method="large")
        femNode.addObject('MeshMatrixMass', totalMass=1)

        fixedROI = femNode.addChild('FixedROI')
        self.BoxROI = fixedROI.addObject('BoxROI', template="Vec3", box=[0.0, 0.0, 0.0, 0.0, 0.0, 0.0], drawBoxes=False,
                                          position="@../mstate.rest_position", name="FixedROI",
                                          computeTriangles=False, computeTetrahedra=False, computeEdges=False)
        fixedROI.addObject('FixedConstraint', indices="@FixedROI.indices")
        slicer.modules.boxROI = self.BoxROI

        collisionNode = femNode.addChild('Collision')
        collisionNode.addObject('TriangleSetTopologyContainer', name="Container")
        collisionNode.addObject('TriangleSetTopologyModifier', name="Modifier")
        collisionNode.addObject('Tetra2TriangleTopologicalMapping', input="@../Container", output="@Container")
        collisionNode.addObject('TriangleCollisionModel', name="collisionModel", proximity=0.001, contactStiffness=20)
        self.mechanicalObject = collisionNode.addObject('MechanicalObject', name='dofs', rest_position="@../mstate.rest_position")
        collisionNode.addObject('IdentityMapping', name='visualMapping')

        femNode.addObject('LinearSolverConstraintCorrection', linearSolver="@precond")

        attachPointNode = rootNode.addChild('AttachPoint')
        attachPointNode.addObject('PointSetTopologyContainer', name="Container")
        attachPointNode.addObject('PointSetTopologyModifier', name="Modifier")
        attachPointNode.addObject('MechanicalObject', name="mstate", template="Vec3d", drawMode=2, showObjectScale=0.01, showObject=False)
        self.mouseInteractor = attachPointNode.addObject('iGTLinkMouseInteractor', name="mouseInteractor", pickingType="constraint", reactionTime=20, destCollisionModel="@../FEM/Collision/collisionModel")

        return rootNode
