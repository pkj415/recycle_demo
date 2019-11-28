from flask import Flask, request, Response
from flask_restplus import Resource, fields, reqparse, Api
import logging
import requests
from solc import compile_standard
import json
import sha3
from web3 import Web3
from werkzeug.exceptions import BadRequest

import os

app = Flask(__name__)
api = Api(app, version="1.0", title="rePurpose Plastic token")

plastic_coin = api.namespace('plastic_coin', description='Plastic coin entity')
transaction = api.namespace('transaction', description='Monitor transactions')
user = api.namespace('user', description='User management')
ps = api.namespace('processor', description='Operations available to processor')

create_application_instance = reqparse.RequestParser()
create_application_instance.add_argument('admin_name', required=True, default="Piyush",
    help='Admin name instance', location='args')

application_instance = {}

def get_token_id(token_uri):
    return int.from_bytes(sha3.keccak_256(token_uri.encode('utf-8')).digest(), byteorder="big", signed=False)

class Application():
    def __init__(self):
        self.user_map = {}
        self.address_user_map = {}
        w3 = Web3(Web3.HTTPProvider("http://localhost:8545"))
        self.owner_account = w3.eth.accounts[0]
        self.contract_address = ""

    def create_account(self, password):
        print("------------- Create account -------------")
        w3 = Web3(Web3.HTTPProvider("http://localhost:8545"))
        address = w3.geth.personal.newAccount(password)
        # Bug in ganache-cli, doesn't accept two arguments, duration=None also doesn't work

        print("Created address {0}".format(address))
        gasLimit = 3000000;
        w3.geth.personal.unlockAccount(address, password, None)
        transaction = {
          "from": w3.eth.accounts[0],
          # "nonce": web3.toHex(1),
          # "gasPrice": w3.toHex(w3.eth.gasPrice * 1e9),
          "gasLimit": w3.toHex(gasLimit),
          "to": address,
          "value": w3.toWei(10,'ether'),
          # "private_key":
          # "chainId": 4 //remember to change this
        }
        # signed_txn = w3.eth.account.signTransaction()

            # var privKey = new Buffer(privateKey, 'hex');
            # var tx = new Tx(rawTransaction);

            # tx.sign(privKey);
            # var serializedTx = tx.serialize();

            # web3.eth.sendRawTransaction('0x' + serializedTx.toString('hex'), function(err, hash) {
            #   if (!err)
            #       {
            #         console.log('Txn Sent and hash is '+hash);
            #       }
            #   else
            #       {
            #         console.error(err);
            #       }
            # });

        # signed_txn = w3.eth.account.signTransaction(dict(
        #     gasPrice = w3.eth.gasPrice, 
        #     gas = 100000,
        #     to=address,
        #     value=web3.toWei(10,'ether')
        #   ))

        w3.eth.sendTransaction(transaction)

        return address

    def add_party(self, party_name, type, password):
        print("------------- Create user -------------")
        if party_name in self.user_map:
            raise BadRequest("This party already exists")

        w3 = Web3(Web3.HTTPProvider("http://localhost:8545"))
        address = self.create_account(password)
        self.user_map[party_name] = {
            "type": type,
            "address": address
        }

        self.address_user_map[address] = party_name
        if type == "Processor":
            processor_address = self.user_map[party_name]["address"]
            print("Processor address {0}".format(processor_address))

            w3.eth.defaultAccount = self.owner_account
            bytecode, abi = compile_contract(['PlasticCoin.sol'], 'PlasticCoin.sol', 'PlasticCoin')
            # bytecode, abi = compile_contract(['Recycle.sol', 'ERC223.sol', 'IERC223.sol', 'ERC223Mintable.sol', 'Address.sol', 'SafeMath.sol', 'IERC223Recipient.sol'], 'ERC223Mintable.sol', 'ERC223Mintable')

            print("Adding as minter to contract address {0}".format(self.contract_address))
            # print("Code at contract address {0} is {1}".format(self.contract_address, w3.eth.getCode(self.contract_address)))
            RecycleContract = w3.eth.contract(address=self.contract_address, abi=abi, bytecode=bytecode)

            tx_hash = RecycleContract.functions.addMinter(processor_address).transact()

            tx_receipt = w3.eth.waitForTransactionReceipt(tx_hash)
            print(tx_receipt)

    def validate_party(self, party, type):
        if party not in self.user_map:
            raise BadRequest("No party with name {0}".format(party))

        if self.user_map[party]["type"] != type:
            raise BadRequest("{0} is not a {1}".format(party, type))

