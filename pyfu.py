
import re
import sys
import json
import time
from gimpfu import *

def flatiter(*args):
	for a in args:
		if hasattr(a,'__iter__'):
			yield flatiter(*a)
		else:
			yield a

def re_list(x,r):
	return [a for a in r if re.search(x,a)]

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
	parents = parents if not parents is None else []
	keys    = keys    if not keys    is None else []
	param   = param   if not param   is None else {}
	persist = True
	if capture:
		persist = capture(ob,keys,parents,param=param)
		persist = persist or persist is None
	if persist and hasattr(ob,'__iter__'):
		iter = type(ob) is dict and ob.iteritems() or zip(range(len(ob)),ob)
		for k,v in iter:
			if hasattr(v,'__getitem__'):
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
def layercrawl(items,parent=None,call=__layercrawl_call,assign=__layercrawl_assign,param=None):
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
	parent = parent if not (parent is None) else {}
	for a in items:
		ob = {}
		call(a,ob,index,param=param)
		if hasattr(a,'layers'):
			layercrawl(a.layers,parent=ob,call=call,assign=assign,param=param)
		assign(parent,a,ob,index,param=param)
		index += 1
	return parent

def layerquery(layer,query):
	layers = hasattr(layer,'__iter__') and layer or [layer]
	matches = []
	def call(a,ob,i,param):
		if query(a):
			param.append(a)
	layercrawl(layers,call=call,param=matches)
	return matches

def layersmash(layers):
	r = []
	def call(a,ob,i,param):
		r.append(a)
	layercrawl(layers,call=call)
	return r
	

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
		# These can be executed later in succession on calling the returned
		# insert_layers function.
		
		# WARNING: This still results in a backwards insertion!  ... Or not?
		#   Now, I am not seeing this.  Will have to look out for this one.
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


