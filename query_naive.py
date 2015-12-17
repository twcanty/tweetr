#!/usr/bin/python2.4
import nltk
import time
import math
from threading import Thread
import operator
import boto.cloudsearch2
import json
import os, sys
import datetime
from boto.cloudsearch2.layer2 import Layer2
from boto.cloudsearch2.domain import Domain
from nltk.corpus import wordnet as wn
from nltk.corpus import wordnet_ic

from pytagcloud import create_tag_image, make_tags
from pytagcloud.lang.counter import get_tag_counts

import re, string, timeit

import psycopg2


from PIL import Image


# nltk.download()

idToTweet = {}
idToRank = {}
exclude = set(string.punctuation)
stopwords = nltk.corpus.stopwords.words('english')

SynonymIDs = set()
HyponymIDs = set()
HypernymIDs = set()

CloudDictionary = {}

last_file_name = ""

NUMBER_TO_DISPLAY = 100


def getTweetText(ids):
	conn = psycopg2.connect("dbname ='twidat' user='tcanty' host='db' password='print4Tom'")
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
			value_len = len(value)
			split = value.split()
			numwords = len(split)
			seenWords = {}
			for word in split:
				no_punc = ''.join(ch for ch in word if ch not in exclude).lower()
				len_no_punc = len(no_punc)
				amountToAdd = 0.0
				# cloud_list.append(word)
				if no_punc is searchTerm:
					CloudDictionary[no_punc] += 1
					if no_punc in seenWords:
						count = seenWords[no_punc]
						amountToAdd += 1.0 / (2.0 * count)
					else:
						seenWords[no_punc] = 1.0
						amountToAdd += 0.85
				elif (no_punc in keywords):
					CloudDictionary[no_punc] += 1.0
					if no_punc in seenWords:
						count = seenWords[no_punc]
						amountToAdd += 1.0 / (2.0 * count)
					else:
						seenWords[no_punc] = 1.0
						amountToAdd += 0.5
				else:
					amountToAdd -= len_no_punc/value_len

				idToRank[key] = amountToAdd

def distributeBySource(rankedTweets):
	total_tweets = len(SynonymIDs) + len(HypernymIDs) + len(HyponymIDs)

	syn_perc = float(len(SynonymIDs)) / total_tweets
	hypo_perc = float(len(HypernymIDs)) / total_tweets
	hyper_perc = float(len(HyponymIDs)) / total_tweets

	syn_allowance = int(NUMBER_TO_DISPLAY * syn_perc)
	hypo_allowance = int(NUMBER_TO_DISPLAY * hypo_perc)
	hyper_allowance = int(NUMBER_TO_DISPLAY * hyper_perc)

	print syn_allowance
	print hypo_allowance
	print hyper_allowance


	tweets_committed = 0
	syn_remaining = syn_allowance
	hypo_remaining = hypo_allowance
	hyper_remaining = hyper_allowance

	syntweets = []
	hypertweets = []
	hypotweets = []
	residual = []

	for tweetID in rankedTweets:
		if (tweets_committed < NUMBER_TO_DISPLAY):
			curr_ID = tweetID[0]
			if (curr_ID in SynonymIDs) and syn_allowance > 0:
				syntweets.append(curr_ID)
				syn_remaining -= 1
			elif (curr_ID in HypernymIDs) and hyper_remaining > 0:
				hypertweets.append(curr_ID)
				hyper_remaining -= 1
			elif (curr_ID in HyponymIDs) and hypo_remaining > 0:
				hypotweets.append(curr_ID)
				hypo_remaining -= 1
			else:
				continue
			tweets_committed += 1
	
	print "Hypernym Tweets:"
	for x in hypertweets:
		print "\t" + str(x)
	print
	print "Synonym Tweets:"
	for x in syntweets:
		print "\t" + str(x)
	print
	print "Hyponym Tweets:"
	for x in hypotweets:
		print "\t" + str(x)

def distributeByWord():
	return

