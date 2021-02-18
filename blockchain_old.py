import hashlib
import json
from datetime import datetime
from time import time, mktime
import pickle
import pandas as pd
from os.path import isfile, join, dirname
import gnupg
import ipfshttpclient
import mysql.connector
import os


def get_timestamp():
    ts = time()
    str_stamp = datetime.fromtimestamp(ts).strftime('%Y_%m_%d %H_%M_%S')
    return str_stamp


class Blockchain(object):
    def __init__(self, ledger_dir=None, ledger_path=None):
        self.chain = []
        # initialize GPG encryption
        self.gpg = gnupg.GPG()
        # open IPFS daemon
        try:
            self.client = ipfshttpclient.connect('/ip4/127.0.0.1/tcp/5001/http')
        except:
            raise ConnectionError('Initialize an IPFS session')
        # connect to database
        self.cnx = mysql.connector.connect(user='node0', password='pw',
                                           host='127.0.0.1',
                                           database='amb')
        # the ledger_path points to the root ledger, which is the master (available to everyone in the org.) by default, but could also be a channel (only available to specific parties)
        # by default, first try loading the ledger at the path
        if (ledger_dir is None and ledger_path is None) or (ledger_dir is not None and ledger_path is not None):
            raise AssertionError('You must either specify a ledger_dir (a directory to search for/download the most recent ledger) or a ledger_path (pointing to a specific version of the ledger)')
        elif ledger_dir is None:
            self.ledger_dir = dirname(ledger_path)
            self.ledger_path = ledger_path
            self.chain, self.ledger_path = self.load_blockchain(my_ledger_path=ledger_path)
        elif ledger_path is None:
            try:
                updated, my_ledger_path = ledger_updated(self.cnx, self.client, self.gpg)
                if updated:
                    self.ledger_dir = ledger_dir
                    self.ledger_path = my_ledger_path
                    self.chain = self.load_blockchain(my_ledger_path=my_ledger_path)
                else:
                    refreshed_blockchain = download_ledger(self.cnx, self.client, self.gpg)
                    self.chain = refreshed_blockchain.chain
                    self.ledger_path = refreshed_blockchain.ledger_path
            except IndexError:
                self.chain, self.ledger_path = self.create_new_master()

            # self.chain, self.ledger_path = self.find_current_local_blockchain(ledger_dir)
        else:
            raise AssertionError('Arguments are not valid. See __init__ logic of Blockchain object')
        if self.chain is None:
            raise ValueError('Blockchain object was not initialized properly')
    #
    # def __del__(self):
    #     self.cnx.close()

    def create_new_master(self):
        chain = []
        # genesis block
        chain = self.genesis_block(chain, previous_hash=1)
        ledger_path = self.save_blockchain(length=len(self.chain))
        print('Creating entirely new master blockchain!')
        return chain, ledger_path

    @staticmethod
    def genesis_block(chain, previous_hash):
        block = {
            'index': 0,
            'timestamp': get_timestamp(),
            'transaction_hash': [],
            'previous_block_hash': previous_hash
        }
        chain.append(block)
        return chain

    @staticmethod
    def load_blockchain(my_ledger_path):
        print('loading blockchain...')
        # blockchain = download_ledger(self.cnx, self.client, self.gpg)
        # chain = blockchain.chain
        # consensus protocol: check if my version of the ledger is longer
        myBlockchain = pickle.load(open(my_ledger_path, "rb"))
        # if len(myBlockchain.chain) > len(chain):
        #     print('Warning: consensus dispute - your local version of the ledger is longer than the latest distributed version')
        chain = myBlockchain.chain
        return chain

    def save_blockchain(self, length):
        my_timestamp = get_timestamp()
        ledger_path = 'blockchain_files/' + my_timestamp
        self.cnx = []
        with open(ledger_path, 'wb') as blockchain_file:
            pickle.dump(self, blockchain_file)
        self.cnx = mysql.connector.connect(user='node0', password='pw',
                                           host='127.0.0.1',
                                           database='amb')
        upload_ledger(self.cnx, self.client, self.gpg, ledger_path, my_timestamp, length)
        return ledger_path

    @property
    def last_block(self):
        return self.chain[-1]

    @staticmethod
    def hash(block):
        """
        Creates a SHA-256 hash of a Block
        :param block: <dict> Block
        :return: <str>
        """
        # We must make sure that the Dictionary is Ordered, or we'll have inconsistent hashes
        block_string = json.dumps(block, sort_keys=True).encode()
        return hashlib.sha256(block_string).hexdigest()


