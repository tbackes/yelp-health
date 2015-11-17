import pandas as pd
import numpy as np
import pickle
import re
import string
from merge_main import open_pickle, save_to_pickle
from import_yelp_mongo import get_yelp_reviews, get_yelp_reviews_afterdate

pd.options.mode.chained_assignment = None  # default='warn'


def state_yelp_reviews(df, d, tag):
    ids_ = df.business_id.values.tolist()
    R = get_yelp_reviews_afterdate(ids_, d)
    print R.info()
    
    save_to_pickle(R, '../data/yelp/yelp_reviews_%s.pkl' % tag)
    
    return R

def generate_inspec_dates(df):
    df_sort = df.sort_values(['id_','inspec_id','date'],ascending=False)
    
    dates = df_sort.date.values.tolist()
    ids = df_sort.id_.values.tolist()
    df_sort['date_start'] = dates[1:] + [0]
    df_sort['id_start'] = ids[1:] + ['']

    ind = df_sort['id_start'] <> df_sort.id_
    df_sort.date_start[ind] = df_sort.date[ind].apply(lambda x: pd.to_datetime(x) + pd.Timedelta('-182 days'))
    df_sort.date_start[~ind] = df_sort.date_start[~ind].apply(lambda x: pd.to_datetime(x) + pd.Timedelta('1 days'))
    df_sort.date_start = pd.to_datetime(df_sort.date_start)
    
    df_sort.set_index('inspec_id', inplace=True)
    return df_sort[['date_start']]

def merge_reviews_to_inspections(Y_WI, R_WI):
    X_WI = pd.merge(Y_WI, R_WI, how='left', on='business_id', suffixes=['_i','_r'])
    print X_WI.shape

    for col in ['date_r','date_i','date_start']:
        X_WI[col] = pd.to_datetime(X_WI[col])

    X_WI = X_WI[((X_WI.date_r >= X_WI.date_start) & (X_WI.date_r <= X_WI.date_i))]
    
    print X_WI.shape
    return X_WI

def merge_inspec_dates(I, df, R, cols):
	temp = generate_inspec_dates(I)
	i_cols = ['date','id_','inspec_id'] + cols
	b_cols = ['business_id', 'id_']
	temp2 = pd.merge(df[b_cols], I[i_cols], on='id_', how='inner', suffixes=['_h','_y'])
	y = pd.merge(temp2, temp, how='left', left_on='inspec_id', right_index=True)
	return y, merge_reviews_to_inspections(y, R)

def summarize_reviews(x):
	x['review_length'] = x.text.apply(len)
	x['negative_rating'] = x.stars.apply(lambda x: x <= 2).astype(int)
	x_gp = x.groupby(['inspec_id','business_id','id_'])

	ct_list = ['text','negative_rating']
	av_list = ['stars','review_length']
	var_list = ['stars']
	X = pd.concat([x_gp.count()[ct_list], x_gp.mean()[av_list], x_gp.var()[var_list], x_gp.text.apply(lambda x: ' '.join(x))], axis=1)
	X.columns = ['rev_ct','neg_ct','stars_avg','rev_len_avg','stars_var','text']
	X.stars_var.fillna(0, inplace=True)

	#X['text'] = x_gp.text.apply(lambda x: ' ',join(x))
	print X.info()
	return X

