from flask import Flask, request, Response
from flask_restplus import Resource, fields, reqparse, Api
import logging
from solc import compile_standard
import json
from web3 import Web3
from werkzeug.exceptions import BadRequest

import os
# from api.endpoints.contract import ns, ps, cs, ds
# from api.restplus import api

app = Flask(__name__)
api = Api(app, version="1.0", title="rePurpose Plastic token")

plastic_coin = api.namespace('plastic_coin', description='Plastic coin entity')
transaction = api.namespace('transaction', description='Monitor transactions')
user = api.namespace('user', description='User management')
ps = api.namespace('processor', description='Operations available to processor')
cs = api.namespace('collector', description='Operations available to collector')
ds = api.namespace('donor', description='Operations available to donor')

create_application_instance = reqparse.RequestParser()
create_application_instance.add_argument('admin_name', required=True, default="Piyush",
    help='Admin name instance', location='args')

application_instance = {}

class Application():
    def __init__(self):
        self.user_map = {}
        w3 = Web3(Web3.HTTPProvider("http://localhost:8545"))
        self.owner_account = w3.eth.accounts[0]
        self.contract_address = ""

    def create_account(self):
        w3 = Web3(Web3.HTTPProvider("http://localhost:8545"))
        address = w3.geth.personal.newAccount("this-phrase")
        # Bug in ganache-cli, doesn't accept two arguments, duration=None also doesn't work

        print("Created address {0}".format(address))
        gasLimit = 3000000;
        w3.geth.personal.unlockAccount(address, "this-phrase", None)
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

    def add_party(self, party_name, type):
        if party_name in self.user_map:
            raise BadRequest("This party already exists")

        w3 = Web3(Web3.HTTPProvider("http://localhost:8545"))
        self.user_map[party_name] = {
            "type": type,
            "address": self.create_account()
        }

        if type == "Processor":
            processor_address = self.user_map[party_name]["address"]
            print("Processor address {0}".format(processor_address))

            # w3 = Web3(Web3.HTTPProvider("http://localhost:8545"))
            w3.eth.defaultAccount = self.owner_account
            bytecode, abi = compile_contract(['Recycle.sol', 'ERC223.sol', 'IERC223.sol', 'ERC223Mintable.sol', 'Address.sol', 'SafeMath.sol', 'IERC223Recipient.sol'], 'ERC223Mintable.sol', 'ERC223Mintable')

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
        global application_instance
        args = create_application_instance.parse_args(request)
        admin_name = args.get('admin_name')
        print("Creating instance for {0}".format(admin_name))

        if admin_name in application_instance:
            raise BadRequest("This instance already exists")

        w3 = Web3(Web3.HTTPProvider("http://localhost:8545"))
        w3.eth.defaultAccount = w3.eth.accounts[0]

        bytecode, abi = compile_contract(['Recycle.sol', 'ERC223.sol', 'IERC223.sol', 'ERC223Mintable.sol', 'Address.sol', 'SafeMath.sol', 'IERC223Recipient.sol'], 'ERC223Mintable.sol', 'ERC223Mintable')

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

# create_user = reqparse.RequestParser()
# create_user.add_argument('admin_name', required=True, default="Piyush",
#     help='Admin name', location='args')
# create_user.add_argument('type', required=True, default=1,
#     choices=("Processor", "Collector", "Donor"), help='Select the type of party', location='args')
# create_user.add_argument('name_of_party', required=True, default=1,
#     help='Something like Ambuja Cement (a Processor), Saahas (a collector), Rajat (a donor)', location='args')

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

        print("Adding party {0}".format(request.json))

        if admin_name not in application_instance:
            raise BadRequest("No instance exists for {0}".format(admin_name))

        app = application_instance[admin_name]
        app.add_party(email, user_type)

        esp = Response(
            json.dumps({"public_key": app.user_map[email][address]}),
            status=200, mimetype='application/json')

list_parties_request = reqparse.RequestParser()
list_parties_request.add_argument('admin_name', required=True, default="Piyush",
    help='Admin name', location='args')

