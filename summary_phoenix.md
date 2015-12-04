# Phoenix, AZ

## Data

### Inspections:

Health Inspection data was gathered from the Maricopa County's Environmental Services portal. (http://www.maricopa.gov/EnvSvc/OnlineApplication/EnvironmentalHealth/FoodInspections)

Inspection dates ranged from: 10/23/2012 to 10/14/2015

The main information collected for each inspection include:
- `Date`
- `Purpose`
- `Grade`
- `# Violations - Priority`
	* A provision that contributes directly to the elimination, prevention, or reduction to an acceptable level, of hazards associated with foodborne illness or injury. There are no other provisions that more directly control the hazard in question.
- `# Violations - Priority Foundation`
	* A provision whose application supports, facilitates or enables one or more priority items.
- `# Violations - Core`
	* A provision that relates to general sanitation, operational controls, facilities or structures, equipment design, or general maintenance, and which is not designated as a Priority Item or Priority Foundation Item.
	* For more information, see: http://www.maricopa.gov/EnvSvc/EnvHealth/Violations.aspx

### Merge with Yelp Data:
After merging with the yelp business database:
- 4090 Restaurants
- 23,487 Inspection Instances
	* An inspection instance was defined as the period ending on the date of inspection and starting on the day after the previous inspection. If no previous inspection is available, the inspection period starts 6 months prior to the date of inspection.
	* For now, only ***routine*** inspections were used to create inspection instances.
	* Inspection instances span the period from: 04/24/2012 to 10/14/2015

## Target Generation:

The target (i.e. dependent variable) is based on `# Violations - Priority`.
- For classification modeling, thresholds from t = 1 to 6 were evaluated to create a binary target.
- I ended up using t = 2 as my final binary target (i.e., Unhealthy Restaurants = 2+ Priority Violations)
	* Under Maricopa County's [voluntary rating program](http://www.maricopa.gov/ENVSVC/EnvHealth/PermitScoring.aspx), 2+ priority violations result in a rating of C or D.
	* It would be interesting to explore a multiclass problem with targets of 0, 1, 2+ priority violations. (I would avoid more granular targets, as the counts become very low at 3+ priority violations).

## Feature Generation:

Features generated using yelp data are described [here](https://github.com/tbackes/yelp-health/blob/master/summary_yelp.md).

Additional features were generated using previous inspection history. 
- The following summary variables were generated over three time frames: Previous Inspection, Previous 2 Inspections, All Previous Inspections
- Avg # Priority Violations
- Avg # Priority Foundation Violations
- Avg # Core Violations

## Classification Modeling:
I used both the `RandomForestClassifier` and `LinearSVC` model classes from `sklearn` for classification modeling. This is an unbalanced class problem (Unhealth restaurants represent ~15% of the population). To account for this during the modeling process:
- I set `class_weight = balanced`
- I used the f1 score for optimization

Below are the best model results for each combination of variables, reported on a 25% holdout validation sample:
- **Yelp Summary**: Revew Count, Negative Review Count, Avg Rating, Rating Variance, Avg Review Length
- **LDA Topics**: Topic distribution probabilities for 20 topics generated using [LDA-codeword analysis](https://github.com/tbackes/yelp-health/blob/master/summary_yelp.md)
- **TFIDF**: TFIDF matrix generated using review text.
- **Prev. Inspec**: Variables looking at number of violations on previous inspections


| FN  | FP   | TN   | TP  | accuracy | f1     | mse    | precision | recall  | model         | Yelp Summary | LDA Topics | TFIDF | Prev. Inspec |
|-----|------|------|-----|----------|--------|--------|-----------|---------|---------------|--------------|------------|-------|--------------|
| 507 | 2629 | 3393 | 518 | 0.5550   | 0.2483 | 0.4450 | 0.1646    | 0.5054  | Random Forest | 1            | 0          | 0     | 0            |
| 508 | 2347 | 3675 | 517 | 0.5949   | 0.2659 | 0.4051 | 0.1805    | 0.50440 | Random Forest | 0            | 1          | 0     | 0            |
| 511 | 2255 | 3767 | 514 | 0.6075   | 0.2710 | 0.3925 | 0.1856    | 0.5015  | Random Forest | 1            | 1          | 0     | 0            |
| 484 | 2184 | 3838 | 541 | 0.6214   | 0.2885 | 0.3786 | 0.1985    | 0.5278  | Linear SVC    | 0            | 0          | 1     | 0            |
| 474 | 2236 | 3786 | 551 | 0.6154   | 0.2891 | 0.3846 | 0.1977    | 0.5376  | Linear SVC    | 0            | 1          | 1     | 0            |
| 513 | 2082 | 3940 | 512 | 0.6318   | 0.2830 | 0.3682 | 0.1974    | 0.4995  | Linear SVC    | 1            | 1          | 1     | 0            |
| 478 | 1529 | 4493 | 547 | 0.7152   | 0.3528 | 0.2848 | 0.2635    | 0.5337  | Random Forest | 0            | 0          | 0     | 1            |
| 472 | 1568 | 4454 | 553 | 0.7105   | 0.3516 | 0.2895 | 0.2607    | 0.5395  | Random Forest | 0            | 1          | 0     | 1            |
| 465 | 1578 | 4444 | 560 | 0.7101   | 0.3541 | 0.2899 | 0.2619    | 0.5463  | Random Forest | 1            | 1          | 0     | 1            |
| 487 | 1618 | 4404 | 538 | 0.7013   | 0.3383 | 0.2987 | 0.2495    | 0.5249  | Linear SVC    | 0            | 0          | 1     | 1            |

Summary: 
- None of the yelp features add significant incremental value to models including the previous inspection history.
- Of models without previous inspection history, the Linear SVC trained on only the TFIDF matrix has the best results.
