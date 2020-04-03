from flask import Flask, request, Response
from flask_restplus import Resource, fields, reqparse, Api
import json
import sha3
from werkzeug.exceptions import BadRequest
from client import RecycleHypClient
import getpass
import os

app = Flask(__name__)
api = Api(app, version="1.0", title="rePurpose Plastic token", validate=False)

plastic_coin = api.namespace('plastic_coin', description='Plastic coin entity')

def _get_keyfile():
    username = getpass.getuser()
    home = os.path.expanduser("~")
    key_dir = os.path.join(home, ".sawtooth", "keys")

    return '{}/{}.priv'.format(key_dir, username)

mint_request = api.model('mint_request', {
    'client_public_key': fields.String(required=True, default="0370a1a847e878e98aa044ca7bf9374e944f78c750a450b9dc40b7b13c95dce30f", description='Coin creator\'s address'),
    'client_nonce': fields.Integer(required=True, default=1, description='Client Nonce'),
    'offset_amount': fields.Float(required=True, default=10.5, description='Weight of plastic offset'),
    'pledged_users': fields.List(fields.Nested(api.model('pledged_users', {
            'public_key': fields.String(required=True, default="034f8240a75dea0e3ce12a48ba34a3bd4702b0a1a1164d124e4880e167ed3f63c3", description='User address'),
            'share': fields.Integer(required=True, default=1, description='Share of user')
        }))),
    'version': fields.Integer(required=True, default=1, description='Version of the coin'),
    'transaction_signature': fields.String(required=True, default="", description='Signature of payload')
})

@plastic_coin.route('')
class CreatePlasticCoin(Resource):
    @api.expect(mint_request)
    def post(self):
        print("------------- Create Coin -------------")
        print("Params - {0}".format(request.json))

        client = RecycleHypClient(base_url='http://127.0.0.1:8008', keyfile=_get_keyfile())
        coin_address = client.create_coin(request.json)

        resp_json = json.dumps({"coin_address": coin_address})
        print("Resp json - {0}".format(resp_json))
        resp = Response(
            resp_json,
            status=200, mimetype='application/json')

        return resp

@plastic_coin.route('/<string:coin_address>')
class GetPlasticCoin(Resource):
    def get(self, coin_address):
        print("------------- Get Coin -------------")
        
        client = RecycleHypClient(base_url='http://127.0.0.1:8008', keyfile=_get_keyfile())
        resp_json = client.get_coin(coin_address)
        print("Resp json - {0}".format(resp_json))

        return Response(
            resp_json,
            status=200, mimetype='application/json')

filter_coins_request = api.model('filter_coins_request', {
    'coins_filter': fields.Nested(api.model('filter', {
        'version': fields.Integer(required=False, default=1, description='Version of the coin'),
        'creator': fields.String(required=False, default="0370a1a847e878e98aa044ca7bf9374e944f78c750a450b9dc40b7b13c95dce30f", description='Address of coin creator')
    }))
})

@user.route('/<string:address>/filter_tokens')
class FilterTokens(Resource):
    @api.expect(filter_coins_request)
    def post(self, address):
        global application_instance
        print("------------- Filter Coins -------------")
        print("Params - {0}".format(request.json))

        # TODO: Implement the token filters
        client = RecycleHypClient(base_url='http://127.0.0.1:8008', keyfile=_get_keyfile())
        resp = client.filter_tokens(request.json)
        resp_json = json.dumps(resp)
        print("Resp json - {0}".format(resp_json))

        return Response(
            resp_json,
            status=200, mimetype='application/json')

def main():
    import sys
    port = int(sys.argv[1])
    app.run(host='0.0.0.0', port=port, debug=True)


if __name__ == "__main__":
    main()
