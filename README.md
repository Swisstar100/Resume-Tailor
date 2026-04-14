Resume Tailor is a resume scoring and rewritting website built around scholarly articles on "Smart-Hiring" ATS soring systems used today (https://arxiv.org/html/2511.02537v1)
Users are able to create 3 applications which take a resume and job description to score against and rewrite for.

The scoring system works as follows:
# Skill Extraction Pipeline: normalize text -> match phrases between text and lexicon -> gather list of nouns/phrases --->
#   -> match list of nouns & phrases with lexicon using fuzzy algorithm
# Skill Scoring Pipeline: Vectorize all skills in resume and job post -> get cos_sim between resume & job skills ---> 
#   -> get best match in each col and get their mean

# Experience Extraction Pipeline: normalize resume & job post -> break project & experience into chunks by titles/headers --->
#   -> break job experience requirements into chunks using Claude
# Experience Scoring Pipeline: Vectorize all resume and job chunks -> get cos_sim between resume & job experience ---> 
#   -> get best match in each col and get their mean -> reduce experience score by .05 for every year that has passed since it occured
