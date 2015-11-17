import pandas as pd
import numpy as np
import pickle
import re
import string
import merge_main as lib
pd.options.mode.chained_assignment = None  # default='warn'


def preprocess_WI():
    H = lib.open_pickle('../data/mad/mad_health_FINAL.pkl')
    
    H['name_'] = H.name.apply(lib.standard_name)
    H['id_'] = H.index

    H_address = H.address.apply(lambda x: lib.parse_address(x,ampersand=True))
    col = H_address.columns.values
    col[0] = 'city_'
    H_address.columns = col

    H = pd.concat([H, H_address], axis=1)
    return H


if __name__ == '__main__':
    B_WI = lib.preprocess_yelp(lib.get_yelp_businesses(), 'WI', ampersand=True)
    WI = preprocess_WI()

    merge_level1 = lib.merge_exact_match(WI, B_WI)
    merge_level2 = lib.merge_partial_match2(WI, B_WI, merge_level1, merge_level=2, dump_tag='mad_32')
    merge_level3 = lib.merge_partial_match2(WI, B_WI, merge_level2, merge_level=3, dump_tag='mad_33')
    merge_level4 = lib.merge_partial_match2(WI, B_WI, merge_level3, merge_level=4, dump_tag='mad_34')


    # merge_level2.to_csv('../data/mad/merge_dump_22.csv', encoding='utf-8')
    # merge_level3.to_csv('../data/mad/merge_dump_23.csv', encoding='utf-8')

    lib.save_to_pickle(merge_level4, '../data/mad/madison_yelp_merge.pkl')
