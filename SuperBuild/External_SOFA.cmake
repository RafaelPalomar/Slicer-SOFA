set(proj SOFA)

# Set dependency list
set(${proj}_DEPENDS
  Boost
  Eigen3
  TinyXML2
  SofaIGTLink
  SofaPython3
  SofaSTLIB
  pybind11
  OpenIGTLink
  )

# Include dependent projects if any
ExternalProject_Include_Dependencies(${proj} PROJECT_VAR proj)

if(${SUPERBUILD_TOPLEVEL_PROJECT}_USE_SYSTEM_${proj})
  message(FATAL_ERROR "Enabling ${SUPERBUILD_TOPLEVEL_PROJECT}_USE_SYSTEM_${proj} is not supported !")
endif()

# Sanity checks
if(DEFINED SOFA_DIR AND NOT EXISTS ${SOFA_DIR})
  message(FATAL_ERROR "SOFA_DIR [${SOFA_DIR}] variable is defined but corresponds to nonexistent directory")
endif()

if(NOT DEFINED ${proj}_DIR AND NOT ${SUPERBUILD_TOPLEVEL_PROJECT}_USE_SYSTEM_${proj})

  set(EP_SOURCE_DIR ${CMAKE_BINARY_DIR}/${proj})
  set(EP_BINARY_DIR ${CMAKE_BINARY_DIR}/${proj}-build)

 list(APPEND CMAKE_EXTERNAL_DIRECTORIES ${SofaIGTLink_DIR})
 list(APPEND CMAKE_EXTERNAL_DIRECTORIES ${SofaPython3_DIR})
 list(APPEND CMAKE_EXTERNAL_DIRECTORIES ${SofaSTLIB_DIR})

  ExternalProject_Add(${proj}
    ${${proj}_EP_ARGS}
    # Note: Update the repository URL and tag to match the correct SOFA version
    GIT_REPOSITORY "https://github.com/sofa-framework/sofa.git"
    GIT_TAG "e4420f49a2fdf36390ac97b3841db430ccbc8143" #master-20240313
    SOURCE_DIR ${EP_SOURCE_DIR}
    BINARY_DIR ${EP_BINARY_DIR}
    CMAKE_CACHE_ARGS
      -DCMAKE_BUILD_TYPE:STRING=${CMAKE_BUILD_TYPE}
      -DCMAKE_C_COMPILER:FILEPATH=${CMAKE_C_COMPILER}
      -DCMAKE_C_FLAGS:STRING=${ep_common_c_flags}
      -DCMAKE_CXX_COMPILER:FILEPATH=${CMAKE_CXX_COMPILER}
      -DCMAKE_CXX_FLAGS:STRING=${ep_common_cxx_flags}
      -DCMAKE_CXX_STANDARD:STRING=${CMAKE_CXX_STANDARD}
      -DCMAKE_CXX_STANDARD_REQUIRED:BOOL=${CMAKE_CXX_STANDARD_REQUIRED}
      -DCMAKE_CXX_EXTENSIONS:BOOL=${CMAKE_CXX_EXTENSIONS}
      -DSOFA_BUILD_TESTS:BOOL=${BUILD_TESTING}
      -DAPPLICATION_RUNSOFA:BOOL=ON
      -DAPPLICATION_SCENECHECKING:BOOL=ON
      -DCOLLECTION_SOFACONSTRAINT:BOOL=ON
      -DCOLLECTION_SOFAGENERAL:BOOL=ON
      -DCOLLECTION_SOFAGRAPHCOMPONENT:BOOL=ON
      -DCOLLECTION_SOFAGUI:BOOL=ON
      -DCOLLECTION_SOFAGUICOMMON:BOOL=ON
      -DCOLLECTION_SOFAGUIQT:BOOL=ON
      -DCOLLECTION_SOFAMISCCOLLISION:BOOL=ON
      -DCOLLECTION_SOFAUSERINTERACTION:BOOL=ON
      -DSOFA_GUI_QT_ENABLE_QDOCBROWSER:BOOL=OFF
      -#DSofaPython3_ENABLED:BOOL=ON
      -DSofaSTLIB_ENABLED:BOOL=ON
      -DLIBRARY_SOFA_GUI:BOOL=ON
      -DLIBRARY_SOFA_GUI_COMMON:BOOL=ON
      -DMODULE_SOFA_GUI_COMPONENT:BOOL=ON
      -DPLUGIN_SOFA_GUI_BATCH:BOOL=ON
      -DPLUGIN_SOFA_GUI_QT:BOOL=ON
      -DSOFA_ROOT:PATH=${EP_SOURCE_DIR}
      -DSOFA_WITH_OPENGL:BOOL=ON
      -DBoost_INCLUDE_DIR:PATH=${Boost_DIR}/include
      -DEIGEN3_INCLUDE_DIR:PATH=${Eigen3_DIR}/include/eigen3
      -DTinyXML2_INCLUDE_DIR:PATH=${TinyXML2_DIR}/../TinyXML2
      -DTinyXML2_LIBRARY:PATH=${TinyXML2_DIR}/libtinyxml2.so.10
      -DSOFA_EXTERNAL_DIRECTORIES:STRING=${CMAKE_EXTERNAL_DIRECTORIES}
      -DPYTHON_EXECUTABLE:FILEPATH=${PYTHON_EXECUTABLE}
      -DPython3_EXECUTABLE:FILEPATH=${PYTHON_EXECUTABLE}
      -DPython_EXECUTABLE:FILEPATH=${PYTHON_EXECUTABLE}
      -DPYTHON_LIBRARIES:FILEPATH=${PYTHON_LIBRARY}
      -DPYTHON_INCLUDE_DIRS:PATH=${PYTHON_INCLUDE_DIR}
      -Dpybind11_DIR:PATH=${pybind11_DIR}/share/cmake/pybind11
      -DOpenIGTLink_DIR:PATH=${OpenIGTLink_DIR}
    DEPENDS
      ${${proj}_DEPENDS}
    INSTALL_COMMAND ""
    )
  set(${proj}_DIR ${EP_BINARY_DIR})

