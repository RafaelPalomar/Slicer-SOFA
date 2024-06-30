set(proj tinyxml2)

# Set dependency list
set(${proj}_DEPENDS
  ""
  )

# Include dependent projects if any
ExternalProject_Include_Dependencies(${proj} PROJECT_VAR proj)

if(${SUPERBUILD_TOPLEVEL_PROJECT}_USE_SYSTEM_${proj})
  message(FATAL_ERROR "Enabling ${SUPERBUILD_TOPLEVEL_PROJECT}_USE_SYSTEM_${proj} is not supported !")
endif()

# Sanity checks
if(DEFINED tinyxml2_DIR AND NOT EXISTS ${tinyxml2_DIR})
  message(FATAL_ERROR "tinyxml2_DIR [${tinyxml2_DIR}] variable is defined but corresponds to nonexistent directory")
endif()

if(NOT DEFINED ${proj}_DIR AND NOT ${SUPERBUILD_TOPLEVEL_PROJECT}_USE_SYSTEM_${proj})

  set(EP_SOURCE_DIR ${CMAKE_BINARY_DIR}/${proj})
  set(EP_BINARY_DIR ${CMAKE_BINARY_DIR}/${proj}-build)

  ExternalProject_Add(${proj}
    ${${proj}_EP_ARGS}
    GIT_REPOSITORY "https://github.com/leethomason/tinyxml2.git"
    GIT_TAG "321ea883b7190d4e85cae5512a12e5eaa8f8731f" #10.0.0-20240313
    SOURCE_DIR ${EP_SOURCE_DIR}
    BINARY_DIR ${EP_BINARY_DIR}
    CMAKE_CACHE_ARGS
      # Compiler settings
      -DCMAKE_C_COMPILER:FILEPATH=${CMAKE_C_COMPILER}
      -DCMAKE_C_FLAGS:STRING=${ep_common_c_flags}
      -DCMAKE_CXX_COMPILER:FILEPATH=${CMAKE_CXX_COMPILER}
      -DCMAKE_CXX_FLAGS:STRING=${ep_common_cxx_flags}
      -DCMAKE_CXX_STANDARD:STRING=${CMAKE_CXX_STANDARD}
      -DCMAKE_CXX_STANDARD_REQUIRED:BOOL=${CMAKE_CXX_STANDARD_REQUIRED}
      -DCMAKE_CXX_EXTENSIONS:BOOL=${CMAKE_CXX_EXTENSIONS}
      # Options
      -DBUILD_TESTING:BOOL=OFF
      -Dtinyxml2_SHARED_LIBS:BOOL=OFF
      -DCMAKE_POSITION_INDEPENDENT_CODE:BOOL=ON
      # Output directory
      -DCMAKE_RUNTIME_OUTPUT_DIRECTORY:PATH=${CMAKE_BINARY_DIR}/${Slicer_THIRDPARTY_BIN_DIR}
      -DCMAKE_LIBRARY_OUTPUT_DIRECTORY:PATH=${CMAKE_BINARY_DIR}/${Slicer_THIRDPARTY_LIB_DIR}
      -DCMAKE_ARCHIVE_OUTPUT_DIRECTORY:PATH=${CMAKE_ARCHIVE_OUTPUT_DIRECTORY}
      # Install directories
      -DCMAKE_INSTALL_LIBDIR:PATH=${Slicer_THIRDPARTY_LIB_DIR}
    DEPENDS
      ${${proj}_DEPENDS}
    INSTALL_COMMAND ""
    )
  set(${proj}_DIR ${EP_BINARY_DIR})

  set(${proj}_INCLUDE_DIR ${EP_SOURCE_DIR})

  if(DEFINED CMAKE_CONFIGURATION_TYPES)
    set(lib_cfg_dir "$<CONFIG>")
  else()
    set(lib_cfg_dir ".")
  endif()
  if(WIN32)
    set(${proj}_LIBRARY ${EP_BINARY_DIR}/${lib_cfg_dir}/tinyxml2.lib)
  else()
    set(${proj}_LIBRARY ${EP_BINARY_DIR}/${lib_cfg_dir}/libtinyxml2.a)
  endif()

else()
  ExternalProject_Add_Empty(${proj} DEPENDS ${${proj}_DEPENDS})
endif()

mark_as_superbuild(${proj}_DIR:PATH)

mark_as_superbuild(
  VARS
    ${proj}_INCLUDE_DIR:PATH
    ${proj}_LIBRARY:FILEPATH
  )
