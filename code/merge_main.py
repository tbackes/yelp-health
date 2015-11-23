import pandas as pd
import numpy as np
import pickle
import re
import string
import json
from fuzzywuzzy import fuzz
from unidecode import unidecode
pd.options.mode.chained_assignment = None  # default='warn'

def clean_string(text):
    return unidecode(text)#.encode('utf-8').decode('utf-8'))

def save_to_pickle(data, fname):
    with open(fname, 'wb') as handle:
        pickle.dump(data, handle)


def open_pickle(f_name):
    with open(f_name, 'rb') as f:
        data = pickle.load(f)
    return data

def standard_name(x):
    if type(x) == float:
        x = str(x)

    try:
        x = clean_string(x)
    except Exception as e:
        print x, e

    if x.find('#') > 0:
        x = x.split('#')[0]
    if x.find('@') > 0:
        x = x.split('@')[0]

    # Insert space between lower-upper combos (McMan -> Mc Man; LaFiera -> La Fiera)
    for w in re.findall(r'[a-z][A-Z]', x):
        x = x.replace(w, w[0] + ' ' + w[1])
    
    # Convert upper-lower combos to all lower case (Rest -> rest; THis -> this)
    for w in re.findall(r'[A-Z]+[a-z]',x):
        x = x.replace(w, w.lower())

    # Remove any spaces between initials (only detects upper case) (J D --> JD; S. S. E. -> S.S.E.) 
    for w in re.findall(r'(?=([A-Z]\.? [A-Z]))', x):
        x = x.replace(w, w.replace(' ',''))
    
    rep_list = {'-':' ', '/':' ', '&':' and '}
    sub_list = {'grille':'grill', 'ristorante':'restaurant','restaurante':'restaurant',
                'italiano':'italian', 'mexicano':'mexican', 'mexicana':'mexican'}
    x = x.lower()
    for key, value in rep_list.iteritems():
        x = x.replace(key, value)
    for key, value in sub_list.iteritems():
        x = re.sub(r'\b(%s)\b' % key, value, x)
    
    x = x.strip()
    x = re.sub(r'(\#\d+)\Z','',x)
    x = re.sub(r'\bnumber\b',' no ',x)
    x = re.sub(r'\bnum\b',' no ',x)
    x = re.sub(r'\bno \d+\Z','',x)
    x = re.split(r'\b(at)\b', x)[0].strip()
    return re.sub('[%s]' % re.escape(string.punctuation), '', x)

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

def address_abbr():
    return {'road':'rd', 'street':'st', 'avenue':'av', 'ave':'av', 'drive':'dr', 'boulevard':'blvd',
            'lane':'ln', 'circle':'cir', 'building':'building', 'mount':'mt', 'square':'sq',
            'n':'north', 'e':'east', 's':'south', 'w':'west', 'suite':'ste', 'bv':'blvd', 'suit':'ste',
            'pky':'pkwy', 'parkway':'pkwy', 'terrace':'terr', 'trail':'trl', 'place':'pl',
            'first':'1st', 'second':'2nd', 'third':'3rd', 'fourth':'4th', 'fifth':'5th', 'sixth':'6th',
            'seventh':'7th', 'eighth':'8th', 'ninth':'9th', 'tenth':'10th'}

def standardize_cities(a):
    # standardize cities with different abbreviations/spellings
    cities = {'nv': {'n las vegas':'north_las_vegas', 'n. las vegas':'north_las_vegas', 
                     'north las vegas':'north_las_vegas'}, 
              'wi': {'mc farland':'mcfarland', 'de forest':'deforest'},
              'pa': {'mc kees rocks':'mkees_rocks'}}
    for state, city_list in cities.iteritems():
        for key, value in city_list.iteritems():
            a = re.sub(r'\n(%s, %s)\b' % (key, state), '\n%s, %s' % (value, state), a)

    # replace spaces with underscores for multiword cities
    cities = {'nv': ['las vegas', 'boulder city', 'spring valley', 'nellis afb', 'summerlin south', 
                     'clark county', 'green valley'],
              'az': ['queen creek', 'cave creek', 'fountain hills', 'casa grande', 'paradise valley', 
                     'litchfield park', 'sun city'],
              'wi': ['cottage grove', 'sun prairie'],
              'pa': ['west mifflin', 'mount lebanon', 'mckees rocks', 'west homestead', 'castle shannon']}
    for state, city_list in cities.iteritems():
        for c in city_list:
            a = re.sub(r'\n(%s, %s)\b' % (c, state), '\n%s, %s' % (c.replace(' ','_'), state), a)

    return a


def parse_address(x, neighborhood=None, ampersand=True):
    # strip neighborhood if necessary:
    if neighborhood is not None and len(neighborhood) > 0:
        for n in neighborhood:
            x = re.sub(r'\n(%s)\n' % n, ' \n', x)

    a = x.lower()

    # standardize nevada cities
    a = standardize_cities(a)

    for state in ['az','nv','nc','il','wi','pa']:
        a = a.replace(' %s ' % state, ' ')
    a = a.replace('-',' ')

    if ampersand:
        a = re.sub('[%s]' % re.escape(string.punctuation.replace('&','').replace('_','')), '', a)#, flags=re.U)
    else:
        a = re.sub('[%s]' % re.escape(string.punctuation.replace('_','')), '', a)#, flags=re.U)
    a = re.sub(r'\b(and)\b',' & ', a)
    
    # standardize common words
    abbr = address_abbr()
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
            i = a.find(' '+x.group())
            address['street'] = a[:i]
            address['suite'] = a[i:]
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


