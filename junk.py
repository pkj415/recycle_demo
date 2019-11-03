import logging
from solc import compile_standard
import json
from web3 import Web3

w3 = Web3(Web3.HTTPProvider("http://localhost:8545"))
