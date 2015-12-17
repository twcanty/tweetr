	# dog = wn.synset('dog.n.01')
	# print(wn.synsets("dance"))
	syns_apple = wn.synsets("politics")
	# syn_orange = wn.synsets("orange")[0]
	synonyms = {}
	hypernyms = []

	for syn_apple in syns_apple:
		print syn_apple.name()
		synonyms[syn_apple.name()] = syn_apple
		# for l in syn_apple.lemmas():
			# synonyms.append(l.name())
	# print (set(synonyms))

	unique = []
	print
	print

	for key, value in synonyms.iteritems():
		unique.append(value)
	for i in range(0, len(unique)):
		print unique[i].root_hypernyms()
		# curr = unique[i]
		# hyps = curr.root_hypernyms();
		# for item in hyps:
		# 	hypernyms.append(item.name())
		# for j in range (i+1, len(unique)):
			# common = curr.root_hypernyms(unique[i])
			# for item in common:
				# hypernyms.append(item)

	print set(hypernyms) 
		# print syn_apple.lowest_common_hypernyms(syn_orange)

	#     for l in syn.lemmas():
	#         synonyms.append(l.name())
	#         if l.antonyms():
	#             antonyms.append(l.antonyms()[0].name())
	# print(set(synonyms))
	# print(set(antonyms))

	# for syn in syns:
	# 	print syn.hypernyms()
	# print dog