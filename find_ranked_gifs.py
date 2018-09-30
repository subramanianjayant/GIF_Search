import clarifai
import giphy_client
import numpy as np
import pandas as pd
import time
import os

from clarifai.rest import ClarifaiApp
from giphy_client.rest import ApiException
from gensim.models import KeyedVectors

def main(IMAGE):
	app = ClarifaiApp()
	model = app.public_models.general_model
	if 'http' in IMAGE:
        	response = response_from_url(model,IMAGE)
	else:
		if os.path.isfile(IMAGE):
        		response = response_from_file(model,IMAGE)
		else:
			return pd.DataFrame({})
	concepts = {concept['name']:concept['value'] for concept in response}	
	api_instance = giphy_client.DefaultApi()

	query = ''
	for concept in concepts:
	        query = query+concept+' '
	print 'QUERY: %s' % query
	giflist = GIFS_from_query(query, api_instance)
	giflist = [gif.images.downsized.url for gif in giflist]

	concepts = pd.DataFrame.from_dict(concepts, orient= 'index').reset_index()
	concepts = clean_concepts(concepts)
	concepts['tempkey'] = 1

	ranked_gifs = {url:get_metric(url,model,concepts) for url in giflist}
	ranked_gifs = pd.DataFrame.from_dict(ranked_gifs, orient = 'index').sort_values(by = 0, ascending = False)
	return ranked_gifs


def load_word2vec():
	print 'Loading Google Word2Vec model...'
	filename = 'GoogleNews-vectors-negative300.bin'
	model = KeyedVectors.load_word2vec_format(filename, binary=True)
	print 'Loading complete'
	return model

def response_from_file(model,filename):
	response = model.predict_by_filename(filename)
	return response['outputs'][0]['data']['concepts']

def response_from_url(model, url):
	response = model.predict_by_url(url)
	return response['outputs'][0]['data']['concepts']

def clean_concepts(concepts_df):
	concepts_df = concepts_df[~concepts_df['index'].str.contains(' ')] 
	return concepts_df

def GIFS_from_query(query, api_instance, limit=20,giphy_api_key = 'rAtfa5dDLJW3xJDwJjGfOxMoyXYwDWIs'):
	api_response = api_instance.gifs_search_get(giphy_api_key,query,limit = limit, lang = 'en', fmt = 'json')
	return api_response.data


def calculate_cos_distance(row):
	w1 = row['index_x']
	w2 = row['index_y']
	try:
		retrieval1 = w2v[w1]
		retrieval2 = w2v[w2]
	except KeyError:
		return 0
        return w2v.similarity(w1,w2)

def get_metric(gif_url, model,concepts):
	gif_concepts = response_from_url(model,gif_url)
	gif_concepts = {concept['name']:concept['value'] for concept in gif_concepts}
	gif_concepts = pd.DataFrame.from_dict(gif_concepts, orient = 'index').reset_index()
	gif_concepts = clean_concepts(gif_concepts)
	gif_concepts['tempkey'] = 1
	metric_df = pd.merge(concepts,gif_concepts,on='tempkey').drop('tempkey',axis='columns')

	metric_df['relation'] = metric_df.apply(calculate_cos_distance, axis=1)
	metric_df['metric'] = metric_df['0_x']*metric_df['0_y']*metric_df['relation']
	final_metric = metric_df['metric'].mean()
	return final_metric

w2v = load_word2vec()

from flask import Flask, request, render_template

app = Flask(__name__)

@app.route('/', methods=['GET','POST'])
def hello_world():
        ordered_urls = []
	if request.method == 'POST':
                imageurl = request.form.get('url')
                df = main(imageurl)
		if df.empty:
			ordered_urls = ['http://www.teachitza.com/delphi/io3.jpg']
		else:
			ordered_urls = [url for url in df.index]
        return render_template('output.html',results=ordered_urls)

if __name__ == '__main__':
        app.run(debug = True, port=5000)

#if __name__=='__main__':
#	print main('https://img.huffingtonpost.com/asset/6b7fdeab1900001d035028dc.jpeg?cache=sixpwrbb1s&ops=1910_1000')
