import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from sys import argv

pd.options.mode.chained_assignment = None  # default='warn'

import yelp_tfidf as lib_tfidf
from merge_main import open_pickle, save_to_pickle
import lda
from scipy.sparse import hstack, csr_matrix
from sklearn.feature_extraction.text import CountVectorizer

# def get_codewords(n, tf=tf, tf_vector=tf_vector, top_pos=top_pos, top_neg=top_neg):
def get_codewords(n, tf, tf_vocab, top_pos, top_neg):
    # Find index of top 300 positive and negative vocabulary columns:
    ind_tf_pos = [tf_vocab.index(x) for x in top_pos[:n] if x in tf_vocab]
    ind_tf_neg = [tf_vocab.index(x) for x in top_neg[:n] if x in tf_vocab]
    
    # Create new features: GOODREVIEW and BADREVIEW
    GOODREVIEW = tf[:,ind_tf_pos].sum(axis=1)
    BADREVIEW = tf[:,ind_tf_neg].sum(axis=1)

    # exclude additional stop words:
    ind = [x not in ['wa','thi'] for x in tf_vocab]

    # Create final feature matrix (and update vocabulary)
    tf_final = hstack((tf[:,np.array(ind).nonzero()[0]], csr_matrix(GOODREVIEW), csr_matrix(BADREVIEW)))
    vocab_final = [tf_vocab[i] for i, x in enumerate(ind) if x] + ['GOODREVIEW','BADREVIEW']

    return tf_final, vocab_final

def fit_and_print(tf_final, vocab_final, n_topics, alpha=0.1, eta=0.01):
    # Fit LDA
    model_lda = lda.LDA(n_topics=n_topics, n_iter=500, random_state=981, alpha=alpha, eta=eta)
    model_lda.fit(tf_final)
    # Print Top 10 words
    print_topics(model_lda.topic_word_, vocab_final)
        
    return model_lda

def print_topics(topic_word, vocab_final, n=10):
    prob_score = get_probability_score(topic_word)
    for i, topic_dist in enumerate(prob_score):
        topic_words = np.array(vocab_final)[np.argsort(topic_dist)][:-(n+1):-1]
        print '*Topic %s\n- %s' % (i, ' '.join(topic_words))

def get_probability_score(topic_word):
    K, W = topic_word.shape
    
    avg_log_score = np.log(topic_word).sum(axis=0)/K
    prob_score = np.multiply(topic_word, np.log(topic_word) - avg_log_score)
    
    return  prob_score

def get_sentiment_words():
	neg = pd.read_csv('../data/negative-words.txt', skiprows=35,header=None)
	pos = pd.read_csv('../data/positive-words.txt', skiprows=35,header=None)
	neg_stem = lib_tfidf.stem_tokens(neg.values.flatten().tolist())
	pos_stem = lib_tfidf.stem_tokens(pos.values.flatten().tolist())
	return pos_stem, neg_stem

def get_tf(df, max_features):
	# Calculate term frequency matrix
	tfr, tfr_vector = lib_tfidf.yelp_tf(df, 'text', max_features=max_features)
	return tfr, tfr_vector.get_feature_names(), tfr_vector

def get_tf_sentiment(tfr, tfr_vocab, _stem):
	tfr_  = tfr[:, np.array([x in set(_stem) for x in tfr_vocab]).nonzero()[0]]
	vocabr_ = [x for x in tfr_vocab if x in set(_stem)]
	return tfr_, vocabr_

def get_top_words(tfr_, vocabr_):
	#get top occuring sentiment words (only count document frequency)
	docr = (tfr_ > 0).sum(axis=0).tolist()[0]
	indr = np.argsort(docr)[::-1]
	topr = [vocabr_[x] for x in indr]
	return topr

def run(n_topics, n_words, tfr, tfr_vocab, alpha, eta):
	pos_stem, neg_stem = get_sentiment_words()

	tfr_pos, vocabr_pos = get_tf_sentiment(tfr, tfr_vocab, pos_stem)
	tfr_neg, vocabr_neg = get_tf_sentiment(tfr, tfr_vocab, neg_stem)

	topr_pos = get_top_words(tfr_pos, vocabr_pos)
	topr_neg = get_top_words(tfr_neg, vocabr_neg)

	tfr_final, vocabr_final = get_codewords(n_words, tf=tfr, tf_vocab=tfr_vocab, top_pos=topr_pos, top_neg=topr_neg)
	modelr = fit_and_print(tfr_final, vocabr_final, n_topics, alpha=alpha, eta=eta)

	return modelr

def get_reviews():
	return open_pickle('../data/yelp/yelp_reviews_phoenix.pkl')

def get_tf_pickled():
	return open_pickle('../data/yelp/yelp_tf_reviews_phx.pkl')

if __name__ == '__main__':
	n_topics = int(argv[1])
	n_words = int(argv[2])
	alpha = float(argv[3])
	eta = float(argv[4])

	# read in yelp review dataframe
	yelp_AZ = get_reviews()

	# read in yelp review term frequency matrix (and vocabulary)
	tfr, tfr_vocab = get_tf_pickled()

	model = run(n_topics, n_words, tfr, tfr_vocab, alpha, eta)