def REPL(searchterm, searchType):
	con = boto.cloudsearch2.connect_to_region("us-east-1",
        aws_access_key_id='AKIAJFNY5JERULZIU4XQ',
        aws_secret_access_key='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')

	# print conn.list_domains()
	domain_data = con.describe_domains('twidat-word-search')


	domain_data = (domain_data['DescribeDomainsResponse']
	                          ['DescribeDomainsResult']
	                          ['DomainStatusList'])

	domain = Domain(con, domain_data[0])

	search_service = domain.get_search_service()

	# while (1):
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
	listOfHyponyms.append(searchTerm)
	listofHypernyms = []
	for x in synsets:
		listOfSynonyms.extend([str(lemma.name()) for lemma in x.lemmas()])
		listOfHyponyms.extend([str(hyponym.name().split(".")[0]) for hyponym in x.hyponyms()])
		listofHypernyms.extend([str(hypernym.name().split(".")[0]) for hypernym in x.hypernyms()])
		# relevantSynonyms.update(set(str(lemma.name()) for lemma in x.lemmas()))
		# relevantHyponyms.update(set(str(hyponym.name()) for hyponym in x.hyponyms()))
		# relevantHypernyms.update(set(str(hypernym.name()) for hypernym in x.hypernyms()))
	print
	print "relevant synonyms: \n" + str(set(listOfSynonyms))
	print
	print
	print "relevant hyponyms: \n" + str(set(listOfHyponyms))
	print
	print "relevant hypernyms: \n" + str(set(listofHypernyms))
	relevantSynonyms = set(listOfSynonyms)
	relevantHyponyms = set(listOfHyponyms)
	relevantHypernyms = set(listofHypernyms)

	superlist = set()
	if (searchType == 'drill' or searchType == 'everything'):
		superlist.update(relevantHyponyms)
	if (searchType == 'explore' or searchType == 'everything'):
		superlist.update(relevantHypernyms)
	if (searchType == 'lateral' or searchType == 'everything'):
		print "you know better than this"
		superlist.update(relevantSynonyms)


	tweetIds = []
	for word in superlist:
		results = search_service.search(word);
		if (results.hits > 0):
			for result in results:
				ids = map(int, result['fields']['tweet'])
				if searchType is 'everything':
					if word in relevantSynonyms:
						SynonymIDs.update(ids)
					if word in relevantHyponyms:
						HyponymIDs.update(ids)
					if word in relevantHypernyms:
						HypernymIDs.update(ids)
				tweetIds.extend(ids)



	numthreads = 10;
	max_range = len(tweetIds)
	print max_range
	thread_range = int(math.ceil(max_range / numthreads))

	db_threads = []
	for i in range(0, numthreads):
		offset = i * thread_range
		print "starting db thread with range: " + str(offset) + " " + str(offset + thread_range)
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
		print "starting rank thread with range: " + str(offset) + " " + str(offset + thread_range)
		t = Thread(target=rankTweets, args=(searchterm, superlist, offset, min(max_range, offset+thread_range),))
		t.start()
		# t.join()
		rank_threads.append(t)

	for t in rank_threads:
		t.join()

	sorted_rank = sorted(idToRank.items(), key=operator.itemgetter(1), reverse=True)
	tweets_to_display = []
	i = 0
	for id_rank_tuple in sorted_rank:
		if i < NUMBER_TO_DISPLAY:
			tweets_to_display.append((id_rank_tuple[1], idToTweet[id_rank_tuple[0]]))
			i += 1
		else:
			break

	print "length of idToRank: " + str(len(sorted_rank))
	# distributeBySource(sorted_rank)

	wordCloudList = []
	sorted_cloud_dict = sorted(CloudDictionary.items(), key=operator.itemgetter(1), reverse=True)
	for item in sorted_cloud_dict:
		wordCloudList.append((item[0], item[1]))
	if (len(wordCloudList) == 0):
		wordCloudList.append((searchTerm, 1))
	# try:
	sys.path.insert(0, '.')
	os.system("rm *.png")
		# os.remove(fileName for fileName in os.listdir('/gpfs/main/home/tcanty/course/wordnet/') if fileName.endswith('.png'))
	# except e:
	# 	print e.error()
	# 	pass

	version = abs(hash(str(datetime.datetime.now().time())))
	filename = str(abs(hash(searchTerm))) + str(version) + ".png"
	last_file_name = filename

	width = 800
	height = 300
	n = len(wordCloudList)
	# maxsize = 200 - int((n / .25))
	# minsize = 50
	img = Image.new('RGB', (width, height))
	img.save(filename)
	create_tag_image(make_tags(wordCloudList, minsize=20, maxsize=130), filename, fontname='Lobster', rectangular=True)
	print CloudDictionary

	CloudDictionary.clear()


	SynonymIDs.clear()
	HyponymIDs.clear()
	HypernymIDs.clear()

	idToTweet.clear()
	idToRank.clear()


	return (tweets_to_display, version)


	# i = 0
	# for id_rank_tuple in sorted_rank:
	# 	if i < 100:
	# 		print "SCORE: " + str(id_rank_tuple[1])
	# 		print idToTweet[id_rank_tuple[0]]
	# 		print "------------------------------------------------------------------------"
	# 		i += 1
	# 	else:
	# 		break

	# exclude = set(string.punctuation)
	# print sortedSimScores
	# cloud_dict = {}
	# for x in sortedSimScores:
	# 	# print "x: " + str(x)
	# 	word = x[0][1].name().split(".")[0]
	# 	# print "word: " + word
	# 	result = search_service.search(word)
	# 	if (result.hits > 0):
	# 		for res in result:
	# 			ids = map(int, res['fields']['tweet'])
	# 			for identificationNumber in ids:
	# 				cur.execute("""select tweet from tweets where id = %s""", [identificationNumber])
	# 				for row in cur.fetchall():
	# 					# cloud_string += row[0] + " "
	# 					split = row[0].split()
	# 					for word in split:
	# 						# print "examining: " + word
	# 						no_punc = ''.join(ch for ch in word if ch not in exclude).lower()
	# 						if (len(wn.synsets(no_punc)) > 0):
	# 							# cloud_list.append(word)
	# 							if no_punc in cloud_dict:
	# 								cloud_dict[no_punc] = cloud_dict[no_punc] + 1
	# 							else:
	# 								cloud_dict[no_punc] = 1


	# # for word in cloud_dict.keys():
	# # 	print word

	# print "done first"
	# for k in list(cloud_dict):
	# 	if cloud_dict[k] == 1:
	# 		del cloud_dict[k]

	# print cloud_dict

	# cloud_string = " ".join(cloud_dict.keys())#.join(" ")

	# # print synsets
	# YOUR_TEXT = cloud_string
	# # # print YOUR_TEXT
	# print "Making Cloud"
	# tags = make_tags(get_tag_counts(YOUR_TEXT), maxsize=100)

	# create_tag_image(tags, 'cloud_large.png', size=(800, 800), fontname='Lobster')

	# print "Opening Image"
	# webbrowser.open('cloud_large.png')

	# print sortedSimScores





def main():
	REPL("politics")


if __name__ == "__main__":
    main()


    	# wordnet = wordnet_ic.ic('ic-brown.dat')
	# simScores = {}
	# print "RES"
	# for searchSynset in synsetsOfSearchTerm:
	# 	for relatedSynset in synsetsOfRelatedTerms:
	# 		if searchSynset.pos() is relatedSynset.pos():
	# 			simScores[(searchSynset, relatedSynset)] = searchSynset.wup_similarity(relatedSynset)
	# 			# simScores[relatedSynset] = searchSynset.lin_similarity(relatedSynset, wordnet)
	# simScores[(searchSynset, searchSynset)] = 100.0
	# sortedSimScores = list(sorted(simScores.iteritems(), key=simScores.get, reverse=True)[:5])
	# # for x in sortedSimScores:
	# # 	print x