@user.route('/create_application')    
class CreateApplication(Resource):

    @api.expect(create_application_instance)
    def post(self):
        print("------------- Create application -------------")
        global application_instance
        args = create_application_instance.parse_args(request)
        admin_name = args.get('admin_name')
        print("Creating instance for {0}".format(admin_name))

        if admin_name in application_instance:
            raise BadRequest("This instance already exists")

        w3 = Web3(Web3.HTTPProvider("http://localhost:8545"))
        w3.eth.defaultAccount = w3.eth.accounts[0]

        bytecode, abi = compile_contract(['PlasticCoin.sol'], 'PlasticCoin.sol', 'PlasticCoin')

        RecycleContract = w3.eth.contract(abi=abi, bytecode=bytecode)

        print("Bytecode {0}".format(bytecode))
        RecycleContract = w3.eth.contract(abi=abi, bytecode=bytecode)

        tx_hash = RecycleContract.constructor().transact()

        tx_receipt = w3.eth.waitForTransactionReceipt(tx_hash)
        print(tx_receipt)
        contract_address = tx_receipt.contractAddress
        print("Created contract address {0}".format(contract_address))

        application_instance[admin_name] = Application()
        application_instance[admin_name].contract_address = contract_address

create_user = api.model('create_user', {
    'admin_name': fields.String(required=True, description='Admin name', default="Piyush"),
    'password': fields.String(required=True, default="rePurpose1234", description='Password'),
    'phone': fields.String(default="1-XXX-XXXXXXX", description='Phone number'),
    'email': fields.String(required=True, default="josh@gmail.com", description='Email'),
    'user_type': fields.String(choices=("Processor", "Collector", "Donor"), help='Type of user')
})

@user.route('')
class CreateUser(Resource):
    @api.expect(create_user)
    def post(self):
        global application_instance
        admin_name = request.json.get('admin_name')
        email = request.json.get('email')
        password = request.json.get('password')
        phone = request.json.get('phone')
        user_type = request.json.get('user_type')

        print("Adding user {0}".format(request.json))

        if admin_name not in application_instance:
            raise BadRequest("No instance exists for {0}".format(admin_name))

        app = application_instance[admin_name]
        app.add_party(email, user_type, password)

        resp = Response(
            json.dumps({"public_key": app.user_map[email]["address"]}),
            status=200, mimetype='application/json')

list_users_request = reqparse.RequestParser()
list_users_request.add_argument('admin_name', required=True, default="Piyush",
    help='Admin name', location='args')

@user.route('/list_users')
class ListParties(Resource):
    @api.expect(list_users_request)
    def post(self):
        global application_instance
        args = list_users_request.parse_args(request)
        admin_name = args.get('admin_name')
        
        if admin_name not in application_instance:
            raise BadRequest("No instance exists for {0}".format(admin_name))

        app = application_instance[admin_name]
        contract_address = app.contract_address

        return app.user_map

filter_tokens_request = api.model('filter_tokens_request', {
    'admin_name': fields.String(required=True, description='Admin name', default="Piyush"),
    'token_filter': fields.Nested(api.model('filter', {
        'version': fields.Integer(required=False, default=1, description='Version of the URI'),
        'recycler_address': fields.String(required=False, default="0x1F0a4a146776ECC2a3e52F6700901b51aE528bBC", description='Address of recycler'),
    }))
})

@user.route('/<string:address>/filter_tokens')
class FilterTokens(Resource):
    @api.expect(filter_tokens_request)
    def post(self, address):
        global application_instance
        print("------------- Filter Coins -------------")
        # print("Params - {0}".format(request.json))
        admin_name = request.json.get('admin_name')
        token_filter = request.json.get('token_filter')

        # TODO: Implement the token filters
        
        if admin_name not in application_instance:
            raise BadRequest("No instance exists for {0}".format(admin_name))

        app = application_instance[admin_name]
        contract_address = app.contract_address

        w3 = Web3(Web3.HTTPProvider("http://localhost:8545"))
        bytecode, abi = compile_contract(['PlasticCoin.sol'], 'PlasticCoin.sol', 'PlasticCoin')

        RecycleContract = w3.eth.contract(address=contract_address, abi=abi, bytecode=bytecode)

        token_ids = RecycleContract.functions.getOwnerTokens(address).call()
        print("Token ids - {0}".format(token_ids))

        resp = []
        for token_id in token_ids:
            token_uri = RecycleContract.functions.tokenURI(token_id).call()
            resp.append({
                "token_uri": json.loads(token_uri),
                "share": RecycleContract.functions.getTokenShare(token_id, address).call()
            })

            resp[-1]["token_uri"]["recycler"] = app.address_user_map[
                resp[-1]["token_uri"]["recycler_address"]]


        resp_json = json.dumps(resp)
        print("Resp json - {0}".format(resp_json))

        return Response(
            resp_json,
            status=200, mimetype='application/json')

