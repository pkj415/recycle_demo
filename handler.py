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
        # 1. Deserialize the transaction and verify it is valid
        req_body_str = _unpack_transaction(transaction)

        print('Got req_body_str %s\n', req_body_str)
        req_body = json.loads(req_body_str)
        transaction_signature = req_body["transaction_signature"]
        client_public_key = req_body["client_public_key"]  # Needed as hex

        del req_body["transaction_signature"]
        request_type = req_body["request_type"]
        del req_body["request_type"]

        # Serialization is just a json string
        payload = json.dumps(req_body, sort_keys=True)
        # print('Got payload %s\n', payload)

        public_key = Secp256k1PublicKey.from_hex(client_public_key)
        ctx = Secp256k1Context()
        if not ctx.verify(transaction_signature, payload.encode("utf-8"), public_key):
            raise InvalidTransaction("Verification of authenticity failed")

        if request_type == "create_coin":
            coin_address = self._get_prefix() + _sha512(req_body_str.encode("utf-8"))[0:64]
            self.create_coin(payload, coin_address, client_public_key, context)

    def create_coin(self, payload, coin_address, client_public_key, context):
        print("Creating coin with address {0}".format(coin_address))
        addresses = context.set_state({coin_address: payload.encode("utf-8")})

        if len(addresses) < 1:
            raise InternalError("State Error")

        address = self._get_prefix() + _sha512(client_public_key.encode("utf-8"))[0:64]
        print("Updating list of coins for user {0}".format(client_public_key))
        state = json.loads(context.get_state(address))
        state[coin_address] = json.loads(payload)

        addresses = context.set_state({address: json.dumps(state).encode("utf-8")})

        if len(addresses) < 1:
            raise InternalError("State Error")


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


# def _validate_transaction(name, action, space):
#     if not name:
#         raise InvalidTransaction('Name is required')
#
#     if '|' in name:
#         raise InvalidTransaction('Name cannot contain "|"')
#
#     if not action:
#         raise InvalidTransaction('Action is required')
#
#     if action not in ('create', 'take', 'delete'):
#         raise InvalidTransaction('Invalid action: {}'.format(action))
#
#     if action == 'take':
#         try:
#             assert int(space) in range(1, 10)
#         except (ValueError, AssertionError):
#             raise InvalidTransaction('Space must be an integer from 1 to 9')


def _validate_game_data(action, space, signer, board, state, player1, player2):
    if action == 'create':
        if board is not None:
            raise InvalidTransaction('Invalid action: Game already exists.')

    elif action == 'take':
        if board is None:
            raise InvalidTransaction(
                'Invalid action: Take requires an existing game.')

        if state in ('P1-WIN', 'P2-WIN', 'TIE'):
            raise InvalidTransaction('Invalid Action: Game has ended.')

        if ((player1 and state == 'P1-NEXT' and player1 != signer)
                or (player2 and state == 'P2-NEXT' and player2 != signer)):
            raise InvalidTransaction(
                "Not this player's turn: {}".format(signer[:6]))

        if board[space - 1] != '-':
            raise InvalidTransaction(
                'Invalid Action: space {} already taken'.format(space))

    elif action == 'delete':
        if board is None:
            raise InvalidTransaction('Invalid action: game does not exist')


def _get_state_data(context, namespace_prefix, name):
    # Get data from address
    state_entries = \
        context.get_state([_make_xo_address(namespace_prefix, name)])

    # context.get_state() returns a list. If no data has been stored yet
    # at the given address, it will be empty.
    if state_entries:
        try:
            state_data = state_entries[0].data

            game_list = {
                name: (board, state, player1, player2)
                for name, board, state, player1, player2 in [
                    game.split(',')
                    for game in state_data.decode().split('|')
                ]
            }

            board, state, player1, player2 = game_list[name]

        except ValueError:
            raise InternalError("Failed to deserialize game data.")

    else:
        game_list = {}
        board = state = player1 = player2 = None

    return board, state, player1, player2, game_list


