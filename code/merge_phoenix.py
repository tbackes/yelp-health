import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import json
import pickle
import re
import string
from fuzzywuzzy import fuzz
pd.options.mode.chained_assignment = None  # default='warn'


def standard_name(x):
    x = x.replace('@',' at ')
    x = x.replace('-',' ')
    x = x.replace('/',' ')
    x = re.sub(r'\b(grille)\b', 'grill', x)
    x = re.sub(r'\bNo \d+\Z','',x)
    x = re.split(r'\b(at)\b', x)[0]
    return re.sub('[%s]' % re.escape(string.punctuation), '', x.lower())

def parse_intersection(a):
    address = {}
    words = a.split()
    address['city'] = words[-2]
    address['zip'] = words[-1]
    a = re.split(r'\b(%s)\b' % address['city'], a)
    address['num'] = ''
    address['street'] = a[0]
    address['suite'] = ''
    return address

#def parse_complex(a):
    
#     return address

def parse_address2(x):
    a = x.lower()
    a = a.replace(' az ', ' ')
    a = re.sub('[%s]' % re.escape(string.punctuation.replace('&','')), '', a)#, flags=re.U)
    cities = ['queen creek', 'cave creek', 'fountain hills', 'casa grande', 'paradise valley', 'litchfield park', 'sun city']
    for c in cities:
        a = a.replace(c,c.replace(' ','_'))
    
    abbr = {'road':'rd', 'street':'st', 'avenue':'av', 'ave':'av', 'drive':'dr', 'boulevard':'blvd',
            'n':'north', 'e':'east', 's':'south', 'w':'west', 'suite':'ste'}
    for key, value in abbr.iteritems():
        a = re.sub(r'\b(%s)\b' % key, value, a) 
    
    
    address = {}
    # Check for complex:
    l = a.split('\n')
    if (len(l) > 1) and (len(l[0].strip()) > 0):
        if (re.search(r'\d',l[0].split()[0]) == None) and (l[0].find('&') < 0):
            address['complex'] = l[0]
            a = ' '.join(l[1:])
        else:
            a = a.replace('\n',' ')
            address['complex'] = ''
    else:
        a = a.replace('\n',' ')
        address['complex'] = ''
    
    words = a.split()
    
    # If address is an intersection
    if a.find('&') >= 0:
        address = parse_intersection(a)
    else:
        if len(words) > 2:
            if (re.search(r'\d',words[0]) is not None) and (re.search(r'(rd)|(st)|(nd)|(th)',words[0])==None):
                address['num'] = words[0]
            else:
                address['num'] = ''
            address['zip'] = words[-1]
            address['city'] = words[-2]
        elif len(words) == 2:
            address['num'] = ''
            address['zip'] = words[-1]
            address['city'] = words[-2]
        elif len(words) == 1:
            address['num'] = ''
            address['zip'] = ''
            address['city'] = words[0]
        else:
            address['num'] = ''
            address['zip'] = ''
            address['city'] = ''
        a = re.sub(r'\b(%s)\b' % address['num'], '', a)
        a = re.split(r'\b(%s)\b' % address['city'], a)

        #return a
        if re.search(r'\b(ste)\b',a[0]):
            a = re.split(r'\b(ste)\b', a[0])
            address['street'] = a[0].strip()
            address['suite'] = a[2].strip()
        else:
            address['street'] = a[0].strip()
            address['suite'] = ''
            
        # fix addresses with missing spaces:
        if (len(address['num']) > 0):
            if (address['num'][-1] == 'n'):
                address['num'] = address['num'][:-1]
                address['street'] = 'north ' + address['street']
            elif (address['num'][-1] == 's'):
                address['num'] = address['num'][:-1]
                address['street'] = 'south ' + address['street']
    
    return pd.Series(address)


def fuzz_comparisons(x):
    out = {}
    out['fuzz_partial_ratio'] = fuzz.partial_ratio(*x)
    out['fuzz_ratio'] = fuzz.ratio(*x)
    out['fuzz_token_sort_ratio'] = fuzz.token_sort_ratio(*x)
    out['fuzz_token_set_ratio'] = fuzz.token_set_ratio(*x)
    return pd.Series(out)