mint_request = api.model('mint_request', {
    'admin_name': fields.String(required=True, description='Admin name', default="Piyush"),
    'processor_address': fields.String(required=True, default="0x1F0a4a146776ECC2a3e52F6700901b51aE528bBC", description='Minter address'),
    'collector_address': fields.String(required=True, default="0x1F0a4a146776ECC2a3e52F6700901b51aE528bBC", description='Receiver address'),
    'token_uri': fields.Nested(api.model('token_uri', {
        'version': fields.Integer(required=True, default=1, description='Version of the URI'),
        'physical_certificate_url': fields.String(required=True, default="aws/s3/abc", description='URL of physical certificate'),
        'offset_amount': fields.Float(required=True, default=10.5, description='Weight of plastic offset'),
        'recycler_address': fields.String(required=False, default="<will_be_auto_filled>", description='Recycler'),
    }))
})

@plastic_coin.route('')
class CreatePlasticCoin(Resource):
    @api.expect(mint_request)
    def post(self):
        print("------------- Create Coin -------------")
        print("Params - {0}".format(request.json))
        global application_instance
        admin_name = request.json.get('admin_name')
        processor_address = request.json.get('processor_address')
        collector_address = request.json.get('collector_address')
        token_uri = request.json.get('token_uri')

        if admin_name not in application_instance:
            raise BadRequest("No instance exists for {0}".format(admin_name))

        app = application_instance[admin_name]

        processor = app.address_user_map[processor_address]
        collector = app.address_user_map[collector_address]
        app.validate_party(processor, "Processor")
        app.validate_party(collector, "Collector")
        
        # processor_address = app.user_map[processor]["address"]
        # collector_address = app.user_map[collector]["address"]

        contract_address = app.contract_address
        w3 = Web3(Web3.HTTPProvider("http://localhost:8545"))
        w3.eth.defaultAccount = processor_address
        bytecode, abi = compile_contract(['PlasticCoin.sol'], 'PlasticCoin.sol', 'PlasticCoin')
        # print("Using contract address {0}".format(contract_address))
        RecycleContract = w3.eth.contract(address=contract_address, abi=abi, bytecode=bytecode)

        token_uri['recycler_address'] = processor_address
        token_uri = json.dumps(token_uri)
        token_id = get_token_id(token_uri)

        print("Token id - {0}".format(token_id))
        tx_hash = RecycleContract.functions.mintWithTokenURI(collector_address, get_token_id(token_uri), token_uri).transact()

        print("Tx hash {0}".format(tx_hash))
        resp = Response(
            json.dumps({"token_id": hex(token_id)}),
            status=200, mimetype='application/json')

        return resp

@plastic_coin.route('/<string:coin_id>')
class GetPlasticCoin(Resource):
    def get(self, coin_id):
        print("------------- Get Coin -------------")
        token_id = int(coin_id, 16)
        print("Token id {0}".format(token_id))

        app = application_instance["Piyush"]
        contract_address = app.contract_address
        w3 = Web3(Web3.HTTPProvider("http://localhost:8545"))
        bytecode, abi = compile_contract(['PlasticCoin.sol'], 'PlasticCoin.sol', 'PlasticCoin')

        RecycleContract = w3.eth.contract(address=contract_address, abi=abi, bytecode=bytecode)

        owner_addresses = RecycleContract.functions.getTokenOwners(token_id).call()
        print("Owner addresses - {0}".format(owner_addresses))
        token_uri = RecycleContract.functions.tokenURI(token_id).call()

        resp = {
                "owners": [
                ],
                "token_uri": json.loads(token_uri)
            }

        resp["token_uri"]["recycler"] = app.address_user_map[
            resp["token_uri"]["recycler_address"]]

        for owner_address in owner_addresses:
            resp["owners"].append(
                {
                    "owner_address": owner_address,
                    "email": app.address_user_map[owner_address],
                    "share": RecycleContract.functions.getTokenShare(token_id, owner_address).call()
                })


        resp_json = json.dumps(resp)
        print("Resp json - {0}".format(resp_json))

        return Response(
            resp_json,
            status=200, mimetype='application/json')

