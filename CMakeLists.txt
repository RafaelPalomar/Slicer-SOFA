cmake_minimum_required(VERSION 3.16.3...3.19.7 FATAL_ERROR)

project(SlicerSOFA)

#-----------------------------------------------------------------------------
# Extension meta-information
set(EXTENSION_HOMEPAGE "https://github.com/RafaelPalomar/SlicerSOFA")
set(EXTENSION_CATEGORY "Simulation")
set(EXTENSION_CONTRIBUTORS "Rafael Palomar (Oslo University Hospital, Norway), Paul Baksic (INRIA, France), Steve Pieper (Isomics, Inc., USA), Andras Lasso (Queen's University, Canada), Sam Horvath (Kitware, Inc., USA), Jean Christophe Fillion-Robin (Kitware, Inc., USA)")
set(EXTENSION_DESCRIPTION "This extension enables simulations using the SOFA framework")
set(EXTENSION_ICONURL "https://raw.githubusercontent.com/RafaelPalomar/SlicerSOFA/main/slicer-sofa-logo.png")
set(EXTENSION_SCREENSHOTURLS "https://raw.githubusercontent.com/RafaelPalomar/SlicerSOFA/main/Screenshots/SoftTissueSimulationScreenshot_1.png")
set(EXTENSION_DEPENDS "NA") # Specified as a list or "NA" if no dependencies

set(EXTENSION_BUILD_SUBDIRECTORY inner-build)
set(SUPERBUILD_TOPLEVEL_PROJECT inner)

#-----------------------------------------------------------------------------
# Extension dependencies
find_package(Slicer REQUIRED)
include(${Slicer_USE_FILE})
mark_as_superbuild(Slicer_DIR)

find_package(Git REQUIRED)
mark_as_superbuild(GIT_EXECUTABLE)

#-----------------------------------------------------------------------------
# SuperBuild setup
option(${EXTENSION_NAME}_SUPERBUILD "Build ${EXTENSION_NAME} and the projects it depends on." ON)
mark_as_superbuild(${EXTENSION_NAME}_SUPERBUILD)
if(${EXTENSION_NAME}_SUPERBUILD)
  include("${CMAKE_CURRENT_SOURCE_DIR}/SuperBuild.cmake")
  return()
endif()

#-----------------------------------------------------------------------------
# Extension modules
add_subdirectory(SlicerSofa)
add_subdirectory(SoftTissueSimulation)
## NEXT_MODULE

#-----------------------------------------------------------------------------
set(EXTENSION_CPACK_INSTALL_CMAKE_PROJECTS)
if(NOT APPLE)
  list(APPEND EXTENSION_CPACK_INSTALL_CMAKE_PROJECTS "${EXTENSION_SUPERBUILD_BINARY_DIR}/GLEW-build;glew;Runtime;/")
endif()
list(APPEND EXTENSION_CPACK_INSTALL_CMAKE_PROJECTS "${Sofa_DIR};Sofa;ALL;/")
set(${EXTENSION_NAME}_CPACK_INSTALL_CMAKE_PROJECTS "${EXTENSION_CPACK_INSTALL_CMAKE_PROJECTS}" CACHE STRING "List of external projects to install" FORCE)

if(APPLE)
  set(EXTENSION_FIXUP_BUNDLE_LIBRARY_DIRECTORIES)

  # GLEW
  set(GLEW_RUNTIME_LIBRARY_DIR "${EXTENSION_SUPERBUILD_BINARY_DIR}/GLEW-install/${Slicer_INSTALL_THIRDPARTY_LIB_DIR}")
  list(APPEND EXTENSION_FIXUP_BUNDLE_LIBRARY_DIRECTORIES ${GLEW_RUNTIME_LIBRARY_DIR})

  set(${EXTENSION_NAME}_FIXUP_BUNDLE_LIBRARY_DIRECTORIES "${EXTENSION_FIXUP_BUNDLE_LIBRARY_DIRECTORIES}" CACHE STRING "List of directories to look up libraries to copy into the application package" FORCE)
endif()

#-----------------------------------------------------------------------------
list(APPEND CPACK_INSTALL_CMAKE_PROJECTS "${CMAKE_BINARY_DIR};${EXTENSION_NAME};ALL;/")
list(APPEND CPACK_INSTALL_CMAKE_PROJECTS "${${EXTENSION_NAME}_CPACK_INSTALL_CMAKE_PROJECTS}")
include(${Slicer_EXTENSION_GENERATE_CONFIG})
include(${Slicer_EXTENSION_CPACK})
