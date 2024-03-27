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
  option(SOFA_ENABLE_VISUALIZATION "Compiles the QT based gui." ON)

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
      -DSOFA_ENABLE_LEGACY_HEADERS:BOOL=OFF
      -DPLUGIN_SOFA_GUI_QT=${SOFA_ENABLE_VISUALIZATION}
      -DSOFA_WITH_OPENGL:BOOL=${SOFA_ENABLE_VISUALIZATION}
      -DSOFA_GUI_QT_ENABLE_QDOCBROWSER:BOOL=OFF
      -DPLUGIN_SOFAMATRIX=OFF
      -DMODULE_SOFA_COMPONENT_HAPTICS=OFF
      -DSOFA_BUILD_TESTS=OFF
      -DSOFA_ROOT:PATH=${EP_SOURCE_DIR}
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
add_custom_target(slicer_${proj}_install ALL
    COMMENT "Installing .so  and python files to ${CMAKE_BINARY_DIR}/${EXTENSION_BUILD_SUBDIRECTORY}/${Slicer_INSTALL_QTLOADABLEMODULES_LIB_DIR}/lib"
)

add_dependencies(slicer_${proj}_install ${proj})

add_custom_command(
    TARGET slicer_${proj}_install POST_BUILD
    COMMAND ${CMAKE_COMMAND} -D LIB_DIR="${SOFA_DIR}/lib" -D CMAKE_BINARY_DIR="${CMAKE_BINARY_DIR}" -D EXTENSION_BUILD_SUBDIRECTORY="${EXTENSION_BUILD_SUBDIRECTORY}" -D Slicer_INSTALL_QTLOADABLEMODULES_LIB_DIR="${Slicer_INSTALL_QTLOADABLEMODULES_LIB_DIR}" -P ${CMAKE_SOURCE_DIR}/cmake/InstallSOFiles.cmake
    COMMENT "Copying SO files..."
)

add_custom_command(
    TARGET slicer_${proj}_install POST_BUILD
    COMMAND ${CMAKE_COMMAND} -D LIB_PYTHON_DIR="${SOFA_DIR}/lib/python3/site-packages" -D CMAKE_BINARY_DIR="${CMAKE_BINARY_DIR}" -D EXTENSION_BUILD_SUBDIRECTORY="${EXTENSION_BUILD_SUBDIRECTORY}" -D Slicer_INSTALL_QTLOADABLEMODULES_LIB_DIR="${Slicer_INSTALL_QTLOADABLEMODULES_LIB_DIR}" -P ${CMAKE_SOURCE_DIR}/cmake/InstallPythonFiles.cmake
    COMMENT "Copying Python directories..."
)