@transaction.route('/<tx_hash>')
class Transaction(Resource):
    # Make this async api
    def get(self, tx_hash):
        w3 = Web3(Web3.HTTPProvider("http://localhost:8545"))
        tx_receipt = w3.eth.waitForTransactionReceipt(tx_hash)
        print("Fetching transaction status for tx_hash {0}".format(tx_receipt))

        # TODO: Test failure condition
        resp = Response(
            json.dumps({"status": tx_receipt.status}),
            status=200, mimetype='application/json')

        return resp

send_tokens = api.model('send_tokens', {
    'admin_name': fields.String(required=True, description='Admin name', default="Piyush"),
    'from_address': fields.String(required=True, default="0x1F0a4a146776ECC2a3e52F6700901b51aE528bBC", description='Sender address'),
    'to_address': fields.String(required=True, default="0x1F0a4a146776ECC2a3e52F6700901b51aE528bBC", description='Receiver address'),
    'share': fields.Integer(required=True, default=5, description='Specify share out of 1000 units')
})

@plastic_coin.route('/<string:coin_id>/send')
class SendPlasticCoin(Resource):
    @api.expect(send_tokens)
    def post(self, coin_id):
        print("------------- Share Coin -------------")
        token_id = int(coin_id, 16)
        global application_instance
        admin_name = request.json.get('admin_name')
        from_address = request.json.get('from_address')
        to_address = request.json.get('to_address')
        share = request.json.get('share')

        if admin_name not in application_instance:
            raise BadRequest("No instance exists for {0}".format(admin_name))

        app = application_instance[admin_name]

        contract_address = app.contract_address

        w3 = Web3(Web3.HTTPProvider("http://localhost:8545"))
        w3.eth.defaultAccount = from_address
        bytecode, abi = compile_contract(['PlasticCoin.sol'], 'PlasticCoin.sol', 'PlasticCoin')

        RecycleContract = w3.eth.contract(address=contract_address, abi=abi, bytecode=bytecode)

        # print("Transferring {0} from {1} to {2}".format(amount, from_address, to_address))
        tx_hash = RecycleContract.functions.transferShareFrom(to_address, token_id, int(share)).transact()

        resp = Response(
            json.dumps({"tx_hash": tx_hash.hex()}),
            status=200, mimetype='application/json')

        return resp

get_balance_request = reqparse.RequestParser()
get_balance_request.add_argument('admin_name', required=True, default="Piyush",
    help='Admin name', location='args')
get_balance_request.add_argument('party_name', required=True, default=1, help='Name of party', location='args')

# @ds.route('/get_plastic_coin_balance')
# class PlasticCoinDonor(Resource):

#     @api.expect(get_balance_request)
#     def get(self):
#         global application_instance
#         args = get_balance_request.parse_args(request)
#         admin_name = args.get('admin_name')
#         party_name = args.get('party_name')

#         if admin_name not in application_instance:
#             raise BadRequest("No instance exists for {0}".format(admin_name))

#         app = application_instance[admin_name]

#         if party_name not in app.user_map:
#             raise BadRequest("No party with name {0}".format(party_name))
        
#         party_address = app.user_map[party_name]["address"]

#         contract_address = app.contract_address

#         w3 = Web3(Web3.HTTPProvider("http://localhost:8545"))
#         w3.eth.defaultAccount = party_address
#         bytecode, abi = compile_contract(['Recycle.sol', 'ERC223.sol', 'IERC223.sol', 'ERC223Mintable.sol', 'Address.sol', 'SafeMath.sol', 'IERC223Recipient.sol'], 'ERC223Mintable.sol', 'ERC223Mintable')
#         print("Using contract address {0}".format(contract_address))
#         RecycleContract = w3.eth.contract(address=contract_address, abi=abi, bytecode=bytecode)

