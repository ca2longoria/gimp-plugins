
import sys
import gtk
import copy
from pyfu import *
from gimpfu import *


class PyWindow(gtk.Window):
	"""
	Holy Justice Wiggin, small alien creature!  What is going on here!?
	"""
	class value_map(object):
		def __init__(self):
			self._dict = {}
		def __getitem__(self,key):
			w,get,set = self._dict[key]
			return get(w)
		def __setitem__(self,key,value):
			w,get,set = self._dict[key]
			return set(w,value)
		def __determine(self,w):
			print '__determine',self,w
			if hasattr(w,'get_buffer'):
				b = w.get_buffer()
				if type(b) == gtk.TextBuffer:
					def get(w):
						b = w.get_buffer()
						return b.get_text(b.get_start_iter(),b.get_end_iter())
					def set(w,v):
						b = w.get_buffer()
						b.set_text(v)
					return get,set
			return (lambda w:None,lambda w:None)
		def put(self,key,ob,get=None,set=None):
			if (not get) or (not set):
				g,s = self.__determine(ob)
				get = get or g
				set = set or s
			self._dict[key] = (ob,get,set)
			
	
	def __init__(self,contents=None,title='entitling titlage',size=None,resizable=None,**args):
		"""
		Sanctifies the keyword '_widget' under contents, which represent a
		widget with children.
		
		Parameters:
		contents
			- dict for dynamic initialization and arrangement of child widgets.
			  Its rules are specified, below
		title
			- title of the created window
		size
			- list of [width,height] for window size
		resizable
			- boolean to set the window's resizable flag
		
		Rules for contents parameter parsing:
		- an example:
			{
				'box': { '_widget':(gtk.VBox,),
					# ^ A widget containing children for later insertion can be
					# specified using a dict with a '_widget' key.  That key's
					# value acts in place of the dict for processing, allowing
					# for the other key/value pairs in the dict to be processed
					# with it as their parent.
					
					'text1':(0,gtk.TextView,),
					'_text1':('pack_start',{'expand':False,'fill':False}),
					# ^ Leading a key with an underscore indicates packing
					# instructions this widget's parent will use for its
					# insertion.
					
					'text2':(11,gtk.TextView,),
					'_text2':('pack_end',{
						'expand':False,
						'fill':False,
						'_get':lambda w:'Noodles'
						# ^ Some keys passed into the packing keywords dict are
						# special.  _get and _set, for example, override the
						# functions used by self's 'value' attribute to get or
						# set the contents of the widget in question.  ... This
						# is kind of a hack, but it fits well enough to look at.
					}),
					
					'button':(10,gtk.Button,{'label':'Click Me'}),
					# ^ The numbers leading the tuples are for ascending
					# ordering under the widget's parents.  Leaving this out
					# leaves its insertion unordered, but after those with
					# ordering indexes.
					'_button':('pack_end',{'expand':False,'fill':False})
				}
			}
		
		- the widget lists explained:
			(
				[<ordering-index>],
				<widget-class>,
				[<init-argument-list>],
				[<init-keywords-dict>]
			)
			- Only the widget class is absolutely necessary.  The rest provide
			  either <widget-class>.__init__(self,...) arguments or the ordering
			  index.
		"""
		contents = contents or {}
		gtk.Window.__init__(self,**args)
		self.connect('delete-event',gtk.main_quit)
		self.set_title(title)
		if not size is None:
			self.set_geometry_hints(min_width=size[0],min_height=size[1])
		if size and resizable == False:
			self.set_resizable(False)
		
		widgets = {}
		packing = {}
		ordering = {}
		def capture(ob,keys,parents,param):
			#print 'capture:',ob,keys,len(parents),len(param)
			if len(keys) == 0:
				return
			if keys[-1] == '_root':
				raise 'ERROR: _root is an invalid widget key'
			if keys[-1] == '_widget':
				return False
			if keys[-1][0] == '_':
				packing[keys[-1][1:]] = copy.deepcopy(ob)
				return False
			r = ob
			if type(r) is dict and r.has_key('_widget'):
				r = r['_widget']
			if type(r) in (list,tuple):
				# Leave widgets of unspecified order to the end.
				order_index = sys.maxint
				if type(r[0]) is int:
					# Take first element as ordering index and truncate to
					# expected length.
					order_index = r[0]
					r = r[1:]
				args = len(r) > 1 and (type(r[1]) in (list,tuple)) and tuple(r[1]) or []
				keywords = len(r) > 1 and type(r[-1]) is dict and r[-1] or {}
				widget = r[0](*args,**keywords)
				pkey = len(keys) > 1 and keys[-2] or None
				
				param[keys[-1]] = (widget,pkey and param[pkey][0] or self)
				ordering[keys[-1]] = order_index
				
				# If ob isn't a dict, this is a leaf node, and capture recursion
				# should cease.
				if not type(ob) is dict:
					return False
		crawl(contents,capture=capture,param=widgets)
		self.widgets = widgets
		
		self.value = PyWindow.value_map()
		self.__init_children(widgets,packing,ordering)
		
		# Assign only widget to self.widgets' values, since packing into parents
		# has already occurred.
		for k,a in self.widgets.items():
			self.widgets[k] = a[0]
	
	def __init_children(self,widgets,packing,ordering):
		for k,v in sorted(widgets.items(),key=lambda a:ordering[a[0]]):
			# p should be self in appropriate cases.
			w,p = v
			get,set = (None,None)
			#print 'k,w,p',k,w,p
			if packing.has_key(k):
				special = ('_get','_set')
				pack,keywords = packing[k]
				if keywords.has_key('_get'):
					get = keywords['_get']
				if keywords.has_key('_set'):
					set = keywords['_set']
				for s in special:
					if keywords.has_key(s):
						del keywords[s]
				pack = pack or 'add'
				getattr(p,pack)(w,**keywords)
			else:
				p.add(w)
			# Add to the value mapping.
			self.value.put(k,w,get=get,set=set)


