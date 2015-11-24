import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import pickle
import re
import string
import json
pd.options.mode.chained_assignment = None  # default='warn'
from merge_main import open_pickle, save_to_pickle
from import_yelp_mongo import get_yelp_reviews, get_yelp_reviews_afterdate

from sklearn.cross_validation import train_test_split
from sklearn.linear_model import LogisticRegression, LinearRegression
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.svm import SVC, SVR
from sklearn.svm import LinearSVC, LinearSVR
from sklearn.metrics import f1_score, accuracy_score, precision_score, recall_score,\
                            confusion_matrix, classification_report, mean_squared_error
from sklearn.grid_search import GridSearchCV
from sklearn.cross_validation import KFold
import yelp_tfidf as lib_tfidf

class HealthModel(object):
    def __init__(self, df, tfs, tfs_h, target='sum_priority', tfs_vocab=None, tfs_h_vocab=None):
        self.get_train_test(df, tfs, tfs_h)
        self.target = target
        self.tfs_vocab = tfs_vocab
        self.tfs_h_vocab = tfs_h_vocab

    def get_train_test(self, df, tfs, tfs_h):
        df_train, df_test, tfs_train, tfs_test, tfs_h_train, tfs_h_test = train_test_split(df, tfs, tfs_h,
                                                                                            train_size=0.7, 
                                                                                            random_state=981)
        self.df_train = df_train
        self.df_test = df_test
        self.tfs_train = tfs_train
        self.tfs_test = tfs_test
        self.tfs_h_train = tfs_h_train
        self.tfs_h_test = tfs_h_test
        return

    def get_target_gte(self, t=2, train=True):
        if train:
            return (self.df_train[self.target] >= t).astype(int).values
        else:
            return (self.df_test[self.target] >= t).astype(int).values

    def get_target_bool(self, train=True):
        if train:
            return pd.get_dummies(self.df_train[self.target])
        else:
            return pd.get_dummies(self.df_test[self.target])

    def get_summary_features(self, col, train=True):
        if train:
            return self.df_train[col].values
        else:
            return self.df_test[col].values

    def get_features(self, col=None, tfs=True, tfs_h=True, train=True):
        X = {}
        if col is not None:
            X['summary'] = self.get_summary_features(col, train)
        if tfs:
            X['tfs'] = self.tfs_train.todense() if train else self.tfs_test.todense()
        if tfs_h:
            X['tfs_h'] = self.tfs_h_train.todense() if train else self.tfs_h_test.todense()

        # return X.values
        return np.hstack(X.values())
    
    def save_metrics(self, y_pred, t, rows=None):
        if rows is None:
            y_true = self.get_target_gte(t=t, train=False)
        else:
            y_true = self.get_target_gte(t=t)[rows[1]]
        d = {'accuracy': accuracy_score(y_true, y_pred),
             'precision': precision_score(y_true, y_pred), 
             'recall': recall_score(y_true, y_pred),
             'f1': f1_score(y_true, y_pred),
             'mse': mean_squared_error(y_true, y_pred)}
        CM = confusion_matrix(y_true, y_pred)
        d.update({'TN': CM[0,0],
                  'FP': CM[0,1],
                  'FN': CM[1,0],
                  'TP': CM[1,1],
                 })
        return d

    def train_classifier(self, model, col=None, tfs=False, tfs_h=False, t=2, rows=None):
        X_train = self.get_features(col=col, tfs=tfs, tfs_h=tfs_h)
        y_train = self.get_target_gte(t=t)
        if rows is None:
            X_test = self.get_features(col=col, tfs=tfs, tfs_h=tfs_h, train=False)
        else:
            train = rows[0]
            test = rows[1]
            X_test = X_train[test,:]
            X_train = X_train[train,:]
            y_train = y_train[train]
        model.fit(X_train, y_train)
        y_pred = model.predict(X_test)
        d = self.save_metrics(y_pred, t, rows=rows)
        return {t: d}

    def model_classifier(self, model, col=None, tfs=False, tfs_h=False, val_range=xrange(1,7), rows=None):
        d = {}
        for t in val_range:
            d.update(self.train_classifier(model, col=col, tfs=tfs, tfs_h=tfs_h, t=t, rows=rows))
        return pd.DataFrame.from_records(d).T

    def compare_models(self, models, model_tags, feature_tags, col=None, tfs=False, tfs_h=False, val_range=xrange(1,7)):
        results = []
        for m, tag, f in zip(models, model_tags, feature_tags):
            temp = self.model_classifier(m, col=col, tfs=tfs, tfs_h=tfs_h, val_range=val_range)
            temp.index.name=self.target
            temp['model'] = str(m.__class__).strip("'>").split('.')[-1]
            temp['type'] = tag
            temp['features'] = f
            results.append(temp)
        return pd.concat(results)

    def k_fold_comparison(self, models, model_tags, feature_tags, col=None, tfs=False, tfs_h=False, val_range=[2]):
        k_fold = KFold(self.df_train.shape[0], random_state=981)
        results = []
        for m, tag, f in zip(models, model_tags, feature_tags):
            for k, k_ind in enumerate(k_fold):
                temp = self.model_classifier(m, col=col, tfs=tfs, tfs_h=tfs_h, val_range=val_range, rows=k_ind)
                temp.index.name=self.target
                temp['model'] = str(m.__class__).strip("'>").split('.')[-1]
                temp['type'] = tag 
                temp['features'] = f
                temp['k-fold'] = k
                results.append(temp)
        return pd.concat(results)

    def grid_search_classifier(self, model, param_grid, col=None, tfs=False, tfs_h=False, scoring='f1', t=2):
        grid = GridSearchCV(model, param_grid, n_jobs=-1, scoring=scoring)
        X_train = self.get_features(col=col, tfs=tfs, tfs_h=tfs_h)
        y_train = self.get_target_gte(t=t)
        grid.fit(X_train, y_train)
        print grid.best_params_
        return grid

def unpack_data(fname='../data/phx/model_data_phx.pkl'):
    data = open_pickle(fname)
    df_AZ = data['df_AZ']
    tfs = data['tfs']
    tfs_vocab = data['tfidf_vocab'] 
    tfs_h = data['tfs_h']
    tfs_h_vocab = data['tfidf_h']
    A_labels = data['labels']
    A_vocab = data['vocab'] 
    return df_AZ, tfs, tfs_vocab, tfs_h, tfs_h_vocab, A_labels, A_vocab

if __name__ == '__main__':
    df_AZ, tfs, tfs_vocab, tfs_h, tfs_h_vocab, A_labels, A_vocab = unpack_data('../data/phx/model_data_phx.pkl')

    col1 = ['rev_ct','neg_ct','stars_avg','rev_len_avg','stars_var']
    col2 = ['rev_ct','neg_ct','stars_avg','rev_len_avg','stars_var','n_hygiene','n_service',
            'n_location','n_food','n_premise','n_quality','n_value']

    phx = HealthModel(df, tfs, tfs_h, tfs_vocab=tfs_vocab, tfs_h_vocab=tfs_h_vocab)








