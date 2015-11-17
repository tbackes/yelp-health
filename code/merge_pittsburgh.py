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
    elif len(x) > 0:
        address = {'num':'', 'street':x[0], 'suite':''}
    else:
        address = {'num':'', 'street':'', 'suite':''}
        
    address = lib.strip_address_letters(address)
        
    # remove extra white spaces
    for key, value in address.iteritems():
        address[key] = re.sub(r'\s+', ' ', value).strip()
        
    address['suite'] = lib.clean_string(address['suite'])
    return pd.Series(address)


def preprocess_PA():
    PA = lib.open_pickle('../data/pitt/pitt_inspections_FINAL.pkl')
    
    PA['name_'] = PA.name.apply(lib.standard_name)
    PA['city_'] = PA.city.apply(lambda x: x.lower())
    PA['id_'] = PA.client_id

    PA = pd.concat([PA, PA.address.apply(split_address)], axis=1)
    return PA


if __name__ == '__main__':
    B_PA = lib.preprocess_yelp(lib.get_yelp_businesses(), 'PA')
    PA = preprocess_PA()

    merge_level1 = lib.merge_exact_match(PA, B_PA)
    merge_level2 = lib.merge_partial_match2(PA, B_PA, merge_level1, merge_level=2, dump_tag='pitt_32')
    merge_level3 = lib.merge_partial_match2(PA, B_PA, merge_level2, merge_level=3, dump_tag='pitt_33')
    merge_level4 = lib.merge_partial_match2(PA, B_PA, merge_level3, merge_level=4, dump_tag='pitt_34')


    # merge_level2.to_csv('../data/pitt/merge_dump_22.csv', encoding='utf-8')
    # merge_level3.to_csv('../data/pitt/merge_dump_23.csv', encoding='utf-8')
    # merge_level4.to_csv('../data/pitt/merge_dump_24.csv', encoding='utf-8')

    lib.save_to_pickle(merge_level4, '../data/pitt/pittsburgh_yelp_merge.pkl')






