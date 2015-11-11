import pandas as pd
import numpy as np
import pickle
import re
import string
from merge_vegas import open_pickle, save_to_pickle
import features_main as lib

pd.options.mode.chained_assignment = None  # default='warn'


def get_NC_inspections(df, drop_flag=True):
	inspec = df[['inspections']]
	I = []
	for inspec_item, id_ in zip(inspec.values.flatten().tolist(), df.id_.values.flatten().tolist()):
	    temp = pd.DataFrame(inspec_item, columns=['date','score','grade','inspector'])
	    temp['id_'] = id_
	    temp['inspec_id'] = pd.Series(zip(temp.id_,temp.index)).apply(lambda x: '%s_%s' % (x[0],x[1]))
	    I.append(temp)
	    
	I = pd.concat(I, axis=0).reset_index(drop=True)
	if drop_flag:
		I.drop_duplicates(inplace=True)

	return I

def get_features_NC(df, min_date, city_tag, i_cols):
	I = get_NC_inspections(df)
	R = lib.state_yelp_reviews(df, min_date, city_tag)
	y, x = lib.merge_inspec_dates(I, df, R, i_cols)
	X = lib.summarize_reviews(x)
	return pd.merge(y, X, left_on=['inspec_id','business_id','id_'], right_index=True, how='inner')


# -----------MAIN-----------------------------
###############################################

if __name__ == '__main__':
	NC = open_pickle('../data/char/charlotte_yelp_merge.pkl')
	df_NC = get_features_NC(NC, '2011-06-30', 'charlotte', ['score','grade'])
	save_to_pickle(df_NC, '../data/charlotte/charlote_yelp_features.pkl')

