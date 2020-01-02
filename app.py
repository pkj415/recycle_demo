from flask import Flask, request, Response
from flask_restplus import Resource, fields, reqparse, Api
from solc import compile_standard
import json
import sha3
from web3 import Web3
from werkzeug.exceptions import BadRequest

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
        self.users = []
        w3 = Web3(Web3.HTTPProvider("http://localhost:8545"))
        self.owner_account = w3.eth.accounts[0]
        self.contract_address = ""

    def create_account(self, password):
        w3 = Web3(Web3.HTTPProvider("http://localhost:8545"))
        address = w3.geth.personal.newAccount(password)
        self.users.append(address)

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

    def get_user_map(self):
        w3 = Web3(Web3.HTTPProvider("http://localhost:8545"))
        bytecode, abi = compile_contract(['PlasticCoin.sol'], 'PlasticCoin.sol', 'PlasticCoin',
                                         libraries={"PlasticCoin.sol": {
                                             "PlasticCoinLibrary": self.library_address}}
                                         )

        RecycleContract = w3.eth.contract(address=self.contract_address, abi=abi, bytecode=bytecode)

        user_map = {}
        for user_address in self.users:
            print("Getting user details for {0}".format(user_address))
            email, phone, has_minting_right = RecycleContract.functions.getUserDetails(user_address).call()
            print("Got email and phone {0}, {1}".format(email, phone))
            user_map[user_address] = {
                "email": email,
                "phone": phone,
                "has_minting_right": has_minting_right
            }

        print("User map {0}".format(user_map))
        return user_map

@user.route('/create_application')
class CreateApplication(Resource):

    @api.doc(description="One time operation")
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

        bytecode_library, abi_library = compile_contract(['PlasticCoin.sol'], 'PlasticCoin.sol', 'PlasticCoinLibrary')
        library = w3.eth.contract(abi=abi_library, bytecode=bytecode_library)
        tx_hash = library.constructor().transact()
        tx_receipt = w3.eth.waitForTransactionReceipt(tx_hash)
        library_address = tx_receipt.contractAddress

        print("Created library {0}".format(library_address))
        # library_address = "0x1F0a4a146776ECC2a3e52F6700901b51aE528bBC";

        bytecode, abi = compile_contract(['PlasticCoin.sol'], 'PlasticCoin.sol', 'PlasticCoin', libraries={"PlasticCoin.sol": {
                            "PlasticCoinLibrary": library_address}})

        # print("Piyush Bytecode {0}".format(bytecode))
        RecycleContract = w3.eth.contract(abi=abi, bytecode=bytecode)

        tx_hash = RecycleContract.constructor().transact()

        tx_receipt = w3.eth.waitForTransactionReceipt(tx_hash)
        # print(tx_receipt)
        contract_address = tx_receipt.contractAddress
        print("Created contract address {0}".format(contract_address))

        application_instance[admin_name] = Application()
        application_instance[admin_name].contract_address = contract_address
        application_instance[admin_name].library_address = library_address

create_user = api.model('create_user', {
    'admin_name': fields.String(required=True, description='Admin name', default="Piyush"),
    'password': fields.String(required=True, default="rePurpose1234", description='Password'),
    'phone': fields.String(default="1-XXX-XXXXXXX", description='Phone number'),
    'email': fields.String(required=True, default="josh@gmail.com", description='Email'),
    'has_minting_right': fields.Boolean(required=True, default=True, description='Specify if the user has minting rights')
    # 'user_type': fields.String(choices=("Processor", "Collector", "Donor"), help='Type of user')
})

