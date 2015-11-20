import numpy as np
import pandas as pd
import nltk
import string
import re

from sklearn.feature_extraction.text import TfidfVectorizer
from nltk.tokenize import sent_tokenize
from nltk.stem.porter import PorterStemmer
from nltk.stem.snowball import SnowballStemmer

from nltk.corpus import stopwords

path = '/opt/datacourse/data/parts'
#stemmer = SnowballStemmer('english')
stemmer = PorterStemmer()
stop = stopwords.words('english')

def stem_tokens(tokens):
    stemmed = []
    for item in tokens:
        stemmed.append(stemmer.stem(item))
    return stemmed

def tokenize(text):
    tokens = nltk.word_tokenize(text)
    stems = stem_tokens(tokens)
    return stems

def standardize_text(text):
    lowers = text.lower()
    no_punctuation = re.sub('[%s]' % re.escape(string.punctuation), '', lowers)
    return no_punctuation

def yelp_tfidf(df,col):
    no_punctuation = df[col].apply(standardize_text)
            
    #this can take some time
    tfidf = TfidfVectorizer(tokenizer=tokenize, stop_words='english', max_features=5000)
    tfs = tfidf.fit_transform(no_punctuation)

    return tfs, tfidf

### LARA METHOD
## Aspect Segmentation
def preprocess_sentences(text):
    # tokenize into list of sentences
    sent_tokenize_list = sent_tokenize(text)

    # convert to lowercase and remove punctuation
    sentence_standardized = map(standardize_text, sent_tokenize_list)

    # stem, tokenize and remove stop words
    sentences = [[stemmer.stem(w) for w in nltk.word_tokenize(sentence) if w not in stop] \
                           for sentence in sentence_standardized]

    return sentences

def seed_aspect_keywords():
    A = {'value': ['money', 'value', 'price', 'cost', 'worth', 'bill'],
         'premise': ['music', 'environment','atmosphere', 'decor', 'space', 
                     'bar', 'ambience', 'patio', 'room'],
         'location': ['spot', 'neighborhood', 'location', 'locale'],
         'service': ['employee','professional','bartender', 'manager', 'hostess', 'owner', 'staff',
                     'attention', 'server', 'service', 'waiter', 'waitress', 'waitstaff'],
         'quality': ['portion', 'cook', 'quality', 'prepared', 'meal'],
         'hygiene': ['toilet', 'bathroom', 'gloves', 'hair', 'clean', 'poison', 'dirty', 'wipe', 'infest'],
         'food': ['menu', 'food', 'taste', 'flavor', 'meal', 'dish']
        }

    for key, value in A.iteritems():
        A[key] = [stemmer.stem(w) for w in value]

    return A.values(), A.keys()

def chi_square(tf, aspects):
    print 'C'
    C = tf.sum(); print 'C1'
    C1 = tf.T.dot(aspects); print 'C2'
    C2 = tf.T.dot(aspects < 1); print 'C3'
    #C3 = (1-tf.T.todense()).dot(aspects); print 'C4'
    #C4 = (1-tf.T.todense()).dot(aspects < 1); print 'X2'
    C3 = aspects.sum(axis = 0) - C1; print 'C4'
    C4 = tf.shape[0] - C1 - C2 - C3; print 'X2'

    X2 = (C * np.square(np.multiply(C1,C4) - np.multiply(C2,C3))) / \
            (np.multiply(np.multiply(np.multiply(C1+C3,C2+C4),C1+C2),C3+C4))

    return X2

def filter_tf(tf, vocabulary, n):
    ind = (tf.sum(axis = 0) >= n).nonzero()[1]
    return tf[:,ind], [vocabulary[x] for x in ind]

def label_aspect(A, tf, vocabulary):
    # loop through all aspects to create aspect word counts for each sentence
    Count = np.zeros((tf.shape[0],len(A)))
    for i in xrange(Count.shape[1]):
        w = [vocabulary.index(x) for x in A[i] if x in vocabulary]
        Count[:,i] = tf[:, w].sum(axis=1).reshape(-1)
    maxCount = np.max(Count, axis=1)

    # loop through all sentences and assign to top aspect(s)
    aspects = np.zeros((tf.shape[0],len(A)))
    for s, row in enumerate(Count):
        if maxCount[s] > 0:
            aspects[s, (row == maxCount[s]).nonzero()] = 1

    return aspects

def tokenize_sentences(df):
    return [x for y in df.text.apply(sent_tokenize).values for x in y]

def summarize_aspects(df):
    documents = df.text.apply(preprocess_sentences)

def aspect_segmentation_bootstrap(df, p=15, I=10, n=5):
    # Create word count (by sentence)
    sentences = tokenize_sentences(df)
    stop_words = stop + ['this','was','is','were', 'wa', 'thi']
    vectorizer = TfidfVectorizer(preprocessor=standardize_text, tokenizer=tokenize, stop_words=stop_words, 
                                 use_idf=False, binary=True, norm=False, lowercase=False)
    tf = vectorizer.fit_transform(sentences)

    # Word list:
    vocabulary = vectorizer.get_feature_names()

    # Remove words with less than 5 occurences:
    print tf.shape
    tf, vocabulary = filter_tf(tf, vocabulary, n)
    print tf.shape

    # Get aspect seed keywords
    A_new, aspect_labels = seed_aspect_keywords()
    A = []

    ct = 0
    while (A_new <> A) and (ct < I):
        print '\nIteration %d:' % ct
        A = A_new

        print 'Labeling aspects'
        # loop through all sentences and assign to top aspect(s)
        aspects = label_aspect(A, tf, vocabulary)

        print 'Chi-Square'
        # Calculate Chi-Square between aspects and words 
        X2 = chi_square(tf, aspects)

        A_new = [[vocabulary[w] for w in np.argsort(X2[:,i], axis=0)[-1:-(1+p):-1]] for i in xrange(aspects.shape[1])]
        print 'Change? %s' % A_new <> A
        ct += 1

        print aspect_labels
        print '---'
        for row in A_new:
            print row

    return A, aspect_labels, aspects, A_new, vocabulary, X2
