cmake_minimum_required(VERSION 3.16.0 FATAL_ERROR)

set(CMAKE_SYSTEM_VERSION 10.0 CACHE STRING "" FORCE)
project(QSCore CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

set(COMMON_OPT_FLAGS "-O3 -mcpu=neoverse-v2 -fopenmp")
set(CMAKE_C_COMPILER gcc)
set(CMAKE_CXX_COMPILER g++)

set(CMAKE_THREAD_LIBS_INIT "-lpthread")
set(CMAKE_HAVE_THREADS_LIBRARY 1)
set(CMAKE_USE_WIN32_THREADS_INIT 0)
set(CMAKE_USE_PTHREADS_INIT 1)
set(THREADS_PREFER_PTHREAD_FLAG ON)


if(DEFINED ARMPL AND ARMPL STREQUAL "ON")  # -DARMPL=ON
  message(STATUS "Use ARM HPC compiler and ArmPL if available")
  find_program(ARM_C_COMPILER armclang)
  find_program(ARM_CXX_COMPILER armclang++)
  if(ARM_C_COMPILER AND ARM_CXX_COMPILER)
      message(STATUS "Found Arm Compiler: ${ARM_CXX_COMPILER}")
      set(CMAKE_C_COMPILER ${ARM_C_COMPILER})
      set(CMAKE_CXX_COMPILER ${ARM_CXX_COMPILER})
   else()
      message(STATUS "Arm Compiler not found. Falling back to GCC.")
  endif()
endif() # if -DARMPL

set(CMAKE_C_FLAGS "${COMMON_OPT_FLAGS}")
set(CMAKE_CXX_FLAGS "${COMMON_OPT_FLAGS}")

################################################################################
# Set target arch type if empty. Visual studio solution generator provides it.
################################################################################
if(NOT CMAKE_VS_PLATFORM_NAME)
    set(CMAKE_VS_PLATFORM_NAME "x64")
endif()
# message("${CMAKE_VS_PLATFORM_NAME} architecture in use")

if(NOT ("${CMAKE_VS_PLATFORM_NAME}" STREQUAL "x64"
     OR "${CMAKE_VS_PLATFORM_NAME}" STREQUAL "x86"))
    message(FATAL_ERROR "${CMAKE_VS_PLATFORM_NAME} arch is not supported!")
endif()

################################################################################
# Global configuration types
################################################################################
set(CMAKE_CONFIGURATION_TYPES
    "Debug"
    "Release"
    CACHE STRING "" FORCE
)

################################################################################
# Global compiler options
################################################################################
if(MSVC)
    # remove default flags provided with CMake for MSVC
    set(CMAKE_CXX_FLAGS "")
    set(CMAKE_CXX_FLAGS_DEBUG "")
    set(CMAKE_CXX_FLAGS_RELEASE "")
endif()

################################################################################
# Global linker options
################################################################################
if(MSVC)
    # remove default flags provided with CMake for MSVC
    set(CMAKE_EXE_LINKER_FLAGS "")
    set(CMAKE_MODULE_LINKER_FLAGS "")
    set(CMAKE_SHARED_LINKER_FLAGS "")
    set(CMAKE_STATIC_LINKER_FLAGS "")
    set(CMAKE_EXE_LINKER_FLAGS_DEBUG "${CMAKE_EXE_LINKER_FLAGS}")
    set(CMAKE_MODULE_LINKER_FLAGS_DEBUG "${CMAKE_MODULE_LINKER_FLAGS}")
    set(CMAKE_SHARED_LINKER_FLAGS_DEBUG "${CMAKE_SHARED_LINKER_FLAGS}")
    set(CMAKE_STATIC_LINKER_FLAGS_DEBUG "${CMAKE_STATIC_LINKER_FLAGS}")
    set(CMAKE_EXE_LINKER_FLAGS_RELEASE "${CMAKE_EXE_LINKER_FLAGS}")
    set(CMAKE_MODULE_LINKER_FLAGS_RELEASE "${CMAKE_MODULE_LINKER_FLAGS}")
    set(CMAKE_SHARED_LINKER_FLAGS_RELEASE "${CMAKE_SHARED_LINKER_FLAGS}")
    set(CMAKE_STATIC_LINKER_FLAGS_RELEASE "${CMAKE_STATIC_LINKER_FLAGS}")
endif()

################################################################################
# Nuget packages function stub.
################################################################################
function(use_package TARGET PACKAGE VERSION)
    message(WARNING "No implementation of use_package. Create yours. "
                    "Package \"${PACKAGE}\" with version \"${VERSION}\" "
                    "for target \"${TARGET}\" is ignored!")
endfunction()

################################################################################
# Common utils
################################################################################
include(CMake/Utils.cmake)

################################################################################
# Additional Global Settings(add specific info there)
################################################################################
include(CMake/GlobalSettingsInclude.cmake OPTIONAL)

################################################################################
# Use solution folders feature
################################################################################
set_property(GLOBAL PROPERTY USE_FOLDERS ON)

# option(USE_OPENBLAS, "Enable OpenBLAS libraries" ON)
# set_directory_properties(PROPERTIES CLEAN_NO_CUSTOM TRUE)

################################################################################
# Source groups
################################################################################
set(Header_Files
    "ConfigLoader.h"
    "Debugger.h"
    "Event.h"
    "Log.h"
    "PythonProcessor.h"
    "QiskitProcessor.h"
    "RestClient.h"
    "SessionStorage.h"
    "TketProcessor.h"
    "Typedefs.h"
    "Utils.h"
    "WebFrontend.h"
)
source_group("Header Files" FILES ${Header_Files})

set(Header_Files__interfaces
    "interfaces/iqvm.h"
)
source_group("Header Files\\interfaces" FILES ${Header_Files__interfaces})

find_package(CURL REQUIRED)

set(Source_Files
    "Debugger.cpp"
    "Log.cpp"
    "Event.cpp"
    "QSCore.cpp"
    "Utils.cpp"
    "WebFrontend.cpp"
    "PythonProcessor.cpp"
    "QiskitProcessor.cpp"
    "TketProcessor.cpp"
    "RestClient.cpp"
    "SessionStorage.cpp"
    "ws/WSServer.cpp"
    "ws/WSListener.cpp"    
    "ws/WSSession.cpp"
    "qvm/QppQVM.cpp"
    "dap/content_stream.cpp"
    "dap/network.cpp"
    "dap/io.cpp"
    "dap/nlohmann_json_serializer.cpp"
    "dap/null_json_serializer.cpp"
    "dap/protocol_types.cpp"
    "dap/protocol_events.cpp"
    "dap/protocol_requests.cpp"
    "dap/protocol_response.cpp"
    "dap/socket.cpp"
    "dap/protocol_types.cpp"
    "dap/session.cpp"
    "dap/typeinfo.cpp"
    "dap/typeof.cpp"
    "dap/Impl.cpp"
)
source_group("Source Files" FILES ${Source_Files})

set(ALL_FILES
    ${Header_Files}
    ${Header_Files__interfaces}
    ${Source_Files}
)

################################################################################
# Target
################################################################################
add_executable(${PROJECT_NAME} ${ALL_FILES})

use_props(${PROJECT_NAME} "${CMAKE_CONFIGURATION_TYPES}" "${DEFAULT_CXX_PROPS}")
set(ROOT_NAMESPACE TcpStreamServer)

set_target_properties(${PROJECT_NAME} PROPERTIES
    VS_GLOBAL_KEYWORD "Win32Proj"
)
if("${CMAKE_VS_PLATFORM_NAME}" STREQUAL "x64")
    set_target_properties(${PROJECT_NAME} PROPERTIES
        INTERPROCEDURAL_OPTIMIZATION_RELEASE "TRUE"
    )
elseif("${CMAKE_VS_PLATFORM_NAME}" STREQUAL "x86")
    set_target_properties(${PROJECT_NAME} PROPERTIES
        INTERPROCEDURAL_OPTIMIZATION_RELEASE "TRUE"
    )
endif()
################################################################################
# Include directories
################################################################################
include_directories(${CURL_INCLUDE_DIR})

target_include_directories(${PROJECT_NAME} PUBLIC
            "${CMAKE_CURRENT_SOURCE_DIR}/third_party/boost/include/boost-1_82;"
            "${CMAKE_CURRENT_SOURCE_DIR}/third_party/json/include;"
            "${CMAKE_CURRENT_SOURCE_DIR}/third_party/qpp/include;"
            "${CMAKE_CURRENT_SOURCE_DIR}/third_party/eigen;"
            "${CMAKE_CURRENT_SOURCE_DIR}/third_party/qasmtools/include"
)

################################################################################
# Compile definitions
################################################################################
if("${CMAKE_VS_PLATFORM_NAME}" STREQUAL "x64")
    target_compile_definitions(${PROJECT_NAME} PRIVATE
        #"$<$<CONFIG:Debug>:"
            "CPPDAP_JSON_NLOHMANN"
            "_CRT_SECURE_NO_WARNINGS"
            "_WINSOCK_DEPRECATED_NO_WARNINGS"
       # ">"
        "$<$<CONFIG:Release>:"
            "NDEBUG"
        ">"
        "_CONSOLE;"
        "UNICODE;"
        "_UNICODE"
    )
elseif("${CMAKE_VS_PLATFORM_NAME}" STREQUAL "x86")
    target_compile_definitions(${PROJECT_NAME} PRIVATE
        "$<$<CONFIG:Debug>:"
            "_DEBUG"
        ">"
        "$<$<CONFIG:Release>:"
            "NDEBUG"
        ">"
        "WIN32;"
        "_CONSOLE;"
        "UNICODE;"
        "_UNICODE"
    )
endif()

################################################################################
# Compile and link options
################################################################################
if(MSVC)
    if("${CMAKE_VS_PLATFORM_NAME}" STREQUAL "x64")
        target_compile_options(${PROJECT_NAME} PRIVATE
            $<$<CONFIG:Debug>:
                /std:c++17
                /bigobj
            >
            $<$<CONFIG:Release>:
                /Oi;
                /Gy
            >
            /permissive-;
            /sdl;
            /W3;
            ${DEFAULT_CXX_DEBUG_INFORMATION_FORMAT};
            ${DEFAULT_CXX_EXCEPTION_HANDLING}
        )

    elseif("${CMAKE_VS_PLATFORM_NAME}" STREQUAL "x86")
        target_compile_options(${PROJECT_NAME} PRIVATE
            $<$<CONFIG:Release>:
                /Oi;
                /Gy
            >
            /permissive-;
            /sdl;
            /W3;
            ${DEFAULT_CXX_DEBUG_INFORMATION_FORMAT};
            ${DEFAULT_CXX_EXCEPTION_HANDLING}
        )
    endif()
    if("${CMAKE_VS_PLATFORM_NAME}" STREQUAL "x64")
        target_link_options(${PROJECT_NAME} PRIVATE
            $<$<CONFIG:Release>:
                /OPT:REF;
                /OPT:ICF
            >
            /DEBUG;
            /SUBSYSTEM:CONSOLE
        )
    elseif("${CMAKE_VS_PLATFORM_NAME}" STREQUAL "x86")
        target_link_options(${PROJECT_NAME} PRIVATE
            $<$<CONFIG:Release>:
                /OPT:REF;
                /OPT:ICF
            >
            /DEBUG;
            /SUBSYSTEM:CONSOLE
        )
    endif()
endif()

find_package(OpenMP)
if (OPENMP_FOUND)
    message(STATUS "OpenMP found")
    set (CMAKE_C_FLAGS "${CMAKE_C_FLAGS} ${OpenMP_C_FLAGS}")
    set (CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} ${OpenMP_CXX_FLAGS}")
    set (CMAKE_EXE_LINKER_FLAGS "${CMAKE_EXE_LINKER_FLAGS} ${OpenMP_EXE_LINKER_FLAGS}")

  if(DEFINED ENV{NVPL_ROOT})
     get_filename_component(NVPL_ROOT_ENV $ENV{NVPL_ROOT} ABSOLUTE)
     message(STATUS "Using NVPL_ROOT: ${NVPL_ROOT_ENV}")

     set(NVPL_LIB_PATH "${NVPL_ROOT_ENV}/lib")
     set(NVPL_INC_PATH "${NVPL_ROOT_ENV}/include")
     add_compile_definitions(NVPL_ENABLED)

     include_directories(${NVPL_INC_PATH})
     link_directories(${NVPL_LIB_PATH})

    find_library(NVPL_BLAS_LIBRARY nvpl_blas_ilp64_gomp HINTS ${NVPL_LIB_PATH} )
    if(NVPL_BLAS_LIBRARY)
        message(STATUS "Found NVPL BLAS library: ${NVPL_BLAS_LIBRARY}")
        target_link_libraries(${PROJECT_NAME} PRIVATE ${NVPL_BLAS_LIBRARY})
    else()
        message(STATUS "NVPL BLAS library not found in ${NVPL_LIB}")
    endif()

  else() # NVPL_ROOT not defined
     message(STATUS "NVPL_ROOT is not set in the environment. LD_LIBRARY_PATH: '${LD_LIBRARY_PATH}'")

     if(DEFINED ARMPL AND ARMPL STREQUAL "ON" AND DEFINED ENV{LD_LIBRARY_PATH})
           get_filename_component(ARMPL_LIB_PATH $ENV{LD_LIBRARY_PATH} ABSOLUTE)
           find_library(ARMPL_BLAS_LIBRARY armpl_ilp64_mp HINTS ${ARMPL_LIB_PATH} )
     endif()

     if(DEFINED ARMPL AND ARMPL STREQUAL "ON" AND ARMPL_BLAS_LIBRARY)
         message(STATUS "Found ArmPL BLAS library: ${ARMPL_BLAS_LIBRARY}")
 
        target_link_libraries(${PROJECT_NAME} PRIVATE ${ARMPL_BLAS_LIBRARY})

     else()
         message(STATUS "ArmPL disabled or ArmPL-BLAS library not found in ${ARMPL_LIB_PATH}")
         find_package(BLAS REQUIRED)

         message(STATUS "Building using BLAS libraries")
         target_link_libraries(${PROJECT_NAME} PRIVATE ${BLAS_LIBRARIES} )
     endif()
  endif() # if NVPL_ROOT defined

  add_compile_definitions(QPP_OPENMP)

else()  # no OpenMP
      message(STATUS "OpenMP not found")
endif()

add_compile_definitions(EIGEN_USE_BLAS)
target_link_libraries(${PROJECT_NAME} PRIVATE ${CURL_LIBRARIES} )
target_compile_features(${PROJECT_NAME} PRIVATE cxx_std_17)
set_target_properties( ${PROJECT_NAME} PROPERTIES CXX_STANDARD 17)
set(THREADS_PREFER_PTHREAD_FLAG ON)

find_package(Threads REQUIRED)

target_link_libraries(${PROJECT_NAME} PRIVATE Threads::Threads)
