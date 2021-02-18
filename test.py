from smart_contract import SmartContract
import blockchain
import pandas as pd
import mysql.connector

cnx = mysql.connector.connect(user='node0', password='pw', host='127.0.0.1', database='amb')

myBlockchain = blockchain.BlockchainConnection(cnx)
blockchain.update_gpg_keys(myBlockchain, ['technician@cmu.edu', 'joe@cmu.edu'])
#
# smartContract_001 = SmartContract(myBlockchain, contract_id='003', user_role='admin')
#
# # deploy_contract_block = smartContract_001.deploy_contract(project_name='test project 003', engineer_email='engineer@cmu.edu', engineer_name='Test Engineer', technician_email='technician@cmu.edu', technician_name='Test Technician', build_file_hash='test hash', comments='test comments')
#
# # powder_block = smartContract_001.submit_powder(powder_id='SS316L')
#
# # exists, current_state = blockchain.contract_exists(myBlockchain.cnx, '003')
# #
# # print(current_state)
# #
# blockchain.read_my_transactions(myBlockchain.cnx, myBlockchain.client, myBlockchain.gpg, '003')
# #
# # next_contract_id = blockchain.get_next_contract_id(myBlockchain.cnx)
# # print(next_contract_id)
#
# my_contracts = blockchain.find_my_contracts(myBlockchain.cnx, 'technician@cmu.edu')
# print(my_contracts)
#
# role = blockchain.login(myBlockchain.cnx, 'technicin@cmu.edu')
# print(role)
# import gnupg
# gpg = gnupg.GPG()
# output_filename = 'world_state_enc.gpg'
# with open('world_state.py', 'rb') as f:
#     status = gpg.encrypt_file(f, recipients=['technician@cmu.edu'], output='output.gpg')

