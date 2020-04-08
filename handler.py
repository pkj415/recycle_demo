# Copyright 2016 Intel Corporation
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# ------------------------------------------------------------------------------

import sys
import json
sys.path.extend(["/home/pkj/sawtooth-core/sdk/python", "/home/pkj/sawtooth-core/sdk/python/sawtooth_sdk/protobuf"])

import hashlib
import logging


from sawtooth_sdk.processor.handler import TransactionHandler
from sawtooth_sdk.processor.exceptions import InvalidTransaction
from sawtooth_sdk.processor.exceptions import InternalError

from sawtooth_signing.secp256k1 import Secp256k1PrivateKey, Secp256k1PublicKey, Secp256k1Context

LOGGER = logging.getLogger(__name__)

# TODO - Use protobuf instead of jsons
# CAS errors
# Multiple validators
# Request ordering at client
# Error handling and validations

def _sha512(data):
    return hashlib.sha512(data).hexdigest()

class recyclerHyperledgerTransactionHandler(TransactionHandler):
    def __init__(self, namespace_prefix):
        self._namespace_prefix = namespace_prefix

    @property
    def family_name(self):
        return 'recycleHyperledger'

    @property
    def family_versions(self):
        return ['1.0']

    @property
    def namespaces(self):
        return [self._namespace_prefix]

    def _get_prefix(self):
        return _sha512('recycleHyperledger'.encode('utf-8'))[0:6]

    def apply(self, transaction, context):
        print('Got transaction {0}\n'.format(transaction))

        payload_str = None
        try:
            payload_str = transaction.payload.decode("utf-8")
        except ValueError:
            raise InvalidTransaction("Invalid payload serialization")

        payload = json.loads(payload_str)

        request_type = payload["request_type"]

        if request_type == "create_coin":
            coin_address = _sha512(transaction.header.SerializeToString())[0:64]

            absolute_coin_address = self._get_prefix() + coin_address
            print("Updating state address for creating using - {0}".format(absolute_coin_address))

            addresses = context.set_state(
                {
                    absolute_coin_address: json.dumps(payload.get("body", {}), sort_keys=True).encode("utf-8")
                })

            if len(addresses) < 1:
                raise InternalError("State Error")

            address = self._get_prefix() + _sha512(transaction.header.signer_public_key.encode("utf-8"))[0:64]
            print("Updating state address for list of coins of user - {0}".format(address))

            state = {}
            try:
              state = json.loads(context.get_state(address))
            except:
              # TODO - Check for address not being set instead of handling all errors.
              pass

            state[coin_address] = payload.get("body", {})

            addresses = context.set_state({address: json.dumps(state).encode("utf-8")})

            if len(addresses) < 1:
                raise InternalError("State Error")

        elif request_type == "add_stages":
            coin_address = payload["coin_address"]

            absolute_coin_address = self._get_prefix() + coin_address

            coin_state = json.loads(
              context.get_state([absolute_coin_address])[0].data.decode("utf-8"))

            creator_public_key = coin_state["creator_public_key"]
            if creator_public_key != transaction.header.signer_public_key:
                raise InvalidTransaction("Only creator of the coin can add stages")

            for stage in payload["body"]["stages"]:
                stage_name = stage["name"]
                del stage["name"]

                if "stages" not in coin_state:
                  coin_state["stages"] = {}

                if stage_name in coin_state["stages"]:
                    raise InvalidTransaction("Stage {0} already exists".format(stage_name))

                coin_state["stages"][stage_name] = stage

            context.set_state(
                {
                    absolute_coin_address: json.dumps(coin_state, sort_keys=True).encode("utf-8")
                })

        elif request_type == "update_stage":
            coin_address = req_body["coin_address"]
            del req_body["coin_address"]

            transaction_signature = req_body["transaction_signature"]
            del req_body["transaction_signature"]

            stage_name = req_body["name"]

            absolute_coin_address = self._get_prefix() + coin_address
            coin_state = json.loads(
              context.get_state([absolute_coin_address])[0].data.decode("utf-8"))

            user_with_update_rights = coin_state["stages"][stage_name]["can_update"]

            # TODO - If no user is specified with update rights, skip verification.
            payload = json.dumps(req_body, sort_keys=True)

            public_key = Secp256k1PublicKey.from_hex(user_with_update_rights)
            ctx = Secp256k1Context()
            if not ctx.verify(transaction_signature, payload.encode("utf-8"), public_key):
                raise InvalidTransaction("Verification of authenticity failed")

            del req_body["name"]

            # TODO - Handle CAS errors - Parallel/Sequential executors? Dependency between transactions? Batches?
            coin_state["stages"][stage_name] = req_body

            context.set_state({absolute_coin_address: json.dumps(coin_state).encode("utf-8")})


    def get_coin(self, coin_address):
        address = self._get_prefix() + coin_address

        result = self._send_request(
            "state/{}".format(address),
            auth_user=None,
            auth_password=None)
        try:
            return base64.b64decode(yaml.safe_load(result)["data"])
        except BaseException:
            raise


def _unpack_transaction(transaction):
    header = transaction.header

    # The transaction signer is the player
    # signer = header.signer_public_key

    try:
        return transaction.payload.decode("utf-8")
    except ValueError:
        raise InvalidTransaction("Invalid payload serialization")

    # _validate_transaction(name, action, space)

    # if action == 'take':
    #     space = int(space)
    #
    # return name, action, space, signer