@user.route('')
class CreateUser(Resource):
    @api.doc(description="Create user (Not present if using metamask)")
    @api.expect(create_user)
    def post(self):
        print("------------- Create user -------------")

        global application_instance
        admin_name = request.json.get('admin_name')
        email = request.json.get('email')
        password = request.json.get('password')
        phone = request.json.get('phone')
        has_minting_right = request.json.get('has_minting_right', True)
        # user_type = request.json.get('user_type')

        print("Adding user {0}".format(request.json))

        if admin_name not in application_instance:
            raise BadRequest("No instance exists for {0}".format(admin_name))

        app = application_instance[admin_name]
        # app.add_party(email, user_type, password)
        address = app.create_account(password)

        w3 = Web3(Web3.HTTPProvider("http://localhost:8545"))
        w3.eth.defaultAccount = address
        bytecode, abi = compile_contract(['PlasticCoin.sol'], 'PlasticCoin.sol', 'PlasticCoin',
                                         libraries={"PlasticCoin.sol": {
                                             "PlasticCoinLibrary": app.library_address}}
                                         )

        RecycleContract = w3.eth.contract(address=app.contract_address, abi=abi, bytecode=bytecode)

        print("Adding user details {0} and {1} for {2}".format(email, phone, address))
        if not email:
            email = ""

        if not phone:
            phone = ""

        tx_hash = RecycleContract.functions.insertUserDetails(email, phone, has_minting_right).transact()
        print("Tx hash {0}".format(tx_hash))

        if has_minting_right:
            w3.eth.defaultAccount = app.owner_account
            tx_hash = RecycleContract.functions.addMinter(address).transact()
            print("Tx hash {0}".format(tx_hash))

        resp = Response(
            json.dumps({"public_key": address}),
            status=200, mimetype='application/json')

        return resp

list_users_request = reqparse.RequestParser()
list_users_request.add_argument('admin_name', required=True, default="Piyush",
    help='Admin name', location='args')

@user.route('/list_users')
class ListParties(Resource):
    @api.doc(description="Helper function for now (Won't exist in actual)")
    @api.expect(list_users_request)
    def post(self):
        global application_instance
        args = list_users_request.parse_args(request)
        admin_name = args.get('admin_name')

        if admin_name not in application_instance:
            raise BadRequest("No instance exists for {0}".format(admin_name))

        app = application_instance[admin_name]

        # w3 = Web3(Web3.HTTPProvider("http://localhost:8545"))
        # bytecode, abi = compile_contract(['PlasticCoin.sol'], 'PlasticCoin.sol', 'PlasticCoin')
        #
        # RecycleContract = w3.eth.contract(address=app.contract_address, abi=abi, bytecode=bytecode)
        #
        # import copy
        # user_map = copy.deepcopy(app.user_map)
        # for email in app.user_map:
        #     print("Getting user details for {0}".format(app.user_map[email]["address"]))
        #     email, phone = RecycleContract.functions.getUserDetails(app.user_map[email]["address"]).call()
        #     print("Got email and phone {0}, {1}".format(email, phone))
        #     user_map[email]["email"] = email
        #     user_map[email]["phone"] = phone

        resp = Response(
            json.dumps(app.get_user_map()),
            status=200, mimetype='application/json')
        return resp

