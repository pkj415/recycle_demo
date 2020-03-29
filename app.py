from flask import Flask, request, Response
from flask_restplus import Resource, fields, reqparse, Api
import json
import sha3
from werkzeug.exceptions import BadRequest

app = Flask(__name__)
api = Api(app, version="1.0", title="rePurpose Plastic token", validate=False)

plastic_coin = api.namespace('plastic_coin', description='Plastic coin entity')

@plastic_coin.route('')
class CreatePlasticCoin(Resource):
    @api.expect(mint_request)
    def post(self):
        print("------------- Create Coin -------------")
        print("Params - {0}".format(request.json))

        client = RecycleHypClient(base_url)
        client.create_coin(request.json)
        resp = Response(
            json.dumps({"token_id": hex(token_id)}),
            status=200, mimetype='application/json')

        return resp

def main():
    import sys
    port = int(sys.argv[1])
    app.run(host='0.0.0.0', port=port, debug=True)


if __name__ == "__main__":
    main()
