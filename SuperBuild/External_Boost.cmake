set(proj Boost)

# Set dependency list
set(${proj}_DEPENDS
  ""
)

# Include dependent projects if any
ExternalProject_Include_Dependencies(${proj} PROJECT_VAR proj)

if(${SUPERBUILD_TOPLEVEL_PROJECT}_USE_SYSTEM_${proj})
  message(FATAL_ERROR "Enabling ${SUPERBUILD_TOPLEVEL_PROJECT}_USE_SYSTEM_${proj} is not supported!")
endif()

# Sanity checks
if(DEFINED Boost_DIR AND NOT EXISTS ${Boost_DIR})
  message(FATAL_ERROR "Boost_DIR [${Boost_DIR}] variable is defined but corresponds to nonexistent directory")
endif()

if(NOT DEFINED ${proj}_DIR AND NOT ${SUPERBUILD_TOPLEVEL_PROJECT}_USE_SYSTEM_${proj})

  set(EP_SOURCE_DIR ${CMAKE_BINARY_DIR}/${proj})
  set(EP_BINARY_DIR ${CMAKE_BINARY_DIR}/${proj}-build)
  set(EP_INSTALL_DIR ${CMAKE_BINARY_DIR}/${proj}-install)

  set(_version "1.84.0")
  set(BOOST_URL "https://github.com/boostorg/boost/releases/download/boost-${_version}/boost-${_version}.tar.gz")
  set(BOOST_URL_HASH "SHA256=4d27e9efed0f6f152dc28db6430b9d3dfb40c0345da7342eaa5a987dde57bd95") # Replace <expected hash value> with the actual SHA256 hash of the tar.gz file

  if(WIN32)
    set(BUILD_COMMAND ${EP_SOURCE_DIR}/bootstrap.bat)
  else()
    set(BUILD_COMMAND ${EP_SOURCE_DIR}/bootstrap.sh)
  endif()

  set(EXTERNAL_PROJECT_OPTIONAL_ARGS)
  if(CMAKE_VERSION VERSION_GREATER_EQUAL "3.24")
    list(APPEND EXTERNAL_PROJECT_OPTIONAL_ARGS
      DOWNLOAD_EXTRACT_TIMESTAMP 1
      )
  endif()

  ExternalProject_Add(${proj}
    ${EXTERNAL_PROJECT_OPTIONAL_ARGS}
    URL ${BOOST_URL}
    URL_HASH ${BOOST_URL_HASH}
    DOWNLOAD_DIR ${CMAKE_BINARY_DIR}/download
    SOURCE_DIR ${EP_SOURCE_DIR}
    UPDATE_COMMAND ""
    CONFIGURE_COMMAND ""
    BUILD_COMMAND ${BUILD_COMMAND}
    INSTALL_COMMAND ${EP_SOURCE_DIR}/b2 --prefix=${EP_INSTALL_DIR} install
    BUILD_IN_SOURCE 1
    DEPENDS
      ${${proj}_DEPENDS}
  )
  set(${proj}_DIR ${EP_INSTALL_DIR}/lib/cmake/Boost-${_version}/)

else()
  ExternalProject_Add_Empty(${proj} DEPENDS ${${proj}_DEPENDS})
endif()

mark_as_superbuild(${proj}_DIR:PATH)
