include(FetchContent)

FetchContent_Populate(
  qpp
  URL https://quantag-it.com/pub/libs/qpp.tar.gz
  SOURCE_DIR ${CMAKE_SOURCE_DIR}/third_party/qpp
)

FetchContent_Populate(
  json
  URL https://quantag-it.com/pub/libs/json.tar.gz
  SOURCE_DIR ${CMAKE_SOURCE_DIR}/third_party/json
)

FetchContent_Populate(
  eigen
  URL https://quantag-it.com/pub/libs/eigen.tar.gz
  SOURCE_DIR ${CMAKE_SOURCE_DIR}/third_party/eigen
)

FetchContent_Populate(
  boost
  URL https://quantag-it.com/pub/libs/boost.tar.gz
  SOURCE_DIR ${CMAKE_SOURCE_DIR}/third_party/boost
)

FetchContent_Populate(
  openblas
  URL https://quantag-it.com/pub/libs/openblas.tar.gz
  SOURCE_DIR ${CMAKE_SOURCE_DIR}/third_party/openblas
)