def _store_state_data(
        context, game_list,
        namespace_prefix, name,
        board, state, player1, player2):

    game_list[name] = board, state, player1, player2

    state_data = '|'.join(sorted([
        ','.join([name, board, state, player1, player2])
        for name, (board, state, player1, player2) in game_list.items()
    ])).encode()

    addresses = context.set_state(
        {_make_xo_address(namespace_prefix, name): state_data})

    if len(addresses) < 1:
        raise InternalError("State Error")


def _delete_game(context, name, namespace_prefix):
    LOGGER.warning('Deleting game %s', name)

    address = _make_xo_address(namespace_prefix, name)

    addresses = context.delete_state([address])

    if not addresses:
        raise InternalError('State delete error')


def _play_xo(action, space, signer, board, state, player1, player2):
    if action == 'create':
        return '---------', 'P1-NEXT', '', ''

    elif action == 'take':
        upd_player1, upd_player2 = _update_players(player1, player2, signer)

        upd_board = _update_board(board, space, state)

        upd_state = _update_state(state, upd_board)

        return upd_board, upd_state, upd_player1, upd_player2

    else:
        raise InternalError('Unhandled action: {}'.format(action))


def _update_players(player1, player2, signer):
    '''
    Return: upd_player1, upd_player2
    '''
    if player1 == '':
        return signer, player2

    elif player2 == '':
        return player1, signer

    return player1, player2


def _update_board(board, space, state):
    if state == 'P1-NEXT':
        mark = 'X'
    elif state == 'P2-NEXT':
        mark = 'O'

    index = space - 1

    # replace the index-th space with mark, leave everything else the same
    return ''.join([
        current if square != index else mark
        for square, current in enumerate(board)
    ])


def _update_state(state, board):
    x_wins = _is_win(board, 'X')
    o_wins = _is_win(board, 'O')

    if x_wins and o_wins:
        raise InternalError('Two winners (there can be only one)')

    elif x_wins:
        return 'P1-WIN'

    elif o_wins:
        return 'P2-WIN'

    elif '-' not in board:
        return 'TIE'

    elif state == 'P1-NEXT':
        return 'P2-NEXT'

    elif state == 'P2-NEXT':
        return 'P1-NEXT'

    elif state in ('P1-WINS', 'P2-WINS', 'TIE'):
        return state

    else:
        raise InternalError('Unhandled state: {}'.format(state))


def _is_win(board, letter):
    wins = ((1, 2, 3), (4, 5, 6), (7, 8, 9),
            (1, 4, 7), (2, 5, 8), (3, 6, 9),
            (1, 5, 9), (3, 5, 7))

    for win in wins:
        if (board[win[0] - 1] == letter
                and board[win[1] - 1] == letter
                and board[win[2] - 1] == letter):
            return True
    return False


def _game_data_to_str(board, state, player1, player2, name):
    board = list(board.replace("-", " "))
    out = ""
    out += "GAME: {}\n".format(name)
    out += "PLAYER 1: {}\n".format(player1[:6])
    out += "PLAYER 2: {}\n".format(player2[:6])
    out += "STATE: {}\n".format(state)
    out += "\n"
    out += "{} | {} | {}\n".format(board[0], board[1], board[2])
    out += "---|---|---\n"
    out += "{} | {} | {}\n".format(board[3], board[4], board[5])
    out += "---|---|---\n"
    out += "{} | {} | {}".format(board[6], board[7], board[8])
    return out


def _display(msg):
    n = msg.count("\n")

    if n > 0:
        msg = msg.split("\n")
        length = max(len(line) for line in msg)
    else:
        length = len(msg)
        msg = [msg]

    # pylint: disable=logging-not-lazy
    LOGGER.debug("+" + (length + 2) * "-" + "+")
    for line in msg:
        LOGGER.debug("+ " + line.center(length) + " +")
    LOGGER.debug("+" + (length + 2) * "-" + "+")
