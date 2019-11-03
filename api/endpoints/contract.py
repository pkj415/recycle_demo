import logging
from solc import compile_standard
import json
from web3 import Web3

from flask import request
from werkzeug.exceptions import BadRequest
from flask_restplus import Resource
# from rest_api_demo.api.blog.business import create_blog_post, update_post, delete_post
# from rest_api_demo.api.blog.serializers import blog_post, page_of_blog_posts
# from rest_api_demo.api.blog.parsers import pagination_arguments
from ..restplus import api
from flask_restplus import reqparse
# from rest_api_demo.database.models import Post

# log = logging.getLogger(__name__)
ns = api.namespace('plastic_coin', description='Operations related to the PlasticCoin')

application_instance = {

}

create_application_instance = reqparse.RequestParser()
create_application_instance.add_argument('your_name', required=True,
    help='Your instance so that you don\'t mess anyone else instance', location='args')

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

    def add_party(self, party_name, party_type):
        if party_name in self.user_map:
            raise BadRequest("This party already exists")

        w3 = Web3(Web3.HTTPProvider("http://localhost:8545"))
        self.user_map[party_name] = {
            "type": party_type,
            "address": self.create_account()
        }

        if party_type == "Processor":
            processor_address = self.user_map[party_name]["address"]
            print("Processor address {0}".format(processor_address))

            # w3 = Web3(Web3.HTTPProvider("http://localhost:8545"))
            w3.eth.defaultAccount = self.owner_account
            bytecode, abi = compile_contract(['junk.sol', 'Recycle.sol', 'ERC223.sol', 'IERC223.sol', 'ERC223Mintable.sol', 'Address.sol', 'SafeMath.sol', 'IERC223Recipient.sol'], 'ERC223Mintable.sol', 'ERC223Mintable')

            print("Adding as minter to contract address {0}".format(self.contract_address))
            print("Code at contract address {0} is {1}".format(self.contract_address, w3.eth.getCode(self.contract_address)))
            RecycleContract = w3.eth.contract(address=self.contract_address, abi=abi, bytecode=bytecode)

            tx_hash = RecycleContract.functions.addMinter(processor_address).transact()

            tx_receipt = w3.eth.waitForTransactionReceipt(tx_hash)
            print(tx_receipt)

    def validate_party(self, party, party_type):
        if party not in self.user_map:
            raise BadRequest("No party with name {0}".format(party))

        if self.user_map[party]["type"] != party_type:
            raise BadRequest("{0} is not a {1}".format(party, party_type))

@ns.route('/create_application')    
class CreateApplication(Resource):

    @api.expect(create_application_instance)
    def post(self):
        global application_instance
        args = create_application_instance.parse_args(request)
        your_name = args.get('your_name')
        print("Creating instance for {0}".format(your_name))

        if your_name in application_instance:
            raise BadRequest("This instance already exists")

        w3 = Web3(Web3.HTTPProvider("http://localhost:8545"))
        w3.eth.defaultAccount = w3.eth.accounts[0]

        bytecode, abi = compile_contract(['junk.sol', 'Recycle.sol', 'ERC223.sol', 'IERC223.sol', 'ERC223Mintable.sol', 'Address.sol', 'SafeMath.sol', 'IERC223Recipient.sol'], 'ERC223Mintable.sol', 'ERC223Mintable')

        print("Bytecode {0}".format(bytecode))
        RecycleContract = w3.eth.contract(abi=abi, bytecode=bytecode)

        tx_hash = RecycleContract.constructor().transact()

        tx_receipt = w3.eth.waitForTransactionReceipt(tx_hash)
        print(tx_receipt)
        contract_address = tx_receipt.contractAddress
        print("Created contract address {0}".format(contract_address))

        application_instance[your_name] = Application()
        application_instance[your_name].contract_address = contract_address

create_party = reqparse.RequestParser()
create_party.add_argument('your_name', required=True,
    help='Your instance so that you don\'t mess anyone else instance', location='args')
create_party.add_argument('party_type', required=True, default=1,
    choices=("Processor", "Collector", "Donor"), help='Select the type of party', location='args')
create_party.add_argument('name_of_party', required=True, default=1,
    help='Something like Ambuja Cement (a Processor), Saahas (a collector), Rajat (a donor)', location='args')