def new_block(blockchain_obj: Blockchain, transaction_data, txn_ipfs_hash):
    block = {
        'index': int(len(blockchain_obj.chain)),
        'timestamp': get_timestamp(),
        'transaction_hash': transaction_data,
        'previous_block_hash': blockchain_obj.hash(blockchain_obj.last_block)
    }
    blockchain_obj.chain.append(block)
    ledger_path = blockchain_obj.save_blockchain(length=len(blockchain_obj.chain))
    cur = blockchain_obj.cnx.cursor()
    query_str = 'UPDATE transaction_pool SET block_hash = \'' + blockchain_obj.hash(blockchain_obj.last_block) + '\' WHERE txn_hash = \'' + txn_ipfs_hash + '\';'
    cur.execute(query_str)
    blockchain_obj.cnx.commit()
    return block, ledger_path


def read_full_blockchain(blockchain_obj: Blockchain):
    return blockchain_obj.chain


def read_last_few_blocks(blockchain_obj: Blockchain, n):
    try:
        blocks_df = pd.DataFrame.from_dict(blockchain_obj.chain[-n])
    except IndexError:
        print('There are not enough blocks on this chain yet')
    return blocks_df


def find_blocks_by_contract_id(blockchain_obj: Blockchain, contract_id):
    contract_blocks = blockchain_obj.chain['contract_id'] == contract_id
    return contract_blocks


def find_blocks_by_user(blockchain_obj: Blockchain, email_address):
    user_blocks = blockchain_obj.chain['engineer_email'] == email_address or blockchain_obj.chain['technician_email'] == email_address
    return user_blocks


def verify_chain(blockchain_obj: Blockchain):
    full_ledger = pd.DataFrame.from_dict(read_full_blockchain(blockchain_obj))
    block_hashes = full_ledger.previous_block_hash
    for iBlock in range(len(blockchain_obj.chain) - 1):
        try:
            assert blockchain_obj.hash(blockchain_obj.chain[iBlock]) == block_hashes[iBlock + 1]
        except AssertionError:
            print('!!!WARNING!!! Chain hash been tampered with at block index: ', iBlock)
            break

    print('Chain verified.')

# def get_world_state(blockchain):




########################################################################################################

############################# connector functions ####################################


def upload_ledger(cnx, client, gpg, ledger_path, my_timestamp, length):
    # get recipients
    cur = cnx.cursor()
    query_str = 'SELECT email FROM keyring;'
    cur.execute(query_str)
    result = cur.fetchall()
    recipient_list = []
    for i in range(len(result)):
        email = " ".join(result[i])
        recipient_list.append(email)
    print(recipient_list)

    # get key fingerprints and update keyring if needed
    query_str = 'SELECT public_key FROM keyring;'
    cur.execute(query_str)
    result = cur.fetchall()
    key_ids = []

    # TODO: NEED TO TEST THIS WITH NEW KEYS!
    for i in range(len(result)):
        ikey = " ".join(result[i])
        key_exists = gpg.list_keys(keys=ikey)
        # import keys if needed
        if key_exists is None:
            fname = 'key_files/' + ikey + '.asc'
            ascii_armored_public_keys = gpg.export_keys(ikey)
            with open(fname, 'w') as f:
                f.write(ascii_armored_public_keys)
            gpg.import_keys(key_data=fname)
        key_ids.append(ikey)

    # encrypt blockchain file
    output_filename = ledger_path + '_enc.gpg'
    with open(ledger_path, 'rb') as f:
        status = gpg.encrypt_file(f, recipients=recipient_list, output=output_filename)

    # send via IPFS
    res = client.add(output_filename)
    ipfs_hash_sent = res['Hash']
    print(ipfs_hash_sent)

    # insert IPFS hash into database
    query_str = "INSERT INTO blockchain_hashes (timestamp, ipfs_hash, length) VALUES (\'" + my_timestamp + "\', \'" + ipfs_hash_sent + "\', \'" + str(length) + "\');"
    print(query_str)
    cur.execute(query_str)
    cnx.commit()


