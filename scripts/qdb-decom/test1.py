# sample_script.py

# This is a simple test script for the Python executor microservice.
# The service will execute this code and then look for a variable named `code777`.
# Whatever value `code777` has will be returned back to the client.

# Do some arbitrary computation so we see that code is really executed
numbers = list(range(1, 11))
squared = [n * n for n in numbers]
total = sum(squared)

message = f"Numbers: {numbers}\nSquared: {squared}\nSum of squares: {total}"

# This is the value your microservice will send back (base64-encoded)
code777 = message
