import pandas as pd
import numpy as np
import pickle
import re
import string
from merge_vegas import open_pickle, save_to_pickle
import features_main as lib

pd.options.mode.chained_assignment = None  # default='warn'


def get_WI_inspections(df, drop_flag=True):
	inspec = df[['inspections']]
	I = []
	for inspec_item, id_ in zip(inspec.values.flatten().tolist(), df.id_.values.flatten().tolist()):
	    temp = pd.DataFrame.from_records(inspec_item).T
	    temp['id_'] = id_
	    temp['inspec_id'] = temp.index
	    I.append(temp)
	    
	I = pd.concat(I, axis=0)
	if drop_flag:
		I.drop_duplicates(['date','id_','inspec_id','result','type'], inplace=True)

	return I

def clean_violation_keys(x):
    x = x.lower().strip()
    x = re.sub(r'\b(orrective)\b','corrective',x)
    x = re.sub(r'\b(acton)|(actin)\b','action',x)
    x = re.sub(r'^(action:)|(action taken:)','action taken notes:',x)
    x = re.sub(r'(correction:)','corrective action:',x)
    x = re.sub(r'\b(practices)\b','practice',x)
    x = re.sub('[%s]' % re.escape(string.punctuation), '', x).strip()
    return x

def violations_to_dict(viol):
    d = {}
    for key, value in viol.iteritems():
        d2 = {}
        for j, x in enumerate(value):
            if clean_violation_keys(x) == 'good retail practice':
                d2['cdc risk factor'] = 'good retail practice'
            elif x.lower().find('good retail practice') >= 0:
                d2['cdc risk factor'] = 'good retail practice'
                d2['action taken notes'] = x.replace('good retail practice:', '').strip()
            else:
                i = x.find(':')
                if i > 0:
                    k = clean_violation_keys(x[:i+1])
                    if k=='good retail practice':
                        print "x: '%s' , k: '%s'" % (x, k)
                    if len(k) > 30:
                        d2['observation'] += ' ' + k.replace('code reference','')
                        d2['code reference'] = value[j+1]
                    elif (k == 'code reference') and (value[j][0]=='3'):
                        d2[k] = x[i+1:].strip() + ' ' + value[j+1]
                    elif k=='violation':
                        d2['observation'] = x[i+1:].strip()
                    elif k=='corrective action' and x[i+1:].find('Code reference:') >= 0:
                        a = re.split(r'Code Reference:',x[i+1])
                        d2[k] = a[0].strip()
                        a = a[-1]
                        if x[i+1:].find('CDC Risk Factor:') >= 0:
                            a = re.split(r'CDC Risk Factor:',a)
                            d2['cdc risk factor'] = a[-1]
                        d2['code reference'] = a[0]
                    elif k not in d2:
                        d2[k] = x[i+1:].strip()
        d[key] = d2
    return d

def get_WI_violations(df):
	V = []
	for viol, id_, inspec_id in zip(df.violations.values.flatten().tolist(), 
									df.id_.values.flatten().tolist(), 
									df.inspec_id.values.flatten().tolist()):
	    temp = pd.DataFrame.from_records(violations_to_dict(viol)).T
	    temp['id_'] = id_
	    temp['inspec_id'] = inspec_id
	    temp['viol_id'] = temp.index
	    V.append(temp)
	    
	V = pd.concat(V, axis=0)
	V['cdc risk factor'].fillna('', inplace=True)

	V['critical'] = (~V['cdc risk factor'].isin(['','good retail practice'])).astype(int)
	df['n_violations'] = V.groupby(['id_','inspec_id']).count().reset_index(level=0).critical
	df['n_critical'] = V.groupby(['id_','inspec_id']).sum().reset_index(level=0).critical

	df['n_critical'].fillna(0, inplace=True)
	df['n_violations'].fillna(0, inplace=True)

	return V, df

def get_features_WI(df, min_date, city_tag, i_cols):
	I = get_WI_inspections(df)
	V, I = get_WI_violations(I)
	R = lib.state_yelp_reviews(df, min_date, city_tag)
	y, x = lib.merge_inspec_dates(I, df, R, i_cols)
	X = lib.summarize_reviews(x)
	return pd.merge(y, X, left_on=['inspec_id','business_id','id_'], right_index=True, how='inner')


# -----------MAIN-----------------------------
###############################################

if __name__ == '__main__':
	WI = open_pickle('../data/mad/madison_yelp_merge.pkl')
	df_WI = get_features_WI(WI, '2011-06-30', 'madison', ['n_critical', 'n_violations'])
	save_to_pickle(df_WI, '../data/mad/madison_yelp_features.pkl')

