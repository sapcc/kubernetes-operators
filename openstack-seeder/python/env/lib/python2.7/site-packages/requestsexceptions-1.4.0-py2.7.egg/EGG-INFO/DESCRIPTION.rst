requestsexceptions
==================

The python requests library bundles the urllib3 library, however, some
software distributions modify requests to remove the bundled library.
This makes some operations, such as supressing the "insecure platform
warning" messages that urllib emits difficult.  This is a simple
library to find the correct path to exceptions in the requests library
regardless of whether they are bundled.



