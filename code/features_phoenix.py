import pandas as pd
import numpy as np
import pickle
import re
import string
from merge_vegas import open_pickle, save_to_pickle
import features_main as lib

pd.options.mode.chained_assignment = None  # default='warn'


def get_AZ_inspections(df, drop_flag=True):
    I = open_pickle('../data/phx/phoenix_I_full.pkl')

    I[I.n_priority == 'NA'].n_priority = -1
    I['id_'] = I.permit_id

    I = I[I.permit_id.isin(df.permit_id.unique())]
    if drop_flag:
        I.drop_duplicates(inplace=True) 

    return I

def viol_type(x):
    out = ''
    if x.lower().find(' p:') >= 0:
        out += 'P'
    if x.lower().find(' pf:') >= 0:
        out += 'F'
    if x.lower().find(' c:') >= 0:
        out += 'C'
    return out

def count_viol_type(x):
    p = len(re.findall('\W(p:)\W', x.lower()))
    f = len(re.findall('\W(pf:)\W', x.lower()))
    c = len(re.findall('\W(c:)\W', x.lower()))
    return pd.Series({'n_priority':p, 'n_foundation':f, 'n_core':c})

def get_AZ_violations(df):
    V = open_pickle('../data/phx/phoenix_V_full.pkl')

    V['type'] = V.comments.apply(viol_type)
    V = pd.concat([V, V.comments.apply(count_viol_type).set_index(V.index)], axis=1)
    
    df['n_violations'] = V.groupby(['id_','inspec_id']).count().reset_index(level=0).code
    df['v_core'] = V[V.n_core > 0].groupby(['id_','inspec_id']).count().reset_index(level=0).code
    df['sum_core'] = V[V.n_core > 0].groupby(['id_','inspec_id']).sum().reset_index(level=0).code
    df['v_foundation'] = V[V.n_foundation > 0].groupby(['id_','inspec_id']).count().reset_index(level=0).code
    df['sum_foundation'] = V[V.n_foundation > 0].groupby(['id_','inspec_id']).sum().reset_index(level=0).code
    df['v_priority'] = V[V.n_priority > 0].groupby(['id_','inspec_id']).count().reset_index(level=0).code
    df['sum_priority'] = V[V.n_priority > 0].groupby(['id_','inspec_id']).sum().reset_index(level=0).code

    return V, df

def get_features_AZ(df, min_date, city_tag, i_cols):
    if 'id_' not in df.columns:
        df['id_'] = df.permit_id
    I = get_AZ_inspections(df)
    V, I = get_AZ_violations(I)
    R = lib.state_yelp_reviews(df, min_date, city_tag)
    y, x = lib.merge_inspec_dates(I, df, R, i_cols)
    X = lib.summarize_reviews(x)
    return pd.merge(y, X, left_on=['inspec_id','business_id','id_'], right_index=True, how='inner')


# -----------MAIN-----------------------------
###############################################

if __name__ == '__main__':
    AZ = open_pickle('../data/phx/phoenix_yelp_merge.pkl')
    df_AZ = get_features_AZ(AZ, '2012-04-01', 'phoenix', ['n_priority', 'grade', 'n_violations','v_core','sum_core',
                                                          'v_foundation','sum_foundation','v_priority','sum_priority'])
    save_to_pickle(df_AZ, '../data/phx/phoenix_yelp_features.pkl')