def clean_name(x):
    stop_words_rest = {'restaurant','bar','lounge','grill','sushi','cafe','deli',
                       'buffet','bakery','shop','grille','market'}
    for w in stop_words_rest:
        x = re.sub(r'\b(%s)\b' % w, '', x)
    x = x.strip()
    return x

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

def get_yelp_businesses():
    fname_business = '../data/yelp/yelp_dataset_challenge_academic_dataset/yelp_academic_dataset_business.json'
    with open(fname_business) as f:
        B = pd.DataFrame(json.loads(line) for line in f)
    return B


def preprocess_yelp(B, state_abbr, ampersand=True):
    B_state = B[(B.state==state_abbr)& (B.categories.apply(lambda x: 'Restaurants' in x))]
    B_state['address'] = B_state.full_address.apply(lambda x: x.replace('\n',' ')\
                                                         .replace('Ste','Suite')\
                                                         .replace(',','')\
                                                         .replace(' %s ' % state_abbr, ' '))
    
    B_state['name_'] = B_state.name.apply(standard_name)
    B_address = pd.Series(zip(B_state.full_address, B_state.neighborhoods)).apply(lambda x: parse_address(x[0],x[1],ampersand))
    B_address.set_index(B_state.index, inplace=True)
    col = B_address.columns.values
    col[0] = 'city_'
    B_address.columns = col

    B_state = pd.concat([B_state, B_address], axis=1)

    return B_state

def merge_yelp_to_health(H, B, ind):
    return H.set_index(ind).join(B.set_index(ind), how='inner', rsuffix = 'y_')

def fuzz_comparisons(x):
    out = {}
    out['fuzz_partial_ratio'] = fuzz.partial_ratio(*x)
    out['fuzz_ratio'] = fuzz.ratio(*x)
    out['fuzz_token_sort_ratio'] = fuzz.token_sort_ratio(*x)
    out['fuzz_token_set_ratio'] = fuzz.token_set_ratio(*x)
    return pd.Series(out)

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

def merge_exact_match(STATE, B_state):
    ind1 = ['name_','num','street','city_','zip']
    MERGE_level1 = merge_yelp_to_health(STATE, B_state, ind1)
    #STATE.set_index(ind1).join(B_state.set_index(ind1), how='inner', rsuffix = 'y_')
    print MERGE_level1.shape
    return MERGE_level1

def to_int(x):
    try:
        out = int(x)
    except:
        out = np.nan
    return out

def merge_partial_match(STATE, B_state, MERGE_prev, merge_level=0, dump_tag=None):
    if merge_level == 2:
        ind = ['num','street','city_','zip']
    elif merge_level == 3:
        ind = ['city_','zip']

    H_x = STATE[~STATE.id_.isin(MERGE_prev.id_)]
    B_x = B_state[~B_state.business_id.isin(MERGE_prev.business_id)]

    merged = merge_yelp_to_health(H_x, B_x, ind)
    print merged.shape

    merged_fuzz = append_fuzz_scores(merged)

    if dump_tag is not None:
        merged_fuzz.to_csv('../data/pitt/merge_dump_%s.csv' % dump_tag, encoding='utf-8')

    ind_A = (merged_fuzz['max'] >= 75) & (merged_fuzz.avg_w_2 >= 75)
    ind_B = (merged_fuzz['max'] >= 60) & (merged_fuzz.avg_w_2 >= 60) & (merged_fuzz.avg_w_3 >= 80)

    if merge_level == 2:
        ind_merge = ind_A | ind_B
    elif merge_level == 3:
        ind_C = merged_fuzz.num == merged_fuzz.numy_
        ind_D = (merged_fuzz.street == merged_fuzz.street) & \
                 (abs(merged_fuzz.num.apply(to_int) - merged_fuzz.numy_.apply(to_int)) <= 100)
        ind_merge = (ind_A | ind_B) & (ind_C | ind_D)

    MERGE_partial = pd.concat([MERGE_prev, merged_fuzz[ind_merge]])

    print MERGE_partial.shape
    return MERGE_partial

def merge_partial_match2(STATE, B_state, MERGE_prev, merge_level=0, dump_tag=None):
    if merge_level == 2:
        ind = ['num','street','city_','zip']
    elif merge_level == 3:
        ind = ['num','city_','zip']
    elif merge_level == 4:
        ind = ['street','city_','zip']

    H_x = STATE[~STATE.id_.isin(MERGE_prev.id_)]
    B_x = B_state[~B_state.business_id.isin(MERGE_prev.business_id)]

    merged = merge_yelp_to_health(H_x, B_x, ind)
    print merged.shape

    merged_fuzz = append_fuzz_scores(merged)

    if dump_tag is not None:
        merged_fuzz.to_csv('../data/dump/merge_dump_%s.csv' % dump_tag, encoding='utf-8')

    ind_A = (merged_fuzz['max'] >= 75) & (merged_fuzz.avg_w_2 >= 75)
    ind_B = (merged_fuzz['max'] >= 60) & (merged_fuzz.avg_w_2 >= 60) & (merged_fuzz.avg_w_3 >= 80)

    if merge_level < 4:
        ind_merge = ind_A | ind_B
    elif merge_level == 4:
        ind_C = abs(merged_fuzz.num.apply(to_int) - merged_fuzz.numy_.apply(to_int)) <= 100
        ind_merge = (ind_A | ind_B) & ind_C 

    MERGE_partial = pd.concat([MERGE_prev, merged_fuzz[ind_merge]])

    print MERGE_partial.shape
    return MERGE_partial