@user.route('/list_parties')
class ListParties(Resource):

    # @api.marshal_with(page_of_blog_posts)
    @api.expect(list_parties_request)
    def post(self):
        global application_instance
        args = list_parties_request.parse_args(request)
        admin_name = args.get('admin_name')
        
        if admin_name not in application_instance:
            raise BadRequest("No instance exists for {0}".format(admin_name))

        app = application_instance[admin_name]
        contract_address = app.contract_address
        import copy
        res = copy.deepcopy(app.user_map)

        w3 = Web3(Web3.HTTPProvider("http://localhost:8545"))

        bytecode, abi = compile_contract(['Recycle.sol', 'ERC223.sol', 'IERC223.sol', 'ERC223Mintable.sol', 'Address.sol', 'SafeMath.sol', 'IERC223Recipient.sol'], 'ERC223Mintable.sol', 'ERC223Mintable')
        print("Using contract address {0}".format(contract_address))
        RecycleContract = w3.eth.contract(address=contract_address, abi=abi, bytecode=bytecode)

        for user in app.user_map:
            balance = RecycleContract.functions.balanceOf(res[user]["address"]).call()
            print("Balance of {0} is {1}".format(res[user]["address"], balance))
            res[user]["balance"] = balance

        return res

mint_request = api.model('mint_request', {
    'admin_name': fields.String(required=True, description='Admin name', default="Piyush"),
    'processor': fields.String(required=True, default="Ambuja", description='Processor'),
    'collector': fields.String(required=True, default="Saahas", description='Collector'),
    'amount': fields.Integer(required=True, default=1, type=int, description='Amount of plastic coins'),
    'physical_certificate': fields.String(required=True, default=1, type=int, description='Need to figure out how the reference to the certificate will be pased')
})

@plastic_coin.route('')
class CreatePlasticCoin(Resource):
    @api.expect(mint_request)
    def post(self):
        global application_instance
        admin_name = request.json.get('admin_name')
        processor = request.json.get('processor')
        collector = request.json.get('collector')
        amount = request.json.get('amount')

        if admin_name not in application_instance:
            raise BadRequest("No instance exists for {0}".format(admin_name))

        app = application_instance[admin_name]

        app.validate_party(processor, "Processor")
        app.validate_party(collector, "Collector")
        
        processor_address = app.user_map[processor]["address"]
        collector_address = app.user_map[collector]["address"]

        user_address = collector_address
        minter_address = processor_address
        print("user address {0}".format(user_address))
        print("amount {0}".format(amount))

        contract_address = app.contract_address
        w3 = Web3(Web3.HTTPProvider("http://localhost:8545"))
        w3.eth.defaultAccount = minter_address
        bytecode, abi = compile_contract(['Recycle.sol', 'ERC223.sol', 'IERC223.sol', 'ERC223Mintable.sol', 'Address.sol', 'SafeMath.sol', 'IERC223Recipient.sol'], 'ERC223Mintable.sol', 'ERC223Mintable')
        print("Using contract address {0}".format(contract_address))
        RecycleContract = w3.eth.contract(address=contract_address, abi=abi, bytecode=bytecode)

        tx_hash = RecycleContract.functions.mint(user_address, amount).transact()

        print("Create plastic coin {0}. TX hash {1}".format(request, tx_hash))
        resp = Response(
            json.dumps({"tx_hash": tx_hash.hex()}),
            status=200, mimetype='application/json')

        return resp
        # tx_receipt = w3.eth.waitForTransactionReceipt(tx_hash)
        # print(tx_receipt)

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
    'from_address': fields.String(required=True, default="Ambuja", description='Processor'),
    'to_address': fields.String(required=True, default="Saahas", description='Collector'),
    'amount': fields.Integer(required=True, default=5, description='Amount')
})