else()
  ExternalProject_Add_Empty(${proj} DEPENDS ${${proj}_DEPENDS})
endif()

mark_as_superbuild(${proj}_DIR:PATH)


# Add a custom target that depends on the external project
add_custom_target(${proj}_install_so_files ALL
    COMMENT "Installing .so files to ${CMAKE_BINARY_DIR}/${EXTENSION_BUILD_SUBDIRECTORY}/${Slicer_INSTALL_QTLOADABLEMODULES_LIB_DIR}/lib"
)

# Add dependencies to ensure this target is built after the external project
add_dependencies(${proj}_install_so_files ${proj})

# Command to create the installation directory (if it does not exist)
add_custom_command(TARGET ${proj}_install_so_files PRE_BUILD
    COMMAND ${CMAKE_COMMAND} -E make_directory ${CMAKE_BINARY_DIR}/${EXTENSION_BUILD_SUBDIRECTORY}/${Slicer_INSTALL_QTLOADABLEMODULES_LIB_DIR}/lib
)

# Installation of SOFA files
file(GLOB_RECURSE SO_FILES "${SOFA_DIR}/lib/*.so*")
foreach(SO_FILE IN LISTS SO_FILES)
    add_custom_command(TARGET ${proj}_install_so_files POST_BUILD
        COMMAND ${CMAKE_COMMAND} -E copy_if_different ${SO_FILE} ${CMAKE_BINARY_DIR}/${EXTENSION_BUILD_SUBDIRECTORY}/${Slicer_INSTALL_QTLOADABLEMODULES_LIB_DIR}/lib
        COMMENT "Copying ${SO_FILE} to ${CMAKE_BINARY_DIR}/${EXTENSION_BUILD_SUBDIRECTORY}/${Slicer_INSTALL_QTLOADABLEMODULES_LIB_DIR}/lib"
    )
endforeach()

# Create the destination directory if it doesn't exist
add_custom_command(TARGET ${proj}_install_so_files PRE_BUILD
    COMMAND ${CMAKE_COMMAND} -E make_directory  "${CMAKE_BINARY_DIR}/${EXTENSION_BUILD_SUBDIRECTORY}/${Slicer_INSTALL_QTLOADABLEMODULES_LIB_DIR}/Python"
)

set(SOFA_PYTHON_DIR ${SOFA_DIR}/lib/python3/site-packages)
# Get all subdirectories within the sofa python3 directory
file(GLOB CHILDREN RELATIVE ${SOFA_PYTHON_DIR} ${SOFA_PYTHON_DIR}/*)
foreach(child ${CHILDREN})
    if(IS_DIRECTORY ${SOFA_PYTHON_DIR}/${child})
        # Define the source subdirectory and the corresponding destination
        set(SOURCE_SUBDIR ${SOFA_PYTHON_DIR}/${child})
        set(DEST_SUBDIR  ${CMAKE_BINARY_DIR}/${EXTENSION_BUILD_SUBDIRECTORY}/${Slicer_INSTALL_QTLOADABLEMODULES_LIB_DIR}/Python/${child})

        # Copy the subdirectory
        add_custom_command(TARGET ${proj}_install_so_files POST_BUILD
            COMMAND ${CMAKE_COMMAND} -E echo "Copying ${SOURCE_SUBDIR} to ${DEST_SUBDIR}"
            COMMAND ${CMAKE_COMMAND} -E copy_directory ${SOURCE_SUBDIR} ${DEST_SUBDIR}
            COMMENT "Copying subdirectory ${child} to ${DEST_SUBDIR}"
        )
    endif()
endforeach()