stop_words_rest = ['restaurant','bar','lounge','grill','sushi','cafe','deli','buffet','bakery','shop','grille']
def clean_name(x):
    for w in stop_words_rest:
        x = re.sub(r'\b(%s)\b' % w, '', x)
    x = x.strip()
    return x

def save_to_pickle(data, fname):
    with open(fname, 'wb') as handle:
        pickle.dump(data, handle)


def open_pickle(f_name):
    with open(f_name, 'rb') as f:
        data = pickle.load(f)
    return data

fname_business = '../data/yelp/yelp_dataset_challenge_academic_dataset/yelp_academic_dataset_business.json'

with open(fname_business) as f:
    B = pd.DataFrame(json.loads(line) for line in f)

AZ = open_pickle('../data/phx/phoenix_R_full.pkl')

B_AZ = B[(B.state=='AZ')& (B.categories.apply(lambda x: 'Restaurants' in x))]
B_AZ['address'] = B_AZ.full_address.apply(lambda x: x.replace('\n',' ')\
                                                     .replace('Ste','Suite')\
                                                     .replace(',','')\
                                                     .replace(' AZ ', ' '))
B_address = B_AZ.full_address.apply(parse_address2)
H_address = AZ.address.apply(parse_address2)

col = B_AZ.columns.values
col[3] = 'city_'
B_AZ.columns = col
B_AZ = pd.concat([B_AZ, B_address], axis=1)
B_AZ.head()

H_AZ = pd.concat([AZ, H_address], axis=1)
H_AZ.head()

keys = ['name_','num','street','city','zip']
if 'name_' not in B_AZ.columns.values:
    B_AZ['name_'] = B_AZ.name.apply(standard_name)
if 'name_' not in H_AZ.columns.values:
    H_AZ['name_'] = H_AZ.name.apply(standard_name)
temp = H_AZ.set_index(keys).join(B_AZ.set_index(keys), how='inner', rsuffix = 'y_')

H_x = H_AZ[~H_AZ.permit_id.isin(temp.permit_id)]
B_x = B_AZ[~B_AZ.business_id.isin(temp.business_id)]

keys = ['num','street','city','zip']
temp2 = H_x.set_index(keys).join(B_x.set_index(keys), how='inner', rsuffix = 'y_')



names = pd.Series(zip(temp2.name_, temp2.name_y_))
names2 = pd.Series(zip(temp2.name_.apply(clean_name), temp2.name_y_.apply(clean_name)))
names_clean = pd.concat([temp2.name_.apply(clean_name), temp2.name_y_.apply(clean_name)], axis=1)
names_clean.columns = ['name2_h','name2_y']

fuzz_scores = names.apply(fuzz_comparisons)
fuzz_scores.set_index(temp2.index, inplace=True)
fuzz_scores['max'] = fuzz_scores.max(axis=1)

fuzz_scores2 = names2.apply(fuzz_comparisons)
fuzz_scores2.set_index(temp2.index, inplace=True)
fuzz_scores2['avg'] = fuzz_scores2.mean(axis=1)
fuzz_scores2['max'] = fuzz_scores2[['fuzz_partial_ratio','fuzz_ratio','fuzz_token_sort_ratio','fuzz_token_set_ratio']].max(axis=1)
fuzz_scores2['avg_w'] = fuzz_scores2[['avg','max']].mean(axis=1)
fuzz_scores2.columns = map(lambda x: x+'_2', fuzz_scores2.columns.tolist())

temp2 = pd.concat([temp2, fuzz_scores,fuzz_scores2,names_clean], axis=1)

AZ_final = pd.concat([temp,temp2[(fuzz_scores.max>=65) & (fuzz_scores2.avg_w_2>=65)]], axis=0)

save_to_pickle(AZ_final, '../data/phx/phoenix_yelp_merge.pkl')




