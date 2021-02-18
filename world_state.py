import os

class WorldState(object):
    def __init__(self, contract_subdir='contract_files'):
        contract_id_list = [x[0] for x in os.walk(directory)]