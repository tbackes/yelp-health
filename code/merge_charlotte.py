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

def parse_complex(a):
    l = a.split('\n')
    address = {}
    # if there is more than one line and the first line has length > 0
    if (len(l) > 1) and (len(l[0].strip()) > 0):
        # if the first character of the line is not a digit, and it does not seem to be an intersection
        if (re.search(r'\d',l[0].split()[0]) == None) and (l[0].find('&') < 0):
            address['complex'] = l[0]
            a = ' '.join(l[1:])
        else:
            a = a.replace('\n',' ')
            address['complex'] = ''
    else:
        a = a.replace('\n',' ')
        address['complex'] = ''

    return a, address

def parse_address(x, neighborhood=None):
    # strip neighborhood if necessary:
    if neighborhood is not None and len(neighborhood) > 0:
        for n in neighborhood:
            x = re.sub(r'\n(%s)\n' % n, ' ', x)

    a = x.lower()
    a = a.replace(' nc ', ' ')
    a = a.replace('-',' ')
    a = re.sub('[%s]' % re.escape(string.punctuation.replace('&','')), '', a)#, flags=re.U)
    a = re.sub(r'\b(and)\b',' & ', a)
    
    # standardize cities (applies to phoenix)
    cities = ['queen creek', 'cave creek', 'fountain hills', 'casa grande', 'paradise valley', 'litchfield park', 'sun city']
    for c in cities:
        a = a.replace(c,c.replace(' ','_'))
    
    # standardize common words
    abbr = {'road':'rd', 'street':'st', 'avenue':'av', 'ave':'av', 'drive':'dr', 'boulevard':'blvd',
            'lane':'ln', 'circle':'cir', 'building':'building', 'mount':'mt', 
            'n':'north', 'e':'east', 's':'south', 'w':'west', 'suite':'ste', 'bv':'blvd', 'suit':'ste',
            'pky':'pkwy', 'parkway':'pkwy',
            'first':'1st', 'second':'2nd', 'third':'3rd', 'fourth':'4th', 'fifth':'5th', 'sixth':'6th',
            'seventh':'7th', 'eighth':'8th', 'ninth':'9th', 'tenth':'10th'}
    for key, value in abbr.iteritems():
        a = re.sub(r'\b(%s)\b' % key, value, a) 
    
    address = {}

    # Check for complex:
    a, address = parse_complex(a)
    
    words = a.split()
    
    # If address is an intersection
    if a.find('&') >= 0:
        address = address.update(parse_intersection(a))
    # otherwise process street address
    else:
        address.update({'num':'', 'zip':'', 'city':'', 'street':'', 'suite':''})
        if len(words) >= 2:
            address.update({'zip':words[-1], 'city':words[-2]})
            
            # if there are more than 2 words, and the 1st word starts with a digit but is
            # not a word (1st, 2nd, etc.) than set num = the first word
            if len(words) > 2 and (re.search(r'\d',words[0]) is not None) and \
                (re.search(r'(rd)|(st)|(nd)|(th)',words[0])==None):
                    address['num'] = words[0]
        # if there is only one word, set this word as the city
        elif len(words) == 1:
            address['city'] = words[0]
        
        # remove the number from the address, and split on the city
        a = re.sub(r'\b(%s)\b' % address['num'], '', a)
        a = re.split(r'\b%s\b' % address['city'], a)
        
        # sometimes the city appears in the street name, so re-combine everything prior to the last split:
        if len(a) > 2:
            a = address['city'].join(a[:-1])
        else:
            a = a[0]

        # check for a suite before extracting the street
        if re.search(r'\b(ste)|(bldg)|(unit)\b',a):
            x = re.search(r'\b(ste)|(bldg)|(unit)\b', a)
            address['street'] = a[:a.find(x.group())]
            address['suite'] = a[a.find(x.group()):]
        else:
            address['street'] = a
        
        address = strip_address_letters(address)
        
        # remove extra white spaces
        for key, value in address.iteritems():
            address[key] = re.sub(r'\s+', ' ', value).strip()
    
    return pd.Series(address)

def strip_address_letters(address):
    # fix addresses with letters
    # (i.e. the 'N' or 'S' part of the street name was appended to the street number)
    # (i.e. an a, b or c indicating a unit number)
    if (len(address['num']) > 0):
        num = address['num']
        if (num[-1] == 'n'):
            address['num'] = num[:-1]
            address['street'] = 'north ' + address['street']
        elif (num[-1] == 's'):
            address['num'] = num[:-1]
            address['street'] = 'south ' + address['street']
        elif re.search(r'\D', num[-1]):
            address['num'] = re.findall(r'\d+', num)[0]
            address['suite'] = re.findall(r'\D+', num)[0] + address['suite']
    return address


def fuzz_comparisons(x):
    out = {}
    out['fuzz_partial_ratio'] = fuzz.partial_ratio(*x)
    out['fuzz_ratio'] = fuzz.ratio(*x)
    out['fuzz_token_sort_ratio'] = fuzz.token_sort_ratio(*x)
    out['fuzz_token_set_ratio'] = fuzz.token_set_ratio(*x)
    return pd.Series(out)


