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
    'client_public_key': fields.String(required=True, default="0x1F0a4a146776ECC2a3e52F6700901b51aE528bBC", description='Minter address'),
    'client_nonce': fields.Integer(required=True, default=1, description='Client Nonce'),
    'offset_amount': fields.Float(required=True, default=10.5, description='Weight of plastic offset'),
    'pledged_users': fields.List(fields.Nested(api.model('pledged_users', {
        'public_key': fields.String(required=True, default="0x1F0a4a146776ECC2a3e52F6700901b51aE528bBC", description='User address'),
	'share': fields.Integer(required=True, default=1, description='Share of user')
    	}))),
    "request_type": fields.String(required=True, default="create_coin", description='Request type'),
    'stages': fields.List(fields.Nested(api.model('stages',
        {
            'name': fields.String(required=True, default="Transport", description='Name of stage'),
            'documents': fields.List(fields.Nested(api.model('documents',
                {
                    'location': fields.String(required=True, default="aws/s3", description='Location of document'),
                    'hash': fields.String(required=True, default="0x1F0a4a146776ECC2a3e52F6700901b51aE528bBC", description='SHA hash of document')
                }
            ))),
        }
    ))),
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
        resp = Response(
            json.dumps({"coin_address": coin_address}),
            status=200, mimetype='application/json')

        return resp


def main():
    import sys
    port = int(sys.argv[1])
    app.run(host='0.0.0.0', port=port, debug=True)


if __name__ == "__main__":
    main()