@ns.route('/create_party')
class CreateParty(Resource):
    @api.expect(create_party)
    def post(self):
        global application_instance
        args = create_party.parse_args(request)
        your_name = args.get('your_name')
        party_type = args.get('party_type')
        name_of_party = args.get("name_of_party")

        print("Adding party {0}".format(args))

        if your_name not in application_instance:
            raise BadRequest("No instance exists for {0}".format(your_name))

        app = application_instance[your_name]
        app.add_party(name_of_party, party_type)

list_parties_request = reqparse.RequestParser()
list_parties_request.add_argument('your_name', required=True,
    help='Your instance so that you don\'t mess anyone else instance', location='args')

@ns.route('/list_parties')
class ListParties(Resource):

    # @api.marshal_with(page_of_blog_posts)
    @api.expect(list_parties_request)
    def post(self):
        global application_instance
        args = list_parties_request.parse_args(request)
        your_name = args.get('your_name')
        
        if your_name not in application_instance:
            raise BadRequest("No instance exists for {0}".format(your_name))

        app = application_instance[your_name]
        contract_address = app.contract_address
        import copy
        res = copy.deepcopy(app.user_map)

        w3 = Web3(Web3.HTTPProvider("http://localhost:8545"))

        bytecode, abi = compile_contract(['junk.sol', 'Recycle.sol', 'ERC223.sol', 'IERC223.sol', 'ERC223Mintable.sol', 'Address.sol', 'SafeMath.sol', 'IERC223Recipient.sol'], 'ERC223Mintable.sol', 'ERC223Mintable')
        print("Using contract address {0}".format(contract_address))
        RecycleContract = w3.eth.contract(address=contract_address, abi=abi, bytecode=bytecode)

        for user in app.user_map:
            balance = RecycleContract.functions.balanceOf(res[user]["address"]).call()
            print("Balance of {0} is {1}".format(res[user]["address"], balance))
            res[user]["balance"] = balance
            del res[user]["address"]

        return res

mint_request = reqparse.RequestParser()
mint_request.add_argument('your_name', required=True,
    help='Your instance so that you don\'t mess anyone else instance', location='args')
mint_request.add_argument('processor', required=True, default=1, help='Processor', location='args')
mint_request.add_argument('collector', required=True, default=1, help='Collector', location='args')
mint_request.add_argument('amount', required=True, default=1, type=int, help='Amount of plastic coins', location='args')

@ns.route('/create_plastic_coin')
class CreatePlasticCoin(Resource):

    # @api.expect(pagination_arguments)
    # @api.marshal_with(page_of_blog_posts)
    @api.expect(mint_request)
    def post(self):
        global application_instance
        args = mint_request.parse_args(request)
        your_name = args.get('your_name')
        processor = args.get('processor')
        collector = args.get('collector')
        amount = args.get('amount')

        if your_name not in application_instance:
            raise BadRequest("No instance exists for {0}".format(your_name))

        app = application_instance[your_name]

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
        bytecode, abi = compile_contract(['junk.sol', 'Recycle.sol', 'ERC223.sol', 'IERC223.sol', 'ERC223Mintable.sol', 'Address.sol', 'SafeMath.sol', 'IERC223Recipient.sol'], 'ERC223Mintable.sol', 'ERC223Mintable')
        print("Using contract address {0}".format(contract_address))
        RecycleContract = w3.eth.contract(address=contract_address, abi=abi, bytecode=bytecode)

        tx_hash = RecycleContract.functions.mint(user_address, amount).transact()

        tx_receipt = w3.eth.waitForTransactionReceipt(tx_hash)
        print(tx_receipt)

        return 0

redeem_plastic_coins_request = reqparse.RequestParser()
redeem_plastic_coins_request.add_argument('your_name', required=True,
    help='Your instance so that you don\'t mess anyone else instance', location='args')
redeem_plastic_coins_request.add_argument('collector', required=True, default=1, help='Collector', location='args')
redeem_plastic_coins_request.add_argument('donor', required=True, default=1, help='Donor', location='args')
redeem_plastic_coins_request.add_argument('amount', required=True, default=1, help='Number of plastic coins', location='args')

