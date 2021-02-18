from smart_contract import SmartContract
import blockchain
import pandas as pd
import mysql.connector


cnx = mysql.connector.connect(user='node0', password='pw', host='127.0.0.1', database='amb')

my_BlockchainConnector = blockchain.BlockchainConnection(cnx)
# my_SmartContract = SmartContract(my_BlockchainConnector, 'engineer')

# my_SmartContract.deploy_contract('Test Project 4-21', 'engineer@cmu.edu', 'Evan', 'technician@cmu.edu', 'Todd', 'test_hash_name', 'test hash')
# my_SmartContract.submit_powder('SS316L')
blockchain.read_my_transactions(my_BlockchainConnector, '011')
blocks = blockchain.read_last_few_blocks(my_BlockchainConnector, 5)
print(blocks)