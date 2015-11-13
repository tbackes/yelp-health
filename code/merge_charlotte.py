import pandas as pd
import numpy as np
import pickle
import re
import string
import merge_main as lib
pd.options.mode.chained_assignment = None  # default='warn'


def split_address(x):
    address = {'suite':''}
    x = x.lower().replace('\r','').replace('\n','')
    x = x.replace(' ste-',' ste ')
    
    words = x.split()
    # some street numbers have a dash, append the second part to suite
    if words[0].find('-') > 0:
        n = words[0].split('-')
        address['suite'] += n[-1] + ' '
        x = ' '.join([n[0]] + words[1:])
    
    x = x.replace('-',' ')
    x = re.sub('[%s]' % re.escape(string.punctuation.replace('&','')), '', x)
    abbr = lib.address_abbr()
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
    else:
        address = {'num':'', 'street':x[0], 'suite':''}
        
    address = lib.strip_address_letters(address)
        
    # remove extra white spaces
    for key, value in address.iteritems():
        address[key] = re.sub(r'\s+', ' ', value).strip()
        
    return pd.Series(address)


def preprocess_NC():
    H = lib.open_pickle('../data/char/char_FULL_04.pkl')
    NC = pd.DataFrame.from_records(H).T
    
    NC['city_'] = NC.city.apply(lambda x: x.lower().strip())
    NC['name_'] = NC.name.apply(lib.standard_name)
    NC['id_'] = NC.index

    NC = pd.concat([NC, NC.address.apply(split_address)], axis=1)
    return NC


if __name__ == '__main__':
    B_NC = lib.preprocess_yelp(lib.get_yelp_businesses(), 'NC')
    NC = preprocess_NC()

    merge_level1 = lib.merge_exact_match(NC, B_NC)
    merge_level2 = lib.merge_partial_match(NC, B_NC, merge_level1, merge_level=2)
    merge_level3 = lib.merge_partial_match(NC, B_NC, merge_level2, merge_level=3)


    merge_level2.to_csv('../data/char/merge_dump_22.csv', encoding='utf-8')
    merge_level3.to_csv('../data/char/merge_dump_23.csv', encoding='utf-8')

    lib.save_to_pickle(merge_level3, '../data/char/charlotte_yelp_merge2.pkl')


