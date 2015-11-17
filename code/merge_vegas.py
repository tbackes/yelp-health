import pandas as pd
import numpy as np
import pickle
import re
import string
import merge_main as lib
pd.options.mode.chained_assignment = None  # default='warn'


def split_address(x):
    if type(x)==float:
        x = ''
    address = {'suite':''}
    x = x.lower().replace('\r','').replace('\n','')
    x = x.replace(' ste-',' ste ')
    
    words = x.split()
    # some street numbers have a dash, append the second part to suite
    if len(words)>0 and words[0].find('-') > 0:
        n = words[0].split('-')
        address['suite'] += n[-1] + ' '
        x = ' '.join([n[0]] + words[1:])
    
    x = x.replace('-',' ')
    x = re.sub('[%s]' % re.escape(string.punctuation.replace('&','')), '', x)
    abbr = {'road':'rd', 'street':'st', 'avenue':'av', 'ave':'av', 'drive':'dr', 'boulevard':'blvd',
            'lane':'ln', 'circle':'cir', 'building':'building', 'mount':'mt', 
            'n':'north', 'e':'east', 's':'south', 'w':'west', 'suite':'ste', 'bv':'blvd', 'suit':'ste',
            'pky':'pkwy', 'parkway':'pkwy',
            'first':'1st', 'second':'2nd', 'third':'3rd', 'fourth':'4th', 'fifth':'5th', 'sixth':'6th',
            'seventh':'7th', 'eighth':'8th', 'ninth':'9th', 'tenth':'10th'}
    for key, value in abbr.iteritems():
        x = re.sub(r'\b(%s)\b' % key, value, x) 
    x = x.strip()
    
    n = re.findall(r'^(\d+\D?)\b',x)
    s = re.search(r'\b(ste\W?\D?\W?\d*\W?\D?)|(unit\W?\D?\W?\d*\W?\D?)\Z', x)
    if len(n) > 0 and s is not None and len(s.group()) > 0:
        i = re.search(r'\b(ste)|(bldg)|(unit)\b', x)
        address['num'] = n[0]
        address['street'] = re.sub(r'^(\d+\D?)\b', '', x[:x.find(i.group())])
        address['suite'] += x[x.find(i.group()):]
    elif len(n) > 0:
        address['num'] = n[0]
        address['street'] = re.sub(r'^(\d+\D?)\b', '', x)
    elif len(x) > 0:
        address = {'num':'', 'street':x[0], 'suite':''}
    else:
        address = {'num':'', 'street':'', 'suite':''}
        
    address = lib.strip_address_letters(address)
        
    # remove extra white spaces
    for key, value in address.iteritems():
        address[key] = re.sub(r'\s+', ' ', value).strip()
        
    return pd.Series(address)

def preprocess_NV():
    H = pd.read_csv('../data/vegas/restaurant_establishments.csv', delimiter=';', header=None, skiprows=1)
    H.columns = ['permit_number', 'facility_id', 'PE', 'restaurant_name',  'location_name',
                 'address', 'latitude', 'longitude', 'city_id', 
                 'city_name', 'zip_code', 'nciaa', 'plan_review', 'record_status',
                 'current_grade', 'current_demerits', 'date_current', 'previous_grade', 
                 'date_previous', 'misc','empty']
    
    H['id_'] = H.facility_id
    H['name_'] = H.restaurant_name.apply(lib.standard_name)
    H['city_'] = H.city_name.apply(lambda x: '_'.join(x.lower().strip().split()))
    H['zip'] = H.zip_code.apply(lambda x: np.nan if type(x)==float else x[:5])

    H = pd.concat([H, H.address.apply(split_address)], axis=1)
    return H


if __name__ == '__main__':
    B_NV = lib.preprocess_yelp(lib.get_yelp_businesses(), 'NV')
    NV = preprocess_NV()

    merge_level1 = lib.merge_exact_match(NV, B_NV)
    merge_level2 = lib.merge_partial_match(NV, B_NV, merge_level1, merge_level=2, dump_tag='vegas_32')
    merge_level3 = lib.merge_partial_match(NV, B_NV, merge_level2, merge_level=3, dump_tag='vegas_33')
    merge_level4 = lib.merge_partial_match(NV, B_NV, merge_level3, merge_level=4, dump_tag='vegas_34')


    merge_level2.to_csv('../data/vegas/merge_dump_22.csv', encoding='utf-8')
    #merge_level3.to_csv('../data/vegas/merge_dump_23.csv', encoding='utf-8')

    lib.save_to_pickle(merge_level1, '../data/vegas/vegas_yelp_merge.pkl')
