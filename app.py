import sys
sys.path.extend(["/home/pkj/sawtooth-core/sdk/python", "/home/pkj/sawtooth-core/sdk/python/sawtooth_sdk/protobuf", "/home/pkj/sawtooth-core/signing"])

from flask import Flask, request, Response
from flask_restplus import Resource, fields, reqparse, Api
import sha3
from werkzeug.exceptions import BadRequest
from client import RecycleHypClient
import getpass
import os

import json
import hashlib
import base64
from base64 import b64encode
import time
import requests
import yaml

from sawtooth_signing import create_context
from sawtooth_signing import CryptoFactory
from sawtooth_signing import ParseError
from sawtooth_signing.secp256k1 import Secp256k1PrivateKey, Secp256k1PublicKey, Secp256k1Context

from sawtooth_sdk.protobuf.transaction_pb2 import TransactionHeader
from sawtooth_sdk.protobuf.transaction_pb2 import Transaction
from sawtooth_sdk.protobuf.batch_pb2 import BatchList
from sawtooth_sdk.protobuf.batch_pb2 import BatchHeader
from sawtooth_sdk.protobuf.batch_pb2 import Batch

app = Flask(__name__)
api = Api(app, version="1.0", title="rePurpose Impact Verification", validate=False)

transact = api.namespace('transact', description='Transaction APIs')
plastic_coin= api.namespace('plastic_coin', description='Coin read APIs')

base_url = 'http://127.0.0.1:8008'

def _sha512(data):
    return hashlib.sha512(data).hexdigest()

def _get_prefix(self):
    return _sha512('recycleHyperledger'.encode('utf-8'))[0:6]

transaction_request = api.model('transaction_request', {
    'client_key': fields.String(required=True, default="0370a1a847e878e98aa044ca7bf9374e944f78c750a450b9dc40b7b13c95dce30f", description='User key\'s file name'),
    'payload': fields.Raw()
})

@transact.route('')
class Transact(Resource):
    @api.expect(transaction_request)
    def post(self):
        print("------------- Transact -------------")
        print("Params - {0}".format(request.json))

        home = os.path.expanduser("~")
        key_dir = os.path.join(home, ".sawtooth", "keys")

        keyfile = '{}/{}.priv'.format(key_dir, request.json["client_key"])

        private_key_str = None
        try:
            with open(keyfile) as fd:
                private_key_str = fd.read().strip()
        except OSError as err:
            raise Exception(
                'Failed to read private key {}: {}'.format(
                    keyfile, str(err)))

        keyfile = '{}/{}.pub'.format(key_dir, request.json["client_key"])
        public_key_str = None
        try:
            with open(keyfile) as fd:
                public_key_str = fd.read().strip()
                public_key = Secp256k1PublicKey.from_hex(public_key_str)
        except OSError as err:
            raise Exception(
                'Failed to read private key {}: {}'.format(
                    keyfile, str(err)))

        try:
            private_key = Secp256k1PrivateKey.from_hex(private_key_str)
        except ParseError as e:
            raise Exception(
                'Unable to load private key: {}'.format(str(e)))

        ctx = Secp256k1Context()
        payload_str = json.dumps(request.json["payload"], sort_keys=True).encode("utf-8")

        header = TransactionHeader(
            signer_public_key=public_key_str,
            family_name="recycleHyperledger",
            family_version="1.0",
            inputs=["220aa7"],
            outputs=["220aa7"],
            dependencies=[],
            payload_sha512=_sha512(payload_str),
            batcher_public_key=public_key_str,
            nonce=time.time().hex().encode()
        ).SerializeToString()

        signature = ctx.sign(header, private_key)
        print("Signature of payload {0} {1}".format(signature,
          ctx.verify(signature, payload_str, public_key)))

        transaction = Transaction(
            header=header,
            payload=payload_str,
            header_signature=signature
        )

        header = BatchHeader(
            signer_public_key=public_key_str,
            transaction_ids=[transaction.header_signature]
        ).SerializeToString()

        signature = ctx.sign(header, private_key)
        print("Signature of batch header {0} {1}".format(signature,
          ctx.verify(signature, header, public_key)))

        batch = Batch(
            header=header,
            transactions=[transaction],
            header_signature=signature)
        batch_list = BatchList(batches=[batch])

        return self._send_request(
            "batches", batch_list.SerializeToString(),
            'application/octet-stream',
            auth_user=None,
            auth_password=None)

    def _send_request(self,
                      suffix,
                      data=None,
                      content_type=None,
                      auth_user=None,
                      auth_password=None):
        if base_url.startswith("http://"):
            url = "{}/{}".format(base_url, suffix)
        else:
            url = "http://{}/{}".format(base_url, suffix)

        headers = {}
        if auth_user is not None:
            auth_string = "{}:{}".format(auth_user, auth_password)
            b64_string = b64encode(auth_string.encode()).decode()
            auth_header = 'Basic {}'.format(b64_string)
            headers['Authorization'] = auth_header

        if content_type is not None:
            headers['Content-Type'] = content_type

        try:
            if data is not None:
                result = requests.post(url, headers=headers, data=data)
            else:
                result = requests.get(url, headers=headers)

            print("<< {0} {1}".format(result.status_code, result.json()))
            if result.status_code == 404:
                raise Exception("No such game")

            elif not result.ok:
                raise Exception("Error {}: {}".format(
                    result.status_code, result.reason))

        except requests.ConnectionError as err:
            raise Exception(
                'Failed to connect to {}: {}'.format(url, str(err)))

        except BaseException as err:
            raise Exception(err)

        return result.text


