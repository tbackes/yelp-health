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

def yelp_tfidf(df):
    no_punctuation = df.text.apply(standardize_text)
            
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
    A = {'value': ['money', 'bill', 'value', 'price', 'cost', 'worth'],
         'premise': ['music', 'environment','atmosphere', 'decor', 'space', 
                     'bar', 'ambience', 'patio', 'room'],
         'location': ['spot', 'neighborhood', 'location', 'located'],
         'service': ['employee','professional','bartender', 'manager', 'hostess', 'owner', 'staff',
                     'attention', 'server', 'service', 'waiter', 'waitress', 'waitstaff'],
         'quality': ['portion', 'cook', 'quality', 'prepared', 'meal'],
         'hygiene': ['toilet', 'bathroom', 'gloves', 'hair', 'floor', 'clean', 'poison', 'dirty'],
         'food': ['menu', 'food', 'taste', 'flavor', 'meal', 'dish']
        }

    for key, value in A.iteritems():
        A[key] = [stemmer.stem(w) for w in value]

    return A

def aspect_segmentation_bootstrap(df):
    documents = df.text.apply(preprocess_sentences)

    A = seed_aspect_keywords()

    for d in documents:
        for sentence in d:
            break

    return

