
import urllib.request, json, time

base="http://127.0.0.1:8000"
print(urllib.request.urlopen(base+"/health").read().decode())
print("Start the API, then POST /seed from Swagger.")
