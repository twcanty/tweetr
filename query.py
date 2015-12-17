#!/usr/bin/python2.4
import nltk
from nltk.corpus import wordnet as wn
from nltk.corpus import wordnet_ic

import boto.cloudsearch2
from boto.cloudsearch2.layer2 import Layer2
from boto.cloudsearch2.domain import Domain

from threading import Thread
import operator

import json
import os, sys
import datetime
import time
import math
import re, string, timeit

from pytagcloud import create_tag_image, make_tags
from pytagcloud.lang.counter import get_tag_counts

import psycopg2

from PIL import Image


idToTweet = {}
idToRank = {}
exclude = set(string.punctuation)

SynonymIDs = set()
HyponymIDs = set()
HypernymIDs = set()

CloudDictionary = {}

last_file_name = ""

NUMBER_TO_DISPLAY = 100


def getTweetText(ids):
	conn = psycopg2.connect("dbname ='twidat' user='tcanty' host='db' password='XXXXX'")
	cur = conn.cursor()

	for tweetID in ids:
		cur.execute("""select tweet from tweets where id = %s""", [tweetID])
		for row in cur.fetchall():
			tweetText = row[0]
			if tweetID not in idToTweet:
				idToTweet[tweetID] = tweetText


def rankTweets(searchTerm, keywords, range_min, range_max):
	keys = idToTweet.keys()[range_min:range_max]

	for key in keys:
		if key not in idToRank:
			value = idToTweet[key]
			value_len = float(len(value))
			split = value.split()
			numwords = len(split)
			seenWords = {}
			idToRank[key] = 0.0
			for word in split:
				no_punc = ''.join(ch for ch in word if ch not in exclude).lower()
				len_no_punc = float(len(no_punc))
				amountToAdd = 0.0

				if no_punc is searchTerm:
					CloudDictionary[no_punc] += 1
					if no_punc in seenWords:
						count = float(seenWords[no_punc])
						amountToAdd += float(1.0 / (2.0 * count))
						seenWords[no_punc] = seenWords[no_punc] + 1.0
					else:
						seenWords[no_punc] = 1.0
						amountToAdd += 0.85
				elif (no_punc in keywords):
					CloudDictionary[no_punc] += 1.0
					if no_punc in seenWords:
						count = float(seenWords[no_punc])
						amountToAdd += float(1.0 / (2.0 * count))
						seenWords[no_punc] = seenWords[no_punc] + 1.0
					else:
						seenWords[no_punc] = 1.0
						amountToAdd += 0.5
				else:
					amountToAdd -= float(len_no_punc/value_len)

				idToRank[key] += amountToAdd

def rankTweetsNaive(searchTerm, keywords, range_min, range_max):
	keys = idToTweet.keys()[range_min:range_max]

	for key in keys:
		if key not in idToRank:
			value = idToTweet[key]
			split = value.split()
			numwords = len(split)
			idToRank[key] = 0.0
			for word in split:
				no_punc = ''.join(ch for ch in word if ch not in exclude).lower()
				amountToAdd = 0.0
				if no_punc == searchTerm:
					CloudDictionary[no_punc] += 1
					amountToAdd += 1.0
				elif (no_punc in keywords):
					CloudDictionary[no_punc] += 1.0
					amountToAdd += 0.8
				else:
					amountToAdd -= 0.5

				idToRank[key] += amountToAdd

def distributeBySource(rankedTweets):
	total_tweets = len(SynonymIDs) + len(HypernymIDs) + len(HyponymIDs)
	if (total_tweets == 0):
		total_tweets = 1
	syn_perc = float(len(SynonymIDs)) / total_tweets
	hypo_perc = float(len(HypernymIDs)) / total_tweets
	hyper_perc = float(len(HyponymIDs)) / total_tweets

	syn_allowance = int(NUMBER_TO_DISPLAY * syn_perc)
	hypo_allowance = int(NUMBER_TO_DISPLAY * hypo_perc)
	hyper_allowance = int(NUMBER_TO_DISPLAY * hyper_perc)


	tweets_committed = 0
	syn_remaining = syn_allowance
	hypo_remaining = hypo_allowance
	hyper_remaining = hyper_allowance

	syntweets = []
	hypertweets = []
	hypotweets = []
	residual = []

	tweets = []

	for tweetID in rankedTweets:
		if (tweets_committed < NUMBER_TO_DISPLAY):
			curr_ID = tweetID[0]
			if (curr_ID in SynonymIDs) and syn_allowance > 0:
				tweets.append(curr_ID)
				syn_remaining -= 1
			elif (curr_ID in HypernymIDs) and hyper_remaining > 0:
				tweets.append(curr_ID)
				hyper_remaining -= 1
			elif (curr_ID in HyponymIDs) and hypo_remaining > 0:
				tweets.append(curr_ID)
				hypo_remaining -= 1
			else:
				continue
			tweets_committed += 1

	return tweets


