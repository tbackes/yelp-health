import pandas as pd
import numpy as np
import pickle
import re
import string
from merge_vegas import open_pickle, save_to_pickle
import features_main as lib

pd.options.mode.chained_assignment = None  # default='warn'


def get_NV_inspections(df, drop_flag=True):
    I = pd.read_csv('../data/vegas/restaurant_inspections.csv', delimiter=';', header=None, skiprows=1)
    I.columns = ['serial_number', 'permit_number', 'date','time',
                 'employee_id', 'type_id', 'demerits', 'grade',
                 'permit_status', 'result', 'violations', 'record_updated', 'empty']
    I.drop(['empty', 'permit_status'],axis=1, inplace=True)
    I.grade.fillna('', inplace=True)
    I.demerits.fillna(-1, inplace=True)
    I.violations.fillna('', inplace=True)

    I['n_violations'] = I.violations.apply(lambda x: len(x.split(',')) if len(x) > 0 else 0)
    I['id_'] = I.permit_number
    I['inspec_id'] = I.serial_number

    I = I[I.permit_number.isin(df.permit_number.unique())]
    if drop_flag:
        I.drop_duplicates(inplace=True) 

    return I[I.permit_number.isin(df.permit_number.unique())]

def get_features_NV(df, min_date, city_tag, i_cols):
    if 'id_' not in df.columns:
        df['id_'] = df.permit_number
    I = get_NV_inspections(df)
    R = lib.state_yelp_reviews(df, min_date, city_tag)
    y, x = lib.merge_inspec_dates(I, df, R, i_cols)
    X = lib.summarize_reviews(x)
    return pd.merge(y, X, left_on=['inspec_id','business_id','id_'], right_index=True, how='inner')


# -----------MAIN-----------------------------
###############################################

if __name__ == '__main__':
    NV = open_pickle('../data/vegas/vegas_yelp_merge.pkl')
    df_NV = get_features_NV(NV, '1989-07-01', 'vegas', ['demerits','grade', 'n_violations'])
    save_to_pickle(df_NV, '../data/vegas/vegas_yelp_features.pkl')