import copy
import types
class observer(object):
	"""
	More of a flat table, right now, than a full-out object.
	"""
	class _Observer(object):
		def __init__(self,classtype=None):
			if hasattr(self,'_etable'):
				return
			# None covers all callbacks without a key.
			self._etable = {None:{}}
			self._ktable = {}
			self._classtype = classtype
		
		def _add_events_1(self,*args):
			for a in args:
				self._etable[None][a] = []
		def _add_events_k(self,*args):
			for a in args:
				self._ktable[a] = []
		
		def __parse_on(self,args):
			k = None
			call = None
			if len(args) < 1:
				raise Exception('argument(s) (k,)call is/are necessary')
			# Set k and call.
			if type(args[0]) is types.FunctionType:
				call = args[0]
				args = args[1:]
			else:
				k = args[0]
				call = args[1]
				args = args[2:]
			if call is None:
				raise Exception('Must provide callback')
			return k,call,args
		def on(self,op,*args,**keys):
			try:
				k,call,args = self.__parse_on(args)
			except Exception as e:
				print 'ERROR:',e
				return False
			# This will only fire for 'set' and 'del', assuming a key was
			# appropriately provided.
			if not self._etable.has_key(k):
				self._etable[k] = copy.deepcopy(self._ktable)
			# Add the callback.
			r = self._etable[k][op]
			r.append((call,args,keys))
			return True
		def off(self,op,all=False,*args,**keys):
			try:
				k,call,args = self.__parse_on(args)
			except Exception as e:
				print 'ERROR:',e
				return False
			if not self._etable.has_key(k):
				return False
			r = self._etable[k][op]
			for i in range(len(r)):
				c,ag,kw = r
				if c == call:
					del r[i]
					if not all:
						break
			return True
	
	class _SetDel(_Observer):
		def __init__(self,classtype):
			observer._Observer.__init__(self,classtype)
			self._add_events_k('set','del')
		def __setitem__(self,k,v):
			print 'setitem',k,v
			old = self[k]
			self._classtype.__setitem__(self,k,v)
			if self._etable.has_key(k):
				r = self._etable[k]['set']
				for call,args,keys in r:
					# new, old, key
					call(v,old,k,*args,**keys)
		def __delitem__(self,k):
			print 'delitem',k
			old = self[k]
			self._classtype.__delitem__(self,k)
			if self._etable.has_key(k):
				r = self._etable[k]['del']
				for call,args,keys in r:
					call(old,k,*args,**keys)
	
	class _AddRemove(_Observer):
		def __init__(self,classtype):
			observer._Observer.__init__(self,classtype)
			self._add_events_1('add','remove')
		def _add_call(self,a,*args,**keys):
			print '_add',a
			r = self._etable[None]['add']
			for call,args2,keys2 in r:
				# This differs from key calls, as in _SetDel.  If an index, for
				# example, is provided, then that prepends the args stored under
				# (call,args,keys).
				call(a,*(args+args2),**keys2)
		def _remove_call(self,a,*args,**keys):
			print '_add',a
			r = self._etable[None]['remove']
			for call,args2,keys2 in r:
				# Looks like it ignores keys.
				call(a,*(args+args2),**keys2)
	
	class _Reorder(_Observer):
		def __init__(self,classtype):
			if not hasattr(classtype,'__iter__'):
				raise Exception('Must be based off an iterable class')
			observer._Observer.__init__(self,classtype)
			self._add_events_1('reorder')
		def _reorder_call(self,*args,**keys):
			print '_reorder_call',args,keys
			r = self._etable[None]['reorder']
			for call,args2,keys2 in r:
				call(self,*(args+args2),**keys2)
	
	class List(_SetDel,_AddRemove,_Reorder,list):
		def __init__(self,*args,**keys):
			observer._SetDel.__init__(self,list)
			observer._AddRemove.__init__(self,list)
			observer._Reorder.__init__(self,list)
			list.__init__(self,*args,**keys)
			print 'init',args,keys
		def __setslice__(self,a,b,r,*args,**keys):
			print 'setslice',a,b,r
			old_slice = self[a:b]
			list.__setslice__(self,a,b,r,*args,**keys)
			# Because the removal and insertion has already occurred, the self
			# passed into the _add_calls will not represent the state of the
			# list at time of insertion.
			for i in range(a,b):
				self._remove_call(old_slice[i-a],i)
			for i in range(a,a+len(r)):
				self._add_call(r[i-a],i,self)
		def __delslice__(self,a,b,*args,**keys):
			print 'delslice',a,b
			old_slice = self[a:b]
			list.__delslice__(self,*args,**keys)
			for i in range(a,b):
				if self._etable.has_key(i):
					r = self._etable[i]['del']
					for call,args2,keys2 in r:
						call(old_slice[i-a],i,*args2,**keys2)
				self._remove_call(old_slice[i-a],i)
		def append(self,v,*args,**keys):
			list.append(self,v)
			self._add_call(v,len(self),self)
		def extend(self,r,*args,**keys):
			old_len = len(self)
			list.extend(self,r,*args,**keys)
			for i in range(old_len,len(self)):
				self._add_call(self[i],old_len+i,self)
		def insert(self,i,v,*args,**keys):
			list.insert(self,i,v,*args,**keys)
			self._add_call(v,i,self)
		def remove(self,v,*args,**keys):
			i = self.index(v)
			list.remove(self,v,*args,**keys)
			self._remove_call(v,i,self)
		def reverse(self,*args,**keys):
			list.reverse(self,*args,**keys)
			self._reorder_call()
		def sort(self,*args,**keys):
			list.sort(self,*args,**keys)
			self._reorder_call()
	
	
	def __init__(self,d={}):
		self._dict = dict(d)
		self._etable = {}
	
	def __getitem__(self,k):
		return self._dict[k]
	
	def __setitem__(self,k,v):
		old = self._dict.has_key(k) and self._dict[k] or None
		self._dict[k] = v
		if self._etable.has_key(k):
			for call,args,keywords in self._etable[k]['set']:
				call(k,v,old,*args,**keywords)
	
	def __delitem__(self,k):
		del self._dict[k]
		if self._etable.has_key(k):
			del self._etable[k]
	
	def on(self,k,op,call,*args,**keywords):
		if not self._etable.has_key(k):
			self._etable[k] = {'set':[],'del':[]}
		self._etable[k][op].append((call,args,keywords))
	
	def off(self,k,op,call):
		if not self._etable.has_key(k):
			return
		r = self._etable[k][op]
		for i in range(len(r)):
			if r[i] == call:
				del r[i]

