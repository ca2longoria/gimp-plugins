
import sys
import json
import time
from gimpfu import *

def stdput(path='./std'):
	a = sys.stdout
	b = sys.stderr
	sys.stdout = open(path+'.out','a')
	sys.stderr = open(path+'.err','a')
	print
	print time.strftime("%H:%M:%S")
	return a,b
def stdget(out,err):
	sys.stdout.close()
	sys.stderr.close()
	sys.stdout = out
	sys.stderr = err

def crawl(ob,keys=None,parents=None,capture=None,bubble=None,param=None):
	"""
	Returns what was passed in as param, after crawling through the target
	object's nested structure and firing callbacks at every node in both capture
	and bubble directions.
	
	Parameters:
	ob
		- target dict being crawled through
	parents
		- stack of parent objects to the current object under callback
	keys
		- stack of matching keys resulting in current object under callback in
		  pairing with parents stack
	capture
		- callback function called at every dict moving in the capture direction
		- capture(<dict>,<list>,<list>,<?>)
			- <dict>, current dict
			- <list>, keys stack at state in capture's calling
			- <list>, parents stack at state in capture's calling
			- <?>, optional parameter passed along from crawl(...)
	bubble
		- callback function called at every dict moving in the bubble direction
		- functionally identical to capture, except during the bubble step
	param
		- optional argument passed in as param to capture and bubble callbacks
	"""
	parents = parents or []
	keys = keys or []
	param = param or {}
	if capture:
		capture(ob,keys,parents,param=param)
	for k,v in ob.iteritems():
		if type(v) is dict:
			parents.append(ob)
			keys.append(k)
			crawl(v,keys=keys,parents=parents,capture=capture,bubble=bubble,param=param)
			keys.pop()
			parents.pop()
	if bubble:
		bubble(ob,keys,parents,param=param)
	return param

def __layercrawl_call(a,ob,i,param=None):
	pass
def __layercrawl_assign(p,a,ob,i,param=None):
	p[a.name] = ob
def layercrawl(items,parent=None,
		call=__layercrawl_call,assign=__layercrawl_assign,param=None):
	"""
	Returns nested object matching layer structure, filled by call and assign
	callback functions.
	
	Parameters:
	items
		- list of layers/grouplayers
	parent
		- parent object (default = None)
	call
		- callback function for assigning key/value pairs between layer and
		  matching dict, takes place during capture stage
		- call(<gimp.Layer>,<dict>,<int>,<?>)
			- gimp.Layer, current layer
			- dict, current dict matching layer in the nested structure
			- int, current index amongst sibling layers
			- ?, optional parameter passed along from layercrawl(...)
	assign
		- callback function for assigning child dict to parent dict, takes place
		  during bubble stage
		- assign(<dict>,<gimp.Layer>,<dict>,<int>,<?>)
			- dict, parent dict
			- gimp.Layer, current layer
			- dict, current dict matching layer in the nested structure
			- int, current index amongst sibling layers
			- ?, optional parameter passed along from layercrawl(...)
	param
		- optional argument passed in as param to call and assign callbacks
	
	Note: gimp.Layer may also be gimp.GroupLayer.
	"""
	index = 0
	parent = parent or {}
	for a in items:
		ob = {}
		call(a,ob,index,param=param)
		if hasattr(a,'layers'):
			layercrawl(a.layers,parent=ob,call=call,assign=assign,param=param)
		assign(parent,a,ob,index,param=param)
		index += 1
	return parent


def clone_layer_tree(img,layer,prefix='copy_',root=None):
	
	# TODO: Refactor to handle "layers" as opposed to "layer".
	
	print 'clone_layer_tree:',img,layer,prefix,root
	# Build the nested object with relevant layer and index data.
	def call(a,ob,i,param):
		ob['layer'] = a
		ob['index'] = i
	def assign(p,a,ob,i,param):
		p[i] = ob
	bob = layercrawl([layer],call=call,assign=assign)
	
	# Crawl through nested object, creating duplicate layers and the function
	# instructions for insertion into the target Image, passed along as both
	# args and insert_layers in the return value for later use at convenience.
	args = []
	def clone(ob,keys,parents,param):
		layer = ob['layer']
		if layer == root:
			ob['newlayer'] = layer
			return
		if hasattr(layer,'layers'):
			layer = gimp.GroupLayer(img)
		else:
			# This is necessary for duplication between images; layer.copy()
			# throws an error in that case.
			layer = pdb.gimp_layer_new_from_drawable(layer,img)
		layer.name = prefix+ob['layer'].name
		ob['newlayer'] = layer
		args.append((pdb.gimp_image_insert_layer,img,layer,
			len(parents) and parents[-1]['newlayer'] or root,
			ob['index']))
	# Since the single layer was passed into layercrawl as a single-member list,
	# the desired object is actually the first element of its return value.
	crawl(bob[0],capture=clone)
	
	# This function will execute insertion behavior at a single later call.
	def insert_layers():
		for a in args:
			a[0](*a[1:])
	
	return bob[0],args,insert_layers
