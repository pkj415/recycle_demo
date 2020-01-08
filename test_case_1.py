import requests
import json

def log_req_response(resp):
	print(">>> {0}".format(resp.request.url + " " + (resp.request.body or "")))
	print("<<< {0}".format(resp.text))

import sys
base_url = sys.argv[1]

headers = {
    'Content-Type': "application/json",
    'Accept': "*/*",
    'Accept-Encoding': "gzip, deflate",
}

response = requests.request("POST", base_url+"/appl/create_application", headers=headers,
	params={"admin_name": "Piyush"})
log_req_response(response)

response = requests.request("GET", base_url+"/appl/" + "Piyush", headers=headers)
log_req_response(response)

payload = json.dumps(
	{
		"admin_name": "Piyush",
		"email": "ambuja@gmail.com",
		"password": "ambuja",
		"has_minting_right": True
	})
response = requests.request("POST", base_url+"/user", data=payload, headers=headers)
ambuja_address = response.json()["public_key"]

log_req_response(response)

payload = json.dumps(
	{
		"admin_name": "Piyush",
		"email": "reliance@gmail.com",
		"password": "reliance",
		"has_minting_right": True
	})
response = requests.request("POST", base_url+"/user", data=payload, headers=headers)
reliance_address = response.json()["public_key"]
log_req_response(response)

payload = json.dumps(
	{
		"admin_name": "Piyush",
		"email": "saahas@gmail.com",
		"password": "saahas",
		"has_minting_right": False
	})
response = requests.request("POST", base_url+"/user", data=payload, headers=headers)
saahas_address = response.json()["public_key"]
log_req_response(response)

payload = json.dumps(
	{
		"admin_name": "Piyush",
		"email": "wvi@gmail.com",
		"password": "wvi",
		"has_minting_right": False
	})
response = requests.request("POST", base_url+"/user", data=payload, headers=headers)
wvi_address = response.json()["public_key"]
log_req_response(response)

payload = json.dumps(
	{
		"admin_name": "Piyush",
		"email": "arun@gmail.com",
		"password": "arun",
		"has_minting_right": False
	})
response = requests.request("POST", base_url+"/user", data=payload, headers=headers)
arun_address = response.json()["public_key"]
log_req_response(response)

payload = json.dumps(
	{
		"admin_name": "Piyush",
		"email": "varun@gmail.com",
		"password": "varun",
		"has_minting_right": False
	})
response = requests.request("POST", base_url+"/user", data=payload, headers=headers)
varun_address = response.json()["public_key"]
log_req_response(response)

response = requests.request("POST", base_url+'/user/list_users', headers=headers,
	params={"admin_name": "Piyush"})
log_req_response(response)

# Mint coins
payload = json.dumps(
	{
		"admin_name": "Piyush",
		"destination_address": saahas_address,
		"source_address": ambuja_address,
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

resp_json = response.json()
# assert(resp_json[])

# Split coin
payload = json.dumps(
	{
		"admin_name": "Piyush",
		"from_address": saahas_address,
		"share": 5,
		"to_address": varun_address
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
	varun_address),
	data=payload,
	headers=headers)
log_req_response(response)