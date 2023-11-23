import requests
import json

url = "http://127.0.0.1:5000/assolement"

# Example data to be sent in the request body
data = {
    "type_info": "monochapelle symétrique",
    "lon_serre": 2.35,
    "larg_serre": 10,
    "nbr_chap": 2,
    "LAT": 48.8566,
    "LON": 2.3522,
    "h_serre": None
}

# Convert data to JSON format
json_data = json.dumps(data)

# Set the Content-Type header to indicate JSON data
headers = {'Content-Type': 'application/json'}

# Perform the POST request
response = requests.post(url, data=json_data, headers=headers)

# Print the response from the server
print(response.status_code)
print(response.json())