def ledger_updated(cnx, client, gpg, gpg_pw='pw'):
    # get hash from db
    cur = cnx.cursor()
    query_str = 'SELECT ipfs_hash, timestamp FROM blockchain_hashes ORDER BY id DESC LIMIT 1;'
    cur.execute(query_str)
    result = cur.fetchall()
    ipfs_hash_rec = result[0][0]
    my_timestamp = result[0][1]
    ledger_path = 'blockchain_files/' + my_timestamp
    if os.path.isfile(ledger_path):
        updated = True
    else:
        updated = False
    return updated, ledger_path


def download_ledger(cnx, client, gpg, gpg_pw='pw'):
    # get hash from db
    cur = cnx.cursor()
    query_str = 'SELECT ipfs_hash, timestamp FROM blockchain_hashes ORDER BY id DESC LIMIT 1;'
    cur.execute(query_str)
    result = cur.fetchall()
    ipfs_hash_rec = result[0][0]
    my_timestamp = result[0][1]
    # sanity check
    # assert ipfs_hash_rec == ipfs_hash_sent

    # download from IPFS
    client.get(ipfs_hash_rec)

    # decrypt
    ledger_path = 'blockchain_files/' + my_timestamp
    with open(ipfs_hash_rec, 'rb') as f:
        status = gpg.decrypt_file(f, passphrase=gpg_pw, output=ledger_path)

    rec_blockchain = pickle.load(open(ledger_path, "rb"))
    verify_chain(rec_blockchain)
    # cnx.close()
    return rec_blockchain

# TODO: similar functions to create & upload keys


def get_next_contract_id(cnx):
    cur = cnx.cursor()
    query_str = "SELECT MAX(contract_id) FROM world_state;"
    cur.execute(query_str)
    result = cur.fetchall()
    n = str(int(result[0][0]) + 1)
    return str(n.zfill(3))


def upload_contract_header(cnx, contract_id, deployed_timestamp, project_name, engineer_email, technician_email, update_timestamp, current_state):
    # get hash from db
    cur = cnx.cursor()
    query_str = "INSERT INTO world_state (contract_id, deployed_timestamp, project_name, engineer_email, technician_email, update_timestamp, current_state) VALUES (\'" + contract_id + "\', \'" + deployed_timestamp + "\', \'" + project_name+ "\', \'" + engineer_email+ "\', \'" + technician_email + "\', \'" + update_timestamp + "\', \'" + current_state + "\');"
    print(query_str)
    cur.execute(query_str)
    cnx.commit()


def download_contract_header(cnx, contract_id):
    # get hash from db
    cur = cnx.cursor()
    query_str = 'SELECT deployed_timestamp, project_name, engineer_email, technician_email, update_timestamp, current_state  FROM world_state WHERE contract_id = ' + "\'" + contract_id + "\';"
    cur.execute(query_str)
    result = cur.fetchall()
    deployed_timestamp = result[0][0]
    project_name = result[0][1]
    engineer_email = result[0][2]
    technician_email = result[0][3]
    update_timestamp = result[0][4]
    current_state = result[0][5]

    contract_header = {
        'deployment_timestamp': deployed_timestamp,
        'last_update_timestamp': update_timestamp,
        'contract_id': contract_id,
        'current_state': current_state,
        'project_name': project_name,
        'engineer_email': engineer_email,
        'technician_email': technician_email
    }
    return contract_header


def update_world_state(cnx, contract_id, update_timestamp, current_state):
    cur = cnx.cursor()
    query_str = 'UPDATE world_state SET update_timestamp = \'' + update_timestamp + '\' WHERE contract_id = \'' + contract_id + '\';'
    print(query_str)
    cur.execute(query_str)

    query_str = 'UPDATE world_state SET current_state = \'' + current_state + '\' WHERE contract_id = \'' + contract_id + '\';'
    print(query_str)
    cur.execute(query_str)
    cnx.commit()


def contract_exists(cnx, contract_id):
    cur = cnx.cursor()
    query_str = 'SELECT current_state  FROM world_state WHERE contract_id = ' + "\'" + contract_id + "\';"
    cur.execute(query_str)
    result = cur.fetchall()
    try:
        current_state = " ".join(result[0])
    except IndexError:
        current_state = None
    if current_state is not None:
        exists = True
    else:
        exists = False
    return exists, current_state


