import pandas as pd
import numpy as np
import pickle
from bs4 import BeautifulSoup, UnicodeDammit
import requests

def save_to_pickle(data, fname):
    with open(fname, 'wb') as handle:
        pickle.dump(data, handle)
        
def merge_two_dicts(x, y):
    '''Given two dicts, merge them into a new dict as a shallow copy.'''
    z = x.copy()
    z.update(y)
    return z

def get_page_info(id_no, s=None):
    '''
    Extract restaurant information from Charlotte's health inspection website

    INPUT:  id_no = int, id # for ESTABLISHMENT
            s = request.Session(), [OPTIONAL] 
    OUTPUT: out = dict, establishment-level information
    '''
    if s is None:
        s = requests.Session()
    link = 'https://public.cdpehs.com/NCENVPBL/INSPECTION/ShowESTABLISHMENTPage.aspx'
    payload = {'ESTABLISHMENT':id_no, 'esttst_cty':60}
    z = s.get(link, params=payload)
    soup = BeautifulSoup(z.content, from_encoding='UTF-8')
    
    t = soup.findAll('table')[0]
    
    insp_info = np.array([y.text for y in t.findAll('td', attrs={'class':'ttc'})]).reshape(-1,4)
    
    if insp_info.shape[0] < 1:
        return None
    
    r = t.findAll('td', attrs={'class':'dfv'})
    rest_info = [x.text for x in r]
    
    return {'name'       :rest_info[0],
            'address'    :rest_info[2],
            'city'       :rest_info[8],
            'state'      :rest_info[9],
            'zip'        :rest_info[10],
            'type'       :rest_info[16],
            'county'     :rest_info[19],
            'inspections':insp_info}

def get_pages_in_range(start, n_loops, step_size=1000):
    '''
    Loop through all potential establishment id's to find valid restaurants. Return their information.

    INPUT:  start = int, location from which to start testing (i.e. 144000)
            n_loops = int, number of loops to use; a file is generated at each loop
            step_size = int, number of pages to check per loop 
    OUTPUT: dictionary of all valid restaurants (type = 1) from this set of pages
            NOTE: sub-files are also saved at each loop as a fail-safe measure
                  data/char/char_$start$.pkl
    '''
    s = requests.Session()
    dicts_main = {}
    for i in xrange(n_loops):
        dicts_loop = {}
        print '[%02d] START: %d' % (i, start)
        for i in xrange(step_size):
            dicts = get_page_info(start, s)
            if dicts is not None and dicts['type'][:3]=='1 -':
                dicts_loop[start] = dicts
                print '%d has %d inspections' % (start, dicts['inspections'].shape[0])
            start += 1
        save_to_pickle(dicts_loop, '../data/char/char_%s.pkl' % (start-1))
        dicts_main = merge_two_dicts(dicts_main, dicts_loop)
    return dicts_main

def build_restaurants(fname):
    '''
    Convert dictionary of restaurant info to a DataFrame

    INPUT:  fname = str, filename of pickled dictionary
    OUTPUT: R = DataFrame, cols = [address, city, county, inspections, name, state, type, zip]
    '''
    dict_final = pickle.load(open(fname,'rb'))
    R = pd.DataFrame.from_records(dict_final).T
    R = R[R.type == '1 - Restaurant']
    R.loc[:,'address'] = R.address.apply(lambda x: x.replace(' \r\n',''))
    return R
    
def build_inspections(R):
    '''
    Construct separate dataframe of inspection results

    INPUT:  R = DataFrame, cols = [address, city, county, inspections, name, state, type, zip]
    OUTPUT: I = DataFrame, cols = [id, date, score, grade, inspector]
    '''
    d = []
    for id_ in R.index:
        for row in R.loc[id_,'inspections']:
            d.append((id_,) + tuple(row))
    I = pd.DataFrame(d, columns=['id','date','score','grade','inspector'])
    I['date'] = pd.to_datetime(I['date'])
    I.loc[I.score==u'\xa0','score'] = 'NaN'
    I.score = I.score.astype(float)
    return I

def get_data(fname):
    '''
    Convert dictionary of restaurant info to restaurant- and inspection-level DataFrames

    INPUT:  fname = str, filename of pickled dictionary
    OUTPUT: R = DataFrame, cols = [address, city, county, name, state, type, zip]
            I = DataFrame, cols = [id, date, score, grade, inspector]
    '''
    R = build_restaurants(fname)
    I = build_inspections(R)
    R.drop('inspections', axis=1, inplace=True)
    return R, I