mint_request = api.model('mint_request', {
    'admin_name': fields.String(required=True, description='Admin name', default="Piyush"),
    'source_address': fields.String(required=True, default="0x1F0a4a146776ECC2a3e52F6700901b51aE528bBC", description='Minter address'),
    'destination_address': fields.String(required=True, default="0x1F0a4a146776ECC2a3e52F6700901b51aE528bBC", description='Receiver address'),
    'token_uri': fields.Nested(api.model('token_uri', {
        'version': fields.Integer(required=True, default=1, description='Version of the URI'),
        'physical_certificate_url': fields.String(required=True, default="aws/s3/abc", description='URL of physical certificate'),
        'offset_amount': fields.Float(required=True, default=10.5, description='Weight of plastic offset'),
        'md5': fields.Float(required=True, default="eb55d2cfc18a41a097b9f188ef738ece", description='MD5 checksum of file.'
                    'This will help check if the file has been modified later.'),
        'recycler_address': fields.String(required=False, default="<will_be_auto_filled>", description='Same as minter address'),
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
        source_address = request.json.get('source_address')
        destination_address = request.json.get('destination_address')
        token_uri = request.json.get('token_uri')

        if admin_name not in application_instance:
            raise BadRequest("No instance exists for {0}".format(admin_name))

        app = application_instance[admin_name]

        user_map = app.get_user_map()
        if not user_map[source_address]["has_minting_right"]:
            raise BadRequest("Source doesn't have minting rights")

        contract_address = app.contract_address
        w3 = Web3(Web3.HTTPProvider("http://localhost:8545"))
        w3.eth.defaultAccount = source_address
        bytecode, abi = compile_contract(['PlasticCoin.sol'], 'PlasticCoin.sol', 'PlasticCoin',
                                         libraries={"PlasticCoin.sol": {
                                             "PlasticCoinLibrary": app.library_address}}
                                         )
        # print("Using contract address {0}".format(contract_address))
        RecycleContract = w3.eth.contract(address=contract_address, abi=abi, bytecode=bytecode)

        token_uri['recycler_address'] = source_address
        token_uri = json.dumps(token_uri)
        token_id = get_token_id(token_uri)

        print("Token id - {0}".format(token_id))
        tx_hash = RecycleContract.functions.mintWithTokenURI(destination_address, get_token_id(token_uri), token_uri).transact()

        print("Tx hash {0}".format(tx_hash))
        resp = Response(
            json.dumps({"token_id": hex(token_id)}),
            status=200, mimetype='application/json')

        return resp


filter_tokens_request = api.model('filter_tokens_request', {
    'admin_name': fields.String(required=True, description='Admin name', default="Piyush"),
    'token_filter': fields.Nested(api.model('filter', {
        'version': fields.Integer(required=False, default=1, description='Version of the URI'),
        'source_address': fields.String(required=False, default="0x1F0a4a146776ECC2a3e52F6700901b51aE528bBC", description='Address of recycler'),
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

        # TODO: Implement the token filters

        if admin_name not in application_instance:
            raise BadRequest("No instance exists for {0}".format(admin_name))

        app = application_instance[admin_name]
        contract_address = app.contract_address

        w3 = Web3(Web3.HTTPProvider("http://localhost:8545"))
        bytecode, abi = compile_contract(['PlasticCoin.sol'], 'PlasticCoin.sol', 'PlasticCoin',
                                         libraries={"PlasticCoin.sol": {
                                             "PlasticCoinLibrary": app.library_address}}
                                         )

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

        resp_json = json.dumps(resp)
        print("Resp json - {0}".format(resp_json))

        return Response(
            resp_json,
            status=200, mimetype='application/json')


@plastic_coin.route('/<string:coin_id>')
class GetPlasticCoin(Resource):
    def get(self, coin_id):
        print("------------- Get Coin -------------")
        token_id = int(coin_id, 16)
        print("Token id {0}".format(token_id))

        app = application_instance["Piyush"]
        contract_address = app.contract_address
        w3 = Web3(Web3.HTTPProvider("http://localhost:8545"))
        bytecode, abi = compile_contract(['PlasticCoin.sol'], 'PlasticCoin.sol', 'PlasticCoin',
                                         libraries={"PlasticCoin.sol": {
                                             "PlasticCoinLibrary": app.library_address}}
                                         )

        RecycleContract = w3.eth.contract(address=contract_address, abi=abi, bytecode=bytecode)

        owner_addresses = RecycleContract.functions.getTokenOwners(token_id).call()
        print("Owner addresses - {0}".format(owner_addresses))
        token_uri = RecycleContract.functions.tokenURI(token_id).call()

        resp = {
                "owners": [
                ],
                "token_uri": json.loads(token_uri)
            }

        user_map = app.get_user_map()
        for owner_address in owner_addresses:
            resp["owners"].append(
                {
                    "owner_address": owner_address,
                    "email": user_map[owner_address]["email"],
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
        bytecode, abi = compile_contract(['PlasticCoin.sol'], 'PlasticCoin.sol', 'PlasticCoin',
                                         libraries={"PlasticCoin.sol": {
                                             "PlasticCoinLibrary": app.library_address}}
                                         )

        RecycleContract = w3.eth.contract(address=contract_address, abi=abi, bytecode=bytecode)

        print("Transferring {0} from {1} to {2}".format(share, from_address, to_address))
        tx_hash = RecycleContract.functions.transferShareFrom(to_address, token_id, int(share)).transact()

        resp = Response(
            json.dumps({"tx_hash": tx_hash.hex()}),
            status=200, mimetype='application/json')

        return resp


def compile_contract(contract_source_files, contractFileName, contractName=None, **kwargs):
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
            },
            "libraries": kwargs.get("libraries", {})
        }
    }

    for contract_source_file in contract_source_files:
        f = open(contract_source_file,"r")
        compiler_input["sources"][contract_source_file] = {
            "content": f.read()
        }

    # print("Compiler input {0}".format(compiler_input))
    # TODO: Fix the allowed paths
    import os
    print("Got kwargs {0}".format(kwargs))
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