def REPL(searchterm, searchType):
	con = boto.cloudsearch2.connect_to_region("us-east-1",
        aws_access_key_id='XXXXXXXXXXXX',
        aws_secret_access_key='XXXXXXXXXXXXXXXXXXXXXXXXXXXXX')

	domain_data = con.describe_domains('twidat-word-search')


	domain_data = (domain_data['DescribeDomainsResponse']
	                          ['DescribeDomainsResult']
	                          ['DomainStatusList'])

	domain = Domain(con, domain_data[0])

	search_service = domain.get_search_service()

	searchTerm = searchterm
	synsets = wn.synsets(searchTerm)
	syn_to_synset = {}
	synonyms = []
	hypernyms = []
	synsetsOfSearchTerm = []
	synsetsOfRelatedTerms = []
	sortedSimScores = []



	listOfSynonyms = []
	listOfHyponyms = []
	listOfSynonyms.append(searchTerm)
	listofHypernyms = []
	for x in synsets:
		listOfSynonyms.extend([str(lemma.name()) for lemma in x.lemmas()])
		listOfHyponyms.extend([str(hyponym.name().split(".")[0]) for hyponym in x.hyponyms()])
		listofHypernyms.extend([str(hypernym.name().split(".")[0]) for hypernym in x.hypernyms()])

	relevantSynonyms = set(listOfSynonyms)
	relevantHyponyms = set(listOfHyponyms)
	relevantHypernyms = set(listofHypernyms)

	superlist = set()
	if (searchType == 'drill' or searchType == 'everything'):
		superlist.update(relevantHyponyms)
	if (searchType == 'explore' or searchType == 'everything'):
		superlist.update(relevantHypernyms)
	if (searchType == 'lateral' or searchType == 'everything'):
		superlist.update(relevantSynonyms)


	tweetIds = []
	for word in superlist:
		results = search_service.search(word);
		if (results.hits > 0):
			for result in results:
				ids = map(int, result['fields']['tweet'])
				if searchType == 'everything':
					if word in relevantSynonyms:
						SynonymIDs.update(ids)
					elif word in relevantHyponyms:
						HyponymIDs.update(ids)
					elif word in relevantHypernyms:
						HypernymIDs.update(ids)
				tweetIds.extend(ids)




	numthreads = 10;
	max_range = len(tweetIds)
	thread_range = int(math.ceil(max_range / numthreads))

	db_threads = []
	for i in range(0, numthreads):
		offset = i * thread_range
		if (offset > max_range):
			break
		subset = tweetIds[offset : min(max_range, offset + thread_range)]
		t = Thread(target=getTweetText, args=(subset,))
		t.start()
		db_threads.append(t)

	for t in db_threads:
		t.join()

	for word in superlist:
		CloudDictionary[word] = 0

	rank_threads = []
	for i in range(0, numthreads):
		offset = i * thread_range;
		if (offset > max_range):
			break
		t = Thread(target=rankTweets, args=(searchterm, superlist, offset, min(max_range, offset+thread_range),))
		t.start()
		rank_threads.append(t)

	for t in rank_threads:
		t.join()

	sorted_rank = sorted(idToRank.items(), key=operator.itemgetter(1), reverse=True)
	tweets_to_display = []


	if (searchType == 'everything'):
		idsToUse = distributeBySource(sorted_rank)
		for idnum in idsToUse:
			tweets_to_display.append(idToTweet[idnum])
	else:
		i = 0
		for id_rank_tuple in sorted_rank:
			if i < NUMBER_TO_DISPLAY:
				tweets_to_display.append(idToTweet[id_rank_tuple[0]])
				i += 1
			else:
				break


	wordCloudList = []
	sorted_cloud_dict = sorted(CloudDictionary.items(), key=operator.itemgetter(1), reverse=True)
	for item in sorted_cloud_dict:
		wordCloudList.append((item[0].replace('_', ' '), item[1]))
	if (len(wordCloudList) == 0):
		wordCloudList.append((searchTerm, 1))
	try:
		sys.path.insert(0, '.')
		os.system("rm *.png")
	except e:

		pass

	version = abs(hash(str(datetime.datetime.now().time())))
	filename = str(abs(hash(searchTerm))) + str(version) + ".png"
	last_file_name = filename

	width = 500
	height = 500
	

	img = Image.new('RGB', (width, height))
	img.save(filename)
	create_tag_image(make_tags(wordCloudList, minsize=20, maxsize=130), filename, fontname='Lobster', rectangular=True)

	CloudDictionary.clear()


	SynonymIDs.clear()
	HyponymIDs.clear()
	HypernymIDs.clear()

	idToTweet.clear()
	idToRank.clear()


	synString = ', '.join(relevantSynonyms).replace('_', ' ')
	hypoString = ', '.join(relevantHypernyms).replace('_', ' ')
	hyperString = ', '.join(relevantHyponyms).replace('_', ' ')

	return (tweets_to_display, version, synString, hyperString, hypoString)



def main():
	REPL("politics")


if __name__ == "__main__":
    main()