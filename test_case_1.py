import requests
import json

def log_req_response(resp):
	print(">>> {0}".format(resp.request.url + " " + (resp.request.body or "")))
	print("<<< {0}".format(resp.text))

base_url = "http://localhost:8000"

headers = {
    'Content-Type': "application/json",
    'Accept': "*/*",
    'Accept-Encoding': "gzip, deflate",
}

response = requests.request("POST", base_url+"/user/create_application", headers=headers,
	params={"admin_name": "Piyush"})
log_req_response(response)

payload = json.dumps(
	{
		"admin_name": "Piyush",
		"email": "ambuja@gmail.com",
		"user_type": "Processor",
		"password": "ambuja"
	})
response = requests.request("POST", base_url+"/user", data=payload, headers=headers)
log_req_response(response)

payload = json.dumps(
	{
		"admin_name": "Piyush",
		"email": "reliance@gmail.com",
		"user_type": "Processor",
		"password": "reliance"
	})
response = requests.request("POST", base_url+"/user", data=payload, headers=headers)
log_req_response(response)

payload = json.dumps(
	{
		"admin_name": "Piyush",
		"email": "saahas@gmail.com",
		"user_type": "Collector",
		"password": "saahas"
	})
response = requests.request("POST", base_url+"/user", data=payload, headers=headers)
log_req_response(response)

payload = json.dumps(
	{
		"admin_name": "Piyush",
		"email": "wvi@gmail.com",
		"user_type": "Collector",
		"password": "wvi"
	})
response = requests.request("POST", base_url+"/user", data=payload, headers=headers)
log_req_response(response)

payload = json.dumps(
	{
		"admin_name": "Piyush",
		"email": "arun@gmail.com",
		"user_type": "Donor",
		"password": "arun"
	})
response = requests.request("POST", base_url+"/user", data=payload, headers=headers)
log_req_response(response)

payload = json.dumps(
	{
		"admin_name": "Piyush",
		"email": "varun@gmail.com",
		"user_type": "Donor",
		"password": "varun"
	})
response = requests.request("POST", base_url+"/user", data=payload, headers=headers)
log_req_response(response)

response = requests.request("POST", base_url+'/user/list_users', headers=headers,
        params={"admin_name": "Piyush"})
log_req_response(response)

users_dict = response.json()

# Mint coins
payload = json.dumps(
	{
	  "admin_name": "Piyush",
	  "collector_address": users_dict["saahas@gmail.com"]["address"],
	  "processor_address": users_dict["ambuja@gmail.com"]["address"],
	  "token_uri": {
	    "offset_amount": 10.5,
	    "physical_certificate_url": "aws/s3/abc",
	    "recycler_address": "<will_be_auto_filled>",
	    "version": 1
	  }
	})

response = requests.request("POST", base_url+"/plastic_coin", data=payload, headers=headers)
log_req_response(response)

coin_id = response.json()["token_id"]

# Get coin information
response = requests.request("GET", base_url+"/plastic_coin/{0}".format(coin_id),
	headers=headers)
log_req_response(response)

# Split coin
payload = json.dumps(
	{
	  "admin_name": "Piyush",
	  "from_address": users_dict["saahas@gmail.com"]["address"],
	  "share": 5,
	  "to_address": users_dict["varun@gmail.com"]["address"]
	})

response = requests.request("POST", base_url+"/plastic_coin/{0}/send".format(coin_id),
	data=payload, headers=headers)
log_req_response(response)

# Get coin information
response = requests.request("GET", base_url+"/plastic_coin/{0}".format(coin_id),
	headers=headers)
log_req_response(response)

# Filter information for owner
payload = json.dumps(
	{
	  "admin_name": "Piyush",
	  "token_filter": {
	  }
	})

response = requests.request("POST", base_url+"/user/{0}/filter_tokens".format(
	users_dict["varun@gmail.com"]["address"]),
	data=payload,
	headers=headers)
log_req_response(response)