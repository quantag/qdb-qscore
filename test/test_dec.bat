call set-env

curl -X POST -k -d "{\"src\":\"ZnJvbSBxaXNraXQgaW1wb3J0IHFhc20yCmZyb20gcWlza2l0IGltcG9ydCBRdWFudHVtQ2lyY3VpdApxYyA9IFF1YW50dW1DaXJjdWl0KDIpCnFjLmgoMCkKcWMuY3goMCwgMSkKY29kZTc3Nz1xYXNtMi5kdW1wcyhxYykK\"}"  %BASE_URL%/dec -H "Content-Type:application/json" -H "token:ey"