@ns.route('/redeem_plastic_coins')
class PlasticCoin(Resource):

    @api.expect(redeem_plastic_coins_request)
    def get(self):
        global application_instance
        args = redeem_plastic_coins_request.parse_args(request)
        your_name = args.get('your_name')
        donor = args.get('donor')
        collector = args.get('collector')
        amount = args.get('amount')
        
        if your_name not in application_instance:
            raise BadRequest("No instance exists for {0}".format(your_name))

        app = application_instance[your_name]
        
        app.validate_party(collector, "Collector")
        app.validate_party(donor, "Donor")
        donor_address = app.user_map[donor]["address"]
        collector_address = app.user_map[collector]["address"]

        contract_address = app.contract_address

        w3 = Web3(Web3.HTTPProvider("http://localhost:8545"))
        w3.eth.defaultAccount = collector_address
        bytecode, abi = compile_contract(['junk.sol', 'Recycle.sol', 'ERC223.sol', 'IERC223.sol', 'ERC223Mintable.sol', 'Address.sol', 'SafeMath.sol', 'IERC223Recipient.sol'], 'ERC223Mintable.sol', 'ERC223Mintable')
        print("Using contract address {0}".format(contract_address))
        RecycleContract = w3.eth.contract(address=contract_address, abi=abi, bytecode=bytecode)

        print("Transferring {0} from {1} to {2}".format(amount, collector_address, donor_address))
        RecycleContract.functions.transfer(donor_address, int(amount)).transact()

        return 0

get_balance_request = reqparse.RequestParser()
get_balance_request.add_argument('your_name', required=True,
    help='Your instance so that you don\'t mess anyone else instance', location='args')
get_balance_request.add_argument('party_name', required=True, default=1, help='Name of party', location='args')

@ns.route('/get_plastic_coin_balance')
class PlasticCoin(Resource):

    @api.expect(get_balance_request)
    def get(self):
        global application_instance
        args = get_balance_request.parse_args(request)
        your_name = args.get('your_name')
        party_name = args.get('party_name')

        if your_name not in application_instance:
            raise BadRequest("No instance exists for {0}".format(your_name))

        app = application_instance[your_name]

        if party_name not in app.user_map:
            raise BadRequest("No party with name {0}".format(party_name))
        
        party_address = app.user_map[party_name]["address"]

        contract_address = app.contract_address

        w3 = Web3(Web3.HTTPProvider("http://localhost:8545"))
        w3.eth.defaultAccount = party_address
        bytecode, abi = compile_contract(['junk.sol', 'Recycle.sol', 'ERC223.sol', 'IERC223.sol', 'ERC223Mintable.sol', 'Address.sol', 'SafeMath.sol', 'IERC223Recipient.sol'], 'ERC223Mintable.sol', 'ERC223Mintable')
        print("Using contract address {0}".format(contract_address))
        RecycleContract = w3.eth.contract(address=contract_address, abi=abi, bytecode=bytecode)

        balance = RecycleContract.functions.balanceOf(party_address).call()
        print("Balance of {0} is {1}".format(party_address, balance))

        return balance

total_plastic_coins_request = reqparse.RequestParser()
total_plastic_coins_request.add_argument('your_name', required=True,
    help='Your instance so that you don\'t mess anyone else instance', location='args')

@ns.route('/total_plastic_coins')
class TotalPlasticCoins(Resource):

    @api.expect(total_plastic_coins_request)
    def get(self):
        global application_instance
        args = total_plastic_coins_request.parse_args(request)
        your_name = args.get('your_name')
        if your_name not in application_instance:
            raise BadRequest("No instance exists for {0}".format(your_name))

        app = application_instance[your_name]
        contract_address = app.contract_address

        w3 = Web3(Web3.HTTPProvider("http://localhost:8545"))
        w3.eth.defaultAccount = w3.eth.accounts[0]


        bytecode, abi = compile_contract(['junk.sol', 'Recycle.sol', 'ERC223.sol', 'IERC223.sol', 'ERC223Mintable.sol', 'Address.sol', 'SafeMath.sol', 'IERC223Recipient.sol'], 'ERC223Mintable.sol', 'ERC223Mintable')
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