@plastic_coin.route('/<token_uuid>/send')
class SendPlasticCoin(Resource):
    @api.expect(send_tokens)
    def post(self, token_uuid):
        global application_instance
        admin_name = request.json.get('admin_name')
        from_address = request.json.get('from_address')
        to_address = request.json.get('to_address')
        amount = request.json.get('amount')

        if admin_name not in application_instance:
            raise BadRequest("No instance exists for {0}".format(admin_name))

        app = application_instance[admin_name]

        contract_address = app.contract_address

        w3 = Web3(Web3.HTTPProvider("http://localhost:8545"))
        w3.eth.defaultAccount = from_address
        bytecode, abi = compile_contract(['Recycle.sol', 'ERC223.sol', 'IERC223.sol', 'ERC223Mintable.sol', 'Address.sol', 'SafeMath.sol', 'IERC223Recipient.sol'], 'ERC223Mintable.sol', 'ERC223Mintable')
        print("Using contract address {0}".format(contract_address))
        RecycleContract = w3.eth.contract(address=contract_address, abi=abi, bytecode=bytecode)

        print("Transferring {0} from {1} to {2}".format(amount, from_address, to_address))
        tx_hash = RecycleContract.functions.transfer(to_address, int(amount)).transact()

        resp = Response(
            json.dumps({"tx_hash": tx_hash.hex()}),
            status=200, mimetype='application/json')

        return resp

get_balance_request = reqparse.RequestParser()
get_balance_request.add_argument('admin_name', required=True, default="Piyush",
    help='Admin name', location='args')
get_balance_request.add_argument('party_name', required=True, default=1, help='Name of party', location='args')

@ds.route('/get_plastic_coin_balance')
class PlasticCoinDonor(Resource):

    @api.expect(get_balance_request)
    def get(self):
        global application_instance
        args = get_balance_request.parse_args(request)
        admin_name = args.get('admin_name')
        party_name = args.get('party_name')

        if admin_name not in application_instance:
            raise BadRequest("No instance exists for {0}".format(admin_name))

        app = application_instance[admin_name]

        if party_name not in app.user_map:
            raise BadRequest("No party with name {0}".format(party_name))
        
        party_address = app.user_map[party_name]["address"]

        contract_address = app.contract_address

        w3 = Web3(Web3.HTTPProvider("http://localhost:8545"))
        w3.eth.defaultAccount = party_address
        bytecode, abi = compile_contract(['Recycle.sol', 'ERC223.sol', 'IERC223.sol', 'ERC223Mintable.sol', 'Address.sol', 'SafeMath.sol', 'IERC223Recipient.sol'], 'ERC223Mintable.sol', 'ERC223Mintable')
        print("Using contract address {0}".format(contract_address))
        RecycleContract = w3.eth.contract(address=contract_address, abi=abi, bytecode=bytecode)

        balance = RecycleContract.functions.balanceOf(party_address).call()
        print("Balance of {0} is {1}".format(party_address, balance))

        return balance

@cs.route('/get_plastic_coin_balance')
class PlasticCoin(Resource):

    @api.expect(get_balance_request)
    def get(self):
        global application_instance
        args = get_balance_request.parse_args(request)
        admin_name = args.get('admin_name')
        party_name = args.get('party_name')

        if admin_name not in application_instance:
            raise BadRequest("No instance exists for {0}".format(admin_name))

        app = application_instance[admin_name]

        if party_name not in app.user_map:
            raise BadRequest("No party with name {0}".format(party_name))
        
        party_address = app.user_map[party_name]["address"]

        contract_address = app.contract_address

        w3 = Web3(Web3.HTTPProvider("http://localhost:8545"))
        w3.eth.defaultAccount = party_address
        bytecode, abi = compile_contract(['Recycle.sol', 'ERC223.sol', 'IERC223.sol', 'ERC223Mintable.sol', 'Address.sol', 'SafeMath.sol', 'IERC223Recipient.sol'], 'ERC223Mintable.sol', 'ERC223Mintable')
        print("Using contract address {0}".format(contract_address))
        RecycleContract = w3.eth.contract(address=contract_address, abi=abi, bytecode=bytecode)

        balance = RecycleContract.functions.balanceOf(party_address).call()
        print("Balance of {0} is {1}".format(party_address, balance))

        return balance

