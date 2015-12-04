# Yelp Reviews

## Data

All Yelp data was pulled from the [Yelp Challenge datasets](http://www.yelp.com/dataset_challenge). In particular, I focused on the following two datasets:

- yelp_academic_dataset_business.json
- yelp_academic_dataset_review.json

### Business

The business data was used to link the yelp dataset back to city health inspection data. 

- primary key: `business_id`
- Filtered on: `categories == 'Restaurant'`
- Fields used to generate merge keys: `state`, `name`, `full_address`, `neighborhoods`

### Review

The review data was used to create features for predictive modeling. All reviews associated with a given inspection instance (the time period between `date_start` and `date of inspection`) were aggregated together to create features. The following fields were used to generate summary variables (which are then inputs for subsequent feature engineering):

- `stars`: rating, 1-5
    * `rev_ct`: Total number of reviews
    * `neg_ct`: Total number of reviews with `stars < 3`
    * `stars_avg`: Average rating
    * `stars_var`: Variance of ratings
- `text`: body of review
    * `rev_len_avg`: Average length of reviews (# characters, not # words)
    * `text`: body of all reviews concatenated into a single string

### Feature Generation:
Additional features were generated using the concatenated `text` field. These features are summarized below. For more information on their predictive power during modeling, refer to the [Phoenix Summary](https://github.com/tbackes/yelp-health/blob/master/summary_phoenix.md).

#### Bag of Words
The first step was to look at word counts. Unigram frequencies were generated using `sklearn`'s `TfidfVectorizer`. 

- Text was converted to lowercase
- Punctuation was removed
- Text was tokenized and stemmed using `sklearn`'s Porter stemmer
- A TFIDF matrix (Term Frequency Inverse Document Frequency) was created, with the vocabulary capped at the top 5000 words.

#### Aspect Segmentation
Wang et al (2010) outlined a method for assigning aspect(s) to each sentence of a review. I decided to use their aspect segmentation approach to try to isolate sentences refering to hygiene-related information. For more background on the approach, please refer to the [original paper](http://citeseerx.ist.psu.edu/viewdoc/download?doi=10.1.1.329.6649&rep=rep1&type=pdf).

First, I followed Wang et al's bootstrap approach for assigning keywords to each aspect. 

1. Split all reviews into sentences;
2. For each sentence, assign aspect label(s) based on the aspect(s) with the most matching keywords. (Multiple aspects are assigned when ties occur);
3. For each word in the corpus vocabulary, calculate the Chai-squared statistic for each aspect;
4. Create a new aspect keyword list using the top `p` words for each aspect (based on Chai-squared calculations from step 3);
5. If the aspect keyword list is unchanged or the maximum iterations have been exceeded proceed to step 6, else repeat steps 2-5;
6. Return the final aspect assignments for each sentence.

I manually selected 7 aspects and applied the above algorithm to get the final keyword lists shown below:

| aspect   | final keywords                                                          | seed words                                                                                                        |
|----------|-------------------------------------------------------------------------|-------------------------------------------------------------------------------------------------------------------|
| value    | price, worth, reason, high, money, bill, cost, fair, valu               | money, valu, price, cost, worth, bill                                                                             |
| premise  | bar, atmospher, patio, room, decor, music, space, environ, ambienc      | music, environ, atmospher, decor, space, bar, ambienc, patio, room                                                |
| location | locat, new, spot, scottsdal, local, hit, neighborhood, conveni, support | spot, neighborhood, locat, local                                                                                  |
| service  | servic, friendli, staff, server, manag, waitress, attent, owner, waiter | employee, profession, bartend, manage, hostess, owner, staff, attent, server, servic, waiter, waitress, waitstaff |
| quality  | meal, cook, price, portion, quality, size, perfectli, gener, prepar     | portion, cook, qualiti, prepar, meal                                                                              |
| hygiene  | clean, dirti, bathroom, hair, restroom, wipe, poison, toilet, glove     | toilet, bathroom, glove, hair, clean, poison, dirti, wipe, infest                                                 |
| food     | food, good, great, menu, tast, flavor, meal, dish, mexican              | menu, food, tast, flavor, meal, dish                                                                              |

I used the aspect segmentation results to create the following features:

- Summary:
	- Count of total # sentences for each aspect: `n_hygiene`,`n_service`, `n_location`,`n_food`,`n_premise`,`n_quality`,`n_value`
	- TFIDF bag of words calculated using only sentences labeled `hygiene`

*Notes:*

One of the challenges of modeling health inspection results with review data is that there is so much "noise" in the review data. Only a small portion of the review text (if any) directly discusses the hygiene or cleanliness of a restaurant. I hoped that this type of aspect segmentation would help me zoom in on any comments that directly discuss hygiene/cleanliness. However, without further analysis its hard to say whether the seed words I chose for the `hygiene` aspect were appropriate. I tried reading a large number or reviews to get a good feel for the types of words reviewers were using; however, one of the difficulties I faced is that reviewers rarely mention if a place is exceptionally clean or if they see good hygiene in practice.Therefore, my seed words are largely negative in nature.

My initial implementation of this approach did not provide as much value as I'd hoped. There is certainly room for improvement, especially in tuning various parameters like the # of aspects, the initial seed words and the size of the final keyword list. However, I decided that my time would be best spent exploring other approaches, so I have not spent any time tuning the aspect segmentation results.

#### CODEWORD LDA
Jack Linshi, a previous Yelp Challenge winner (from Round 3), developed a modified version of Latent Dirichlet Allocation (LDA) that allows topics to be associated with an explicit sentiment. For more background on the approach, please refer to the [original paper](http://www.yelp.com/html/pdf/YelpDatasetChallengeWinner_PersonalizingRatings.pdf).

The traditional input for LDA topic modeling is a term frequency matrix. Linshi's modified approach involves appending two columns to this matrix, associated with the "codewords" GOODREVIEW and BADREVIEW. GOODREVIEW corresponds to the frequency of all words in the review that are also found in a  positive sentiment list and BADREVIEW corresponds to words found in a negative sentiment list. Linshi demonstrated that the inclusion of these "good" and "bad" sentiment columns allows for LDA to associate sentiments to each topic.

These are the steps I followed to process data for this approach:
- Downloaded Bing Liu's [Opinion Lexicon](http://www.cs.uic.edu/~liub/FBS/opinion-lexicon-English.rar).
    * negative-words.txt (4,783 words)
    * positive-words.txt (2,006 words)
- Stemmed the sentiment word lists using Porter Stemmer.
- Calculated the term-frequency matrix for Phoenix, AZ Yelp reviews.
- Determined the top 300 most common stemmed positive and negative words using Phoenix's term frequency matrix.
- Appended sentiment columns to the term-frequency matrix:
    * GOODREVIEW = sum of term frequencies for top 300 positive sentiment words.
    * BADREVIEW = sum of term frequencies for top 300 negative sentiment words.

I used python's [`lda`](https://pypi.python.org/pypi/lda) package to run lda on my modified term frequency matrix, using the following parameters.
- 20 topics
- 500 sampling iterations
- alpha = 0.1 (parameter for distribution over topics)
- eta = 0.01 (parameter for distribution over words)

The fitted LDA model returns a document-topic matrix with point estimates of the topic distribution for each document. In my case, I modeled 20 topics so there were a total of 20 columns. This document-topic matrix became a set of features to use during classification. 

Here are the top 10 words associated with each of the 20 topics:

| Asian | Café + | Italian | Experience - | BBQ | Fine Dining | Seafood - | Mexican | Quality --- | Service +++ |
|---------------|-----------------|-------------------|-----------------------|---------------|-------------|--------------------|---------------------|-------------------------|----------------|
| thai | coffe | pizza | always | bbq | steak | fish | taco | BADREVIEW | GOODREVIEW |
| chicken | ice | crust | locat | chicken | dinner | shrimp | salsa | bad | great |
| rice | tea | italian | time | rib | dessert | fri | mexican | tast | food |
| pho | cream | pasta | ive | wing | birthday | seafood | burrito | food | service |
| soup | vegan | salad | year | pork | rib | crab | chip | bland | good |
| chines | buffet | wing | BADREVIEW | sauc | great | BADREVIEW | bean | star | veri |
| noodl | GOODREVIEW | chees | food | fri | wine | sauc | tortilla | ok | friendli |
| dish | dessert | sauc | ha | brisket | salad | lobster | enchilada | price | staff |
| curri | indian | slice | servic | chees | night | oyster | margarita | wasn’t | price |
| roll | pasti | pie | love | mac | filet | clam | carn | dri | clean |

| Service --- | Lunch | Experience +++ | Sushi - | Bar/Nightlife | Food | Location | American - | Service/Wait - | General --- |
|---------------|-----------------|-------------------|-----------------------|---------------|-------------|--------------------|---------------------|-------------------------|----------------|
| manag | sandwich | great | sushi | beer | salad | restaur | burger | tabl | BADREVIEW |
| BADREVIEW | salad | GOODREVIEW | roll | bar | chees | tabl | breakfast | minut | dont |
| order | chicken | love | hour | drink | bread | dine | fri | wait | know |
| custom | pita | amaz | happi | great | tomato | park | egg | order | walk |
| ask | gyro | servic | tuna | game | chicken | seat | bacon | seat | tabl |
| told | bread | food | price | hour | sauc | locat | dog | server | just |
| said | bagel | atmosphere | GOODREVIEW | music | sweet | phoenix | BADREVIEW | BADREVIEW | im |
| card | sub | staff | fish | patio | dish | area | pancak | ask | guy |
| rude | lunch | wine | great | night | flavor | menu | toast | drink | didnt |
| minut | soup | place | fresh | bartend | green | experi | potato | took | people |

I did not have time to vary the LDA model parameters, so further work would be needed to select optimal values. Given more time, I would perform a grid search on all 4 parameters and optimize based on the f1 score of the resulting hygiene classification results.



## References
Wang, Hongning, Yue Lu, and Chengxiang Zhai. "Latent aspect rating analysis on review text data: a rating regression approach." Proceedings of the 16th ACM SIGKDD international conference on Knowledge discovery and data mining. ACM, 2010.

Linshi, Jack. "Personalizing Yelp Star Ratings: a Semantic Topic Modeling Approach." Yelp Challenge Round 3 Winner. http://www.yelp.com/html/pdf/YelpDatasetChallengeWinner_PersonalizingRatings.pdf

Bing Liu, Minqing Hu and Junsheng Cheng. "Opinion Observer: Analyzing and Comparing Opinions on the Web." Proceedings of the 14th International World Wide Web conference (WWW-2005), May 10-14, 2005, Chiba, Japan.