def read_my_transactions(cnx, client, gpg, contract_id, gpg_pw='pw'):
    cur = cnx.cursor()
    query_str = 'SELECT txn_hash, block_hash FROM transaction_pool WHERE contract_id = \'' + contract_id + '\';'
    cur.execute(query_str)
    result = cur.fetchall()
    for i in range(len(result)):
        ipfs_hash_rec = result[i][0]
        my_timestamp = result[i][1]
        client.get(ipfs_hash_rec)
        # decrypt
        output_path = 'contract_files/' + contract_id + '/' + my_timestamp + '_dec'
        with open(ipfs_hash_rec, 'rb') as f:
            status = gpg.decrypt_file(f, passphrase=gpg_pw, output=output_path)

        my_data = pickle.load(open(output_path, "rb"))
        print(my_data)
        f.close()
        os.remove(ipfs_hash_rec)


def insert_transaction(cnx, client, gpg, contract_id, transaction_data, recipients):
    contract_dir = 'contract_files/' + contract_id
    update_timestamp = get_timestamp()
    if not os.path.isdir(contract_dir):
        os.mkdir(path=contract_dir)
    fname = contract_dir + '/' + update_timestamp + '.txt'
    # transaction_data = str.encode(str(transaction_data))
    # write transaction data to json
    with open(fname, 'wb') as transaction_file:
        pickle.dump(transaction_data, transaction_file)

    # encrypt
    output_filename = contract_dir + '/' + update_timestamp + '_enc.gpg'
    with open(fname, 'rb') as f:
        status = gpg.encrypt_file(f, recipients=recipients, output=output_filename)

    # send via IPFS
    res = client.add(output_filename)
    ipfs_hash_sent = res['Hash']
    print(ipfs_hash_sent)

    cur = cnx.cursor()
    query_str = 'INSERT INTO transaction_pool (contract_id, txn_hash) VALUES(\'' + contract_id + '\', \'' + ipfs_hash_sent + '\');'
    cur.execute(query_str)
    cnx.commit()
    return ipfs_hash_sent


def find_my_contracts(cnx, email_address):
    my_contracts = {
        'deployed_timestamp': [],
        'contract_id': [],
        'project_name': [],
        'engineer_email': [],
        'technician_email': [],
        'update_timestamp': [],
        'current_state': []
    }
    cur = cnx.cursor()
    query_str = "SELECT * FROM world_state WHERE engineer_email = \'" + email_address + '\' OR technician_email = \'' + email_address + '\';'
    cur.execute(query_str)
    result = cur.fetchall()
    for i in range(len(result)):
        my_contracts['deployed_timestamp'].append(result[i][1])
        my_contracts['contract_id'].append(result[i][2])
        my_contracts['project_name'].append(result[i][3])
        my_contracts['engineer_email'].append(result[i][4])
        my_contracts['technician_email'].append(result[i][5])
        my_contracts['update_timestamp'].append(result[i][6])
        my_contracts['current_state'].append(result[i][7])
    return my_contracts


def login(cnx, email_address):
    cur = cnx.cursor()
    query_str = "SELECT * FROM keyring WHERE email = \'" + email_address + '\';'
    cur.execute(query_str)
    result = cur.fetchall()
    try:
        role = result[0][3]
    except IndexError:
        role = 'undefined'
    return role


def register_user(email_address, pw, role):
    gpg = gnupg.GPG()
    cnx = mysql.connector.connect(user='node0', password='pw',
                                  host='127.0.0.1',
                                  database='amb')
    try:
        client = ipfshttpclient.connect('/ip4/127.0.0.1/tcp/5001/http')
    except:
        raise ConnectionError('Initialize an IPFS session')
    input_data = gpg.gen_key_input(name_email=email_address, passphrase=pw)
    key = str(gpg.gen_key(input_data))
    cur = cnx.cursor()
    query_str = "INSERT INTO keyring (email, public_key, role) VALUES (\'" + email_address + "\', \'" + key + "\', \'" + role.lower() + "\');"
    cur.execute(query_str)
    cnx.commit()

    # give this user access to blockchain file
    rec_blockchain = download_ledger(cnx, client, gpg)
    upload_ledger(cnx, client, gpg, rec_blockchain.ledger_path, get_timestamp(), len(rec_blockchain.chain))
    return rec_blockchain