@plastic_coin.route('/<string:coin_address>')
class GetPlasticCoin(Resource):
    def get(self, coin_address):
        print("------------- Get Coin -------------")
      
        address = self._get_prefix() + coin_address

        result = self._send_request(
            "state/{}".format(address),
            auth_user=auth_user,
            auth_password=auth_password)

        resp_json = None
        try:
            resp_json = base64.b64decode(yaml.safe_load(result)["data"])
        except BaseException:
            raise

        print("Resp json - {0}".format(resp_json))

        return Response(
            resp_json,
            status=200, mimetype='application/json')

# filter_coins_request = api.model('filter_coins_request', {
#     'coins_filter': fields.Nested(api.model('filter', {
#         'version': fields.Integer(required=False, default=1, description='Version of the coin'),
#         'creator': fields.String(required=False, default="0370a1a847e878e98aa044ca7bf9374e944f78c750a450b9dc40b7b13c95dce30f", description='Address of coin creator')
#     }))
# })

# @user.route('/<string:user_public_key>/filter_coins')
# class FilterTokens(Resource):
#     @api.expect(filter_coins_request)
#     def post(self, user_public_key):
#         global application_instance
#         print("------------- Filter Coins -------------")
#         print("Params - {0}".format(request.json))

#         # TODO: Implement the token filters
#         client = RecycleHypClient(base_url='http://127.0.0.1:8008', keyfile=_get_keyfile())
#         resp = client.filter_coins(user_public_key, request.json)
#         resp_json = json.dumps(resp)
#         print("Resp json - {0}".format(resp_json))

#         return Response(
#             resp_json,
#             status=200, mimetype='application/json')

# add_stages_request = api.model('add_stages', {
#     'stages': fields.List(fields.Nested(api.model('stages',
#         {
#             'name': fields.String(required=True, default="Transport", description='Name of stage'),
#             'can_update': fields.String(required=True, default="0370a1a847e878e98aa044ca7bf9374e944f78c750a450b9dc40b7b13c95dce30f", description='Address of user with update rights'),
#         }
#     ))),
#     'transaction_signature': fields.String(required=True, default="", description='Signature of payload')
# })

# @plastic_coin.route('/<string:plastic_coin_address>/add_stages')
# class AddStages(Resource):
#     @api.expect(add_stages_request)
#     def post(self, plastic_coin_address):
#         global application_instance
#         print("------------- Add Stages -------------")
#         print("Params - {0}".format(request.json))

#         # TODO: Implement the token filters
#         client = RecycleHypClient(base_url='http://127.0.0.1:8008', keyfile=_get_keyfile())
#         resp = client.add_stages(plastic_coin_address, request.json)
#         resp_json = json.dumps({})
#         print("Resp json - {0}".format(resp_json))

#         return Response(
#             resp_json,
#             status=200, mimetype='application/json')

# update_stage_request = api.model('update_stage', {
#     'name': fields.String(required=True, default="Transport", description='Name of stage'),
#     'documents': fields.List(fields.Nested(api.model('documents',
#         {
#             'location': fields.String(required=True, default="aws/abc.pdf", description='Location of document'),
#             'hash': fields.String(required=True, default="dd004d63bab571b5045e2ff52a82dd89", description='MD5 hash of document')
#         }
#     ))),
#     'can_update': fields.String(required=True, default="0370a1a847e878e98aa044ca7bf9374e944f78c750a450b9dc40b7b13c95dce30f", description='Address of user with update rights'),
#     'transaction_signature': fields.String(required=True, default="", description='Signature of payload')
# })

# @plastic_coin.route('/<string:plastic_coin_address>/update_stage')
# class UpdateStage(Resource):
#     @api.expect(add_stages_request)
#     def post(self, plastic_coin_address):
#         global application_instance
#         print("------------- Add Stages -------------")
#         print("Params - {0}".format(request.json))

#         # TODO: Implement the token filters
#         client = RecycleHypClient(base_url='http://127.0.0.1:8008', keyfile=_get_keyfile())
#         resp = client.update_stage(plastic_coin_address, request.json)
#         resp_json = json.dumps({})
#         print("Resp json - {0}".format(resp_json))

#         return Response(
#             resp_json,
#             status=200, mimetype='application/json')

def main():
    import sys
    port = int(sys.argv[1])
    app.run(host='0.0.0.0', port=port, debug=True)


if __name__ == "__main__":
    main()
