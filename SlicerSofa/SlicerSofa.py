import logging
import os
from typing import Annotated, Optional
from abc import abstractmethod

import vtk

import slicer
from slicer.i18n import tr as _
from slicer.i18n import translate
from slicer.ScriptedLoadableModule import *
from slicer.util import VTKObservationMixin
from slicer.parameterNodeWrapper import (
    parameterNodeWrapper,
    WithinRange,
)

from slicer import vtkMRMLScalarVolumeNode

from SofaEnvironment import *

#
# SlicerSofa
#


class SlicerSofa(ScriptedLoadableModule):
    """Uses ScriptedLoadableModule base class, available at:
    https://github.com/Slicer/Slicer/blob/main/Base/Python/slicer/ScriptedLoadableModule.py
    """

    def __init__(self, parent):
        ScriptedLoadableModule.__init__(self, parent)
        self.parent.title = _("Slicer Sofa")
        self.parent.categories = [translate("qSlicerAbstractCoreModule", "")]
        self.parent.dependencies = []
        self.parent.contributors = [ "Rafael Palomar (Oslo University Hospital, Norway), Paul Baksic (INRIA, France), Steve Pieper (Isomics, Inc., USA), Andras Lasso (Queen's University, Canada), Sam Horvath (Kitware, Inc., USA), Jean Christophe Fillion-Robin (Kitware, Inc., USA)"]
        self.parent.helpText = _("""
This is a support module to enable simulations using the SOFA framework
See more information in <a href="https://github.com/RafaelPalomar/Slicer-SOFA">module documentation</a>.
""")
        # TODO: replace with organization, grant and thanks
        self.parent.acknowledgementText = _("""
This project has been funded by Oslo University Hospital
""")

        #Hide module, so that it only shows up in the Liver module, and not as a separate module
        parent.hidden = True

#
# SofaLogic
#


class SlicerSofaLogic(ScriptedLoadableModuleLogic):
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
        super().__init__()

        self._sceneUp = False
        self._rootNode = None
        self._simulationRunning = False
        self._currentStep = 0
        self._totalSteps = 0
        self._dt = 0
        self.initialgrid = []
        self.startup = True

    def setupScene(self, parameterNode):
        """Setup the simulation scene."""
        if not self._sceneUp:
            self._rootNode = self.createScene(parameterNode)
            Sofa.Simulation.init(self._rootNode)
            self._sceneUp = True

    def startSimulation(self, parameterNode=None) -> None:
        """Start the simulation."""
        self.setupScene(parameterNode)
        self._currentStep = 0
        self._simulationRunning = True

    def stopSimulation(self) -> None:
        """Stop the simulation."""
        if self._sceneUp is True:
            self._simulationRunning = False

    def resetSimulation(self, parameterNode=None) -> None:
        pass

    def simulationStep(self, parameterNode=None) -> None:
        """Perform a single simulation step."""
        if self._sceneUp is False or self._simulationRunning is False:
           slicer.util.errorDisplay("Can't advance the simulation forward. Simulation is not running.")
           return
        parameterNode.modelNode.GetUnstructuredGrid()
        
        self.updateSofa(parameterNode)
        if self._currentStep < self._totalSteps:
            Sofa.Simulation.animate(self._rootNode, self._dt)
            self._currentStep += 1
        elif self._totalSteps < 0:
            Sofa.Simulation.animate(self._rootNode, self._dt)
        else:
            self._simulationRunning = False

        self.updateMRML(parameterNode)

    def clean(self) -> None:
        """Cleans up the simulation"""
        if self._sceneUp is True and self._rootNode:
            Sofa.Simulation.unload(self._rootNode)
            self._rootNode = None
            self._sceneUp = False
            self._simulationRunning = False

    @property
    def rootNode(self):
        return self._rootNode

    @property
    def isSimulationRunning(self):
        return self._simulationRunning

    @property
    def currentStep(self):
        return self._currentStep

    @property
    def totalSteps(self):
        return self._totalSteps

    @property
    def dt(self):
        return self._dt

    @currentStep.setter
    def currentStep(self, step):
       self._currentStep = step

    @totalSteps.setter
    def totalSteps(self, steps):
        self._totalSteps = steps

    @dt.setter
    def dt(self, dt):
        self._dt = dt

    @abstractmethod
    def updateSofa(self, parameterNode) -> None:
        """Update Sofa simulation parameters. Must be implemented by subclasses."""
        pass

    @abstractmethod
    def updateMRML(self, parameterNode) -> None:
        """Update the simulation scene. Must be implemented by subclasses."""
        pass

    @abstractmethod
    def createScene(self, parameterNode) -> Sofa.Core.Node:
        """Create the simulation scene. Must be implemented by subclasses."""
        pass
