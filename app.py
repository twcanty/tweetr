#!/usr/bin/python2.4
from flask import Flask, render_template, request, redirect, url_for, send_from_directory
from query import REPL
from os import remove
import json
UPLOAD_FOLDER = '/gpfs/main/home/tcanty/course/wordnet'
app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

@app.route("/")
def main():
    return render_template('index.html')

@app.route('/search', methods = ['POST'])
def search():
	# try:
	# 	remove('cloud_large.png')
	# except:
	# 	pass
	searchTerm = request.form['searchTerm']
	searchType = request.form['searchType']
	# print("The search term is " + searchTerm)
	# print("The search type is " + searchType)
	val = REPL(searchTerm, searchType)
	# for x in val:
	# 	print str(x)

	filename = str(abs(hash(searchTerm))) + str(val[1]) + ".png"
	sendImage(filename)
	return render_template('search.html', searchTerm=searchTerm,searchType=searchType, data=val[0], filename=filename, syns=val[2], hyper=val[3], hypo=val[4])
	# return redirect('/')

@app.route('/images/<filename>')
def sendImage(filename):
	return send_from_directory(UPLOAD_FOLDER, filename)

if __name__ == "__main__":
	app.debug = True
	app.run(host='0.0.0.0')