total_plastic_coins_request = reqparse.RequestParser()
total_plastic_coins_request.add_argument('admin_name', required=True, default="Piyush",
    help='Admin name', location='args')

@user.route('/total_plastic_coins')
class TotalPlasticCoins(Resource):

    @api.expect(total_plastic_coins_request)
    def get(self):
        global application_instance
        args = total_plastic_coins_request.parse_args(request)
        admin_name = args.get('admin_name')
        if admin_name not in application_instance:
            raise BadRequest("No instance exists for {0}".format(admin_name))

        app = application_instance[admin_name]
        contract_address = app.contract_address

        w3 = Web3(Web3.HTTPProvider("http://localhost:8545"))
        w3.eth.defaultAccount = w3.eth.accounts[0]


        bytecode, abi = compile_contract(['Recycle.sol', 'ERC223.sol', 'IERC223.sol', 'ERC223Mintable.sol', 'Address.sol', 'SafeMath.sol', 'IERC223Recipient.sol'], 'ERC223Mintable.sol', 'ERC223Mintable')
        print("Using contract address {0}".format(contract_address))
        RecycleContract = w3.eth.contract(address=contract_address, abi=abi, bytecode=bytecode)

        print("Code at contract address {0} is {1}".format(contract_address, w3.eth.getCode(contract_address)))

        totalSupply = RecycleContract.functions.totalSupply().call()
        print("Total supply {0}".format(totalSupply))

        return totalSupply

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
    compiled_sol = compile_standard(compiler_input) # Compiled source code
    # print("Compiled bytecode {0}".format(compiled_sol['contracts'][contractFileName][contractName])) # [contractFileName][contractName]['evm']['bytecode']['object']
    bytecode = compiled_sol['contracts'][contractFileName][contractName]['evm']['bytecode']['object']
    abi = json.loads(compiled_sol['contracts'][contractFileName][contractName]['metadata'])['output']['abi']
    return bytecode, abi

# def initialize_app(flask_app):
    # api.add_namespace(ns)
    # api.add_namespace(ps)
    # api.add_namespace(cs)
    # api.add_namespace(ds)
    # flask_app.register_blueprint(blueprint)
    # api.add_resource(HelloWorld, '/')

    #db.init_app(flask_app)


def main():
    import sys
    port = int(sys.argv[1])
    # initialize_app(app)
    # log.info('>>>>> Starting development server at http://{}/api/ <<<<<'.format(app.config['SERVER_NAME']))
    dummy_app = Application()
    w3 = Web3(Web3.HTTPProvider("http://localhost:8545"))
    w3.eth.defaultAccount = w3.eth.accounts[0]

    bytecode, abi = compile_contract(['Recycle.sol', 'ERC223.sol', 'IERC223.sol', 'ERC223Mintable.sol', 'Address.sol', 'SafeMath.sol', 'IERC223Recipient.sol'], 'ERC223Mintable.sol', 'ERC223Mintable')

    RecycleContract = w3.eth.contract(abi=abi, bytecode=bytecode)

    tx_hash = RecycleContract.constructor().transact()

    tx_receipt = w3.eth.waitForTransactionReceipt(tx_hash)
    contract_address = tx_receipt.contractAddress

    dummy_app.contract_address = contract_address
    dummy_app.add_party("Ambuja", "Processor")
    dummy_app.add_party("Reliance", "Processor")
    dummy_app.add_party("Saahas", "Collector")
    dummy_app.add_party("WVI", "Collector")
    dummy_app.add_party("Arun", "Donor")
    dummy_app.add_party("Varun", "Donor")

    global application_instance
    application_instance.update({
        "Piyush" : dummy_app
    })
    app.run(host='0.0.0.0', port=port, debug=True)


if __name__ == "__main__":
    main()
