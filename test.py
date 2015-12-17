#!/usr/bin/python2.4
import nltk
from nltk.corpus import wordnet as wn

import time
import json

import boto.cloudsearch2
from boto.cloudsearch2.layer2 import Layer2
from boto.cloudsearch2.domain import Domain


import psycopg2
import sys

i = 0
interval = 700
while(1):
	try:
		con = boto.cloudsearch2.connect_to_region("us-east-1",
	            aws_access_key_id='AKIAJFNY5JERULZIU4XQ',
	            aws_secret_access_key='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')

		domain_data = con.describe_domains('twidat-word-search')


		domain_data = (domain_data['DescribeDomainsResponse']
		                          ['DescribeDomainsResult']
		                          ['DomainStatusList'])

		domain = Domain(con, domain_data[0])

		doc_service = domain.get_document_service()
		search_service = domain.get_search_service()

		conn = psycopg2.connect("dbname ='twidat' user='tcanty' host='db' password='print4Tom'")
		print i
		cur = conn.cursor()
		word_to_tweets = {}
		cur.execute("""select * from words limit 700 offset %s""", [i])
		rows = cur.fetchall()
		for row in rows:
			word = row[0]
			tweet = row[1]
			if word not in word_to_tweets:
				word_to_tweets[word] = [tweet]
			else:
				word_to_tweets[word].append(tweet)

		for word, listOfTweets in word_to_tweets.iteritems():
			results = search_service.search(word)
			if (results.hits > 0):
				for x in results:
					x['fields']['tweet'].extend(listOfTweets)
					x['fields']['tweet'] = list(set(map(int, x['fields']['tweet'])))
					if (len(x['fields']['tweet']) < 1000):
						doc_service.add(x['fields']['word'], x['fields'])
			else:
				word = {
					'word' : word,
					'tweet': map(int, listOfTweets),
					'position': 0 
				}
				if (len(listOfTweets) < 1000):
					doc_service.add(word['word'], word)

		print word_to_tweets.iterkeys().next()
		result = doc_service.commit()
		i += interval

	except Exception as e:
		print "Encountered error, attempting to sleep and continue."
		time.sleep(10)
		continue

	except psycopg2.DatabaseError, e:
		print "Error: %s" % e
		time.sleep(10)
		continue


print "done"