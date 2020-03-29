import sys
sys.path.extend(["/home/pkj/sawtooth-core/sdk/python", "/home/pkj/sawtooth-core/sdk/python/sawtooth_sdk/protobuf"])

import hashlib
import base64
from base64 import b64encode
import time
import requests
import yaml

from sawtooth_signing import create_context
from sawtooth_signing import CryptoFactory
from sawtooth_signing import ParseError
from sawtooth_signing.secp256k1 import Secp256k1PrivateKey

from sawtooth_sdk.protobuf.transaction_pb2 import TransactionHeader
from sawtooth_sdk.protobuf.transaction_pb2 import Transaction
from sawtooth_sdk.protobuf.batch_pb2 import BatchList
from sawtooth_sdk.protobuf.batch_pb2 import BatchHeader
from sawtooth_sdk.protobuf.batch_pb2 import Batch

from sawtooth_xo.xo_exceptions import XoException


def _sha512(data):
    return hashlib.sha512(data).hexdigest()


class RecycleHypClient:
    def __init__(self, base_url, keyfile=None):

        self._base_url = base_url

        if keyfile is None:
            self._signer = None
            return

        try:
            with open(keyfile) as fd:
                private_key_str = fd.read().strip()
        except OSError as err:
            raise XoException(
                'Failed to read private key {}: {}'.format(
                    keyfile, str(err)))

        try:
            private_key = Secp256k1PrivateKey.from_hex(private_key_str)
        except ParseError as e:
            raise XoException(
                'Unable to load private key: {}'.format(str(e)))

        self._signer = CryptoFactory(create_context('secp256k1')) \
            .new_signer(private_key)

    def create(self, req_body, auth_user=None, auth_password=None):
        # Serialization is just a json string
        payload = json.dumps(req_body)

        # Construct the address
        coin_address = self._get_prefix() + _sha512(json.dumps(req_body))[0:64]
        print("Creating coin {0}".format(coin_address))

        header = TransactionHeader(
            signer_public_key=self._signer.get_public_key().as_hex(),
            family_name="recycleHyperledger",
            family_version="1.0",
            inputs=[coin_address],
            outputs=[coin_address],
            dependencies=[],
            payload_sha512=_sha512(payload),
            batcher_public_key=self._signer.get_public_key().as_hex(),
            nonce=time.time().hex().encode()
        ).SerializeToString()

        signature = self._signer.sign(header)

        transaction = Transaction(
            header=header,
            payload=payload,
            header_signature=signature
        )

        batch_list = self._create_batch_list([transaction])
        # batch_id = batch_list.batches[0].header_signature

        # if wait and wait > 0:
        #     wait_time = 0
        #     start_time = time.time()
        #     response = self._send_request(
        #         "batches", batch_list.SerializeToString(),
        #         'application/octet-stream',
        #         auth_user=auth_user,
        #         auth_password=auth_password)
        #     while wait_time < wait:
        #         status = self._get_status(
        #             batch_id,
        #             wait - int(wait_time),
        #             auth_user=auth_user,
        #             auth_password=auth_password)
        #         wait_time = time.time() - start_time
        #
        #         if status != 'PENDING':
        #             return response
        #
        #     return response

        return self._send_request(
            "batches", batch_list.SerializeToString(),
            'application/octet-stream',
            auth_user=auth_user,
            auth_password=auth_password)

    def get_coin(self, coin_address, auth_user=None, auth_password=None):
        address = self._get_prefix() + coin_address

        result = self._send_request(
            "state/{}".format(address),
            auth_user=auth_user,
            auth_password=auth_password)
        try:
            return base64.b64decode(yaml.safe_load(result)["data"])
        except BaseException:
            return None

    def _get_prefix(self):
        return _sha512('recycleHyperledger'.encode('utf-8'))[0:6]

    def _get_address(self, coin_sha):
        xo_prefix = self._get_prefix()
        game_address = coin_sha.encode('utf-8')[0:64]
        return xo_prefix + game_address

    def _send_request(self,
                      suffix,
                      data=None,
                      content_type=None,
                      auth_user=None,
                      auth_password=None):
        if self._base_url.startswith("http://"):
            url = "{}/{}".format(self._base_url, suffix)
        else:
            url = "http://{}/{}".format(self._base_url, suffix)

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

            if result.status_code == 404:
                raise XoException("No such game")

            elif not result.ok:
                raise XoException("Error {}: {}".format(
                    result.status_code, result.reason))

        except requests.ConnectionError as err:
            raise XoException(
                'Failed to connect to {}: {}'.format(url, str(err)))

        except BaseException as err:
            raise XoException(err)

        return result.text

    # def _send_xo_txn(self,
    #                  name,
    #                  action,
    #                  space="",
    #                  wait=None,
    #                  auth_user=None,
    #                  auth_password=None):
    #     # Serialization is just a delimited utf-8 encoded string
    #     payload = ",".join([name, action, str(space)]).encode()
    #
    #     # Construct the address
    #     address = self._get_address(name)
    #
    #     header = TransactionHeader(
    #         signer_public_key=self._signer.get_public_key().as_hex(),
    #         family_name="xo",
    #         family_version="1.0",
    #         inputs=[address],
    #         outputs=[address],
    #         dependencies=[],
    #         payload_sha512=_sha512(payload),
    #         batcher_public_key=self._signer.get_public_key().as_hex(),
    #         nonce=time.time().hex().encode()
    #     ).SerializeToString()
    #
    #     signature = self._signer.sign(header)
    #
    #     transaction = Transaction(
    #         header=header,
    #         payload=payload,
    #         header_signature=signature
    #     )
    #
    #     batch_list = self._create_batch_list([transaction])
    #     batch_id = batch_list.batches[0].header_signature
    #
    #     if wait and wait > 0:
    #         wait_time = 0
    #         start_time = time.time()
    #         response = self._send_request(
    #             "batches", batch_list.SerializeToString(),
    #             'application/octet-stream',
    #             auth_user=auth_user,
    #             auth_password=auth_password)
    #         while wait_time < wait:
    #             status = self._get_status(
    #                 batch_id,
    #                 wait - int(wait_time),
    #                 auth_user=auth_user,
    #                 auth_password=auth_password)
    #             wait_time = time.time() - start_time
    #
    #             if status != 'PENDING':
    #                 return response
    #
    #         return response
    #
    #     return self._send_request(
    #         "batches", batch_list.SerializeToString(),
    #         'application/octet-stream',
    #         auth_user=auth_user,
    #         auth_password=auth_password)

    def _create_batch_list(self, transactions):
        transaction_signatures = [t.header_signature for t in transactions]

        header = BatchHeader(
            signer_public_key=self._signer.get_public_key().as_hex(),
            transaction_ids=transaction_signatures
        ).SerializeToString()

        signature = self._signer.sign(header)

        batch = Batch(
            header=header,
            transactions=transactions,
            header_signature=signature)
        return BatchList(batches=[batch])
