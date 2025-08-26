import cudaq

@cudaq.kernel
def bell():
    q = cudaq.qvector(2)
    cudaq.h(q[0])
    cudaq.cx(q[0], q[1])

