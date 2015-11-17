import pandas as pd
import numpy as np
import pickle
import re
import string
import merge_main as lib
pd.options.mode.chained_assignment = None  # default='warn'

def preprocess_AZ():
    AZ = lib.open_pickle('../data/phx/phoenix_R_full.pkl')
    H_address = AZ.address.apply(lib.parse_address)
    H_address.set_index(AZ.index, inplace=True)
    col = H_address.columns.values
    col[0] = 'city_'
    H_address.columns = col

    H_AZ = pd.concat([AZ, H_address], axis=1)
    H_AZ['name_'] = H_AZ.name.apply(lib.standard_name)
    H_AZ['id_'] = H_AZ.permit_id

    return H_AZ

if __name__ == '__main__':
    B_AZ = lib.preprocess_yelp(lib.get_yelp_businesses(), 'AZ')
    AZ = preprocess_AZ()

    merge_level1 = lib.merge_exact_match(AZ, B_AZ)
    merge_level2 = lib.merge_partial_match2(AZ, B_AZ, merge_level1, merge_level=2, dump_tag='phx_32')
    merge_level3 = lib.merge_partial_match2(AZ, B_AZ, merge_level2, merge_level=3, dump_tag='phx_33')
    merge_level4 = lib.merge_partial_match2(AZ, B_AZ, merge_level3, merge_level=4, dump_tag='phx_34')

    lib.save_to_pickle(merge_level4, '../data/phx/phoenix_yelp_merge.pkl')