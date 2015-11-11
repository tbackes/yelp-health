import pandas as pd
import numpy as np
from pymongo import MongoClient

def get_yelp_reviews(B_ids):
    client = MongoClient()
    db = client.test
    coll = db.reviews

    return pd.DataFrame(list(coll.find({"business_id":{"$in":B_ids}})))

def get_yelp_reviews_afterdate(B_ids, date):
    client = MongoClient()
    db = client.test
    coll = db.reviews

    return pd.DataFrame(list(coll.find({"business_id":{"$in":B_ids}, "date":{"$gt":date}})))