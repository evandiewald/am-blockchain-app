import gnupg
import ipfshttpclient
import mysql.connector
from blockchain import Blockchain, get_timestamp
import time
import json
import os


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



def download_ledger(cnx, client, gpg, gpg_pw='pw'):
    # get hash from db
    cur = cnx.cursor()
    query_str = 'SELECT ipfs_hash, timestamp FROM blockchain_hashes ORDER BY id DESC LIMIT 1;'
    cur.execute(query_str)
    result = cur.fetchall()
    ipfs_hash_rec = " ".join(result[0])
    my_timestamp = " ".join(result[1])
    print(result)
    # sanity check
    # assert ipfs_hash_rec == ipfs_hash_sent

    # download from IPFS
    client.get(ipfs_hash_rec)

    # decrypt
    ledger_path = 'blockchain_files/' + my_timestamp
    with open(ipfs_hash_rec, 'rb') as f:
        status = gpg.decrypt_file(f, passphrase=gpg_pw, output=ledger_path)

    rec_blockchain = Blockchain(ledger_path=ledger_path)

    # cnx.close()
    return rec_blockchain

# TODO: similar functions to create & upload keys


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
    deployed_timestamp = " ".join(result[0])
    project_name = " ".join(result[1])
    engineer_email = " ".join(result[2])
    technician_email = " ".join(result[3])
    update_timestamp = " ".join(result[4])
    current_state = " ".join(result[5])
    return deployed_timestamp, project_name, engineer_email, technician_email, update_timestamp, current_state


def update_world_state(cnx, contract_id, update_timestamp, current_state):
    cur = cnx.cursor()
    query_str = 'UPDATE world_state SET update_timestamp = \'' + update_timestamp + '\', current_state = \'' + current_state + '\' WHERE contract_id = ' + contract_id + '\';'
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


def read_my_transactions(cnx, client, gpg, contract_id):
    cur = cnx.cursor()
    query_str = 'SELECT txn_hash, block_hash FROM transaction_pool WHERE contract_id = \'' + contract_id + '\';'
    cur.execute(query_str)
    result = cur.fetchall()
    ipfs_hash_rec = " ".join(result[0])
    my_timestamp = " ".join(result[1])
    print(result)
    # sanity check
    # assert ipfs_hash_rec == ipfs_hash_sent

    # # download from IPFS
    # client.get(ipfs_hash_rec)
    #
    # # decrypt
    # ledger_path = 'blockchain_files/' + my_timestamp
    # with open(ipfs_hash_rec, 'rb') as f:
    #     status = gpg.decrypt_file(f, passphrase=gpg_pw, output=ledger_path)
    #
    # rec_blockchain = Blockchain(ledger_path=ledger_path)

    # cnx.close()


def insert_transaction(cnx, client, gpg, contract_id, transaction_data, recipients):
    contract_dir = 'contract_files/' + contract_id
    update_timestamp = get_timestamp()
    if not os.path.isdir(contract_dir):
        os.mkdir(path=contract_dir)
    fname = contract_dir + '/' + update_timestamp + '.txt'
    # write transaction data to json
    with open(fname, 'wb') as outfile:
        json.dump(transaction_data, outfile)

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