def clean_name(x):
    stop_words_rest = {'restaurant','bar','lounge','grill','sushi','cafe','deli',
                       'buffet','bakery','shop','grille'}
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


def clean_first_word(x):
    '''Convert to clean_name and return ony the first word'''
    x = clean_name(x)
    x = x.split()
    if len(x) < 1:
        return ''
    elif len(x) > 1 and x[0] in {'the','la','il','el','a','del','los','las'}:
        return x[1]
    else:
        return x[0]

def get_fuzz_scores(df, func = None, tag = ''):
    '''Create dataframe of fuzz_scores for name_matching'''
    if func is None:
        names = pd.Series(zip(df.name_, df.name_y_))
    else:
        names = pd.Series(zip(df.name_.apply(func), df.name_y_.apply(func)))

    fuzz_scores = names.apply(fuzz_comparisons)
    fuzz_scores.set_index(df.index, inplace=True)
    cols = fuzz_scores.columns.tolist()
    fuzz_scores['avg'] = fuzz_scores.mean(axis=1)
    fuzz_scores['max'] = fuzz_scores[cols].max(axis=1)
    fuzz_scores['avg_w'] = fuzz_scores[['avg','max']].mean(axis=1)
    fuzz_scores.columns = map(lambda x: x+tag, fuzz_scores.columns.tolist())
    return fuzz_scores


def append_fuzz_scores(df):
    '''Create fuzz_scores for name matching and append to original dataframe'''
    names_clean = pd.concat([df.name_.apply(clean_name), df.name_y_.apply(clean_name)], axis=1)
    names_clean.columns = ['name2_h','name2_y']
    
    fuzz_scores = get_fuzz_scores(df)
    fuzz_scores2 = get_fuzz_scores(df, clean_name, '_2')
    fuzz_scores3 = get_fuzz_scores(df, clean_first_word, '_3')
    
    return pd.concat([df, fuzz_scores, fuzz_scores2, fuzz_scores3, names_clean], axis=1)

def yelp_standard_address(x, neighborhood=None):
    '''Pre-process yelp address field'''
    # strip neighborhood if necessary:
    if neighborhood is not None and len(neighborhood) > 0:
        for n in neighborhood:
            print n
            x = re.sub(r'\n(%s)\n' % n, ' ', x)
            #x = re.sub(r'%s(%s)%s' % ('\n',n,'\n'), '', x)
            #x = x.replace('\n%s\n' % n.lower(),' ', )

    rep_list = {'\n':' ', 'Ste':'Suite', ',':'', 
                ' AZ ':' ', ' NC ':' ', ' NV ':' ', ' IL ':' ', ' WI ':' ', ' PA ':' '}
    for key, value in rep_list.iteritems():
        x = x.replace(key,value)

    return x

if __name__ == '__main__':
    pass
    # fname_business = '../data/yelp/yelp_dataset_challenge_academic_dataset/yelp_academic_dataset_business.json'

    # with open(fname_business) as f:
    #     B = pd.DataFrame(json.loads(line) for line in f)

    # NC = open_pickle('../data/phx/phoenix_R_full.pkl')

    # B_NC = B[(B.state=='NC')& (B.categories.apply(lambda x: 'Restaurants' in x))]
    # B_NC['address'] = B_NC.full_address.apply(lambda x: x.replace('\n',' ')\
    #                                                  .replace('Ste','Suite')\
    #                                                  .replace(',','')\
    #                                                  .replace(' NC ', ' '))

    # col = B_AZ.columns.values
    # col[3] = 'city_'
    # B_AZ.columns = col
    # B_AZ = pd.concat([B_AZ, B_address], axis=1)
    # B_AZ.head()

    # H_AZ = pd.concat([AZ, H_address], axis=1)
    # H_AZ.head()

    # keys = ['name_','num','street','city','zip']
    # if 'name_' not in B_AZ.columns.values:
    #     B_AZ['name_'] = B_AZ.name.apply(standard_name)
    # if 'name_' not in H_AZ.columns.values:
    #     H_AZ['name_'] = H_AZ.name.apply(standard_name)
    # temp = H_AZ.set_index(keys).join(B_AZ.set_index(keys), how='inner', rsuffix = 'y_')

    # H_x = H_AZ[~H_AZ.permit_id.isin(temp.permit_id)]
    # B_x = B_AZ[~B_AZ.business_id.isin(temp.business_id)]

    # keys = ['num','street','city','zip']
    # temp2 = H_x.set_index(keys).join(B_x.set_index(keys), how='inner', rsuffix = 'y_')

    # temp2 = append_fuzz_scores(temp2)

    # AZ_final = pd.concat([temp,temp2[(fuzz_scores.max>=65) & (fuzz_scores2.avg_w_2>=65)]], axis=0)

    # save_to_pickle(AZ_final, '../data/phx/phoenix_yelp_merge.pkl')