#         balance = RecycleContract.functions.balanceOf(party_address).call()
#         print("Balance of {0} is {1}".format(party_address, balance))

#         return balance

# @cs.route('/get_plastic_coin_balance')
# class PlasticCoin(Resource):

#     @api.expect(get_balance_request)
#     def get(self):
#         global application_instance
#         args = get_balance_request.parse_args(request)
#         admin_name = args.get('admin_name')
#         party_name = args.get('party_name')

#         if admin_name not in application_instance:
#             raise BadRequest("No instance exists for {0}".format(admin_name))

#         app = application_instance[admin_name]

#         if party_name not in app.user_map:
#             raise BadRequest("No party with name {0}".format(party_name))
        
#         party_address = app.user_map[party_name]["address"]

#         contract_address = app.contract_address

#         w3 = Web3(Web3.HTTPProvider("http://localhost:8545"))
#         w3.eth.defaultAccount = party_address
#         bytecode, abi = compile_contract(['Recycle.sol', 'ERC223.sol', 'IERC223.sol', 'ERC223Mintable.sol', 'Address.sol', 'SafeMath.sol', 'IERC223Recipient.sol'], 'ERC223Mintable.sol', 'ERC223Mintable')
#         print("Using contract address {0}".format(contract_address))
#         RecycleContract = w3.eth.contract(address=contract_address, abi=abi, bytecode=bytecode)

#         balance = RecycleContract.functions.balanceOf(party_address).call()
#         print("Balance of {0} is {1}".format(party_address, balance))

#         return balance

# total_plastic_coins_request = reqparse.RequestParser()
# total_plastic_coins_request.add_argument('admin_name', required=True, default="Piyush",
#     help='Admin name', location='args')

# @user.route('/total_plastic_coins')
# class TotalPlasticCoins(Resource):

#     @api.expect(total_plastic_coins_request)
#     def get(self):
#         global application_instance
#         args = total_plastic_coins_request.parse_args(request)
#         admin_name = args.get('admin_name')
#         if admin_name not in application_instance:
#             raise BadRequest("No instance exists for {0}".format(admin_name))

#         app = application_instance[admin_name]
#         contract_address = app.contract_address

#         w3 = Web3(Web3.HTTPProvider("http://localhost:8545"))
#         w3.eth.defaultAccount = w3.eth.accounts[0]


#         bytecode, abi = compile_contract(['Recycle.sol', 'ERC223.sol', 'IERC223.sol', 'ERC223Mintable.sol', 'Address.sol', 'SafeMath.sol', 'IERC223Recipient.sol'], 'ERC223Mintable.sol', 'ERC223Mintable')
#         print("Using contract address {0}".format(contract_address))
#         RecycleContract = w3.eth.contract(address=contract_address, abi=abi, bytecode=bytecode)

#         print("Code at contract address {0} is {1}".format(contract_address, w3.eth.getCode(contract_address)))

#         totalSupply = RecycleContract.functions.totalSupply().call()
#         print("Total supply {0}".format(totalSupply))

#         return totalSupply

def compile_contract(contract_source_files, contractFileName, contractName=None):
    """
    Reads file, compiles, returns contract name and interface

    Returns:
        bytecode
    """
    compiler_input = {
        "language": 'Solidity',
        "sources": {
        },
        "settings": {
            "outputSelection": {
                '*': {
                    '*': [ "*" ]
                }
            }
        }
    }

    for contract_source_file in contract_source_files:
        f = open(contract_source_file,"r")
        compiler_input["sources"][contract_source_file] = {
            "content": f.read()
        }

    #print("Compiler input {0}".format(compiler_input))
    # TODO: Fix the allowed paths
    import os
    compiled_sol = compile_standard(compiler_input, allow_paths="{0}/node_modules/@openzeppelin/".format(os.getcwd())) # Compiled source code
    # print("Compiled bytecode {0}".format(compiled_sol['contracts'][contractFileName][contractName])) # [contractFileName][contractName]['evm']['bytecode']['object']
    bytecode = compiled_sol['contracts'][contractFileName][contractName]['evm']['bytecode']['object']
    abi = json.loads(compiled_sol['contracts'][contractFileName][contractName]['metadata'])['output']['abi']
    return bytecode, abi

def main():
    import sys
    port = int(sys.argv[1])
    app.run(host='0.0.0.0', port=port, debug=True)

if __name__ == "__main__":
    main()
