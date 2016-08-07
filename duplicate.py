
import sys
import json
from pyfu import *
from pygui import *
from gimpfu import *

debug_path = 'd:\\tmp\\pyfu'
O,E = stdput(debug_path)

def dupgrid(img,draw,countx=1,county=1,new_image=False,row_groups=False,major_group=False):
	stdout,stderr = stdput(debug_path)
	
	# Resize image.
	img_width = img.width
	img_height = img.height
	img_layers = img.layers
	
	# New image.
	if new_image:
		img2 = gimp.Image(img.width,img.height,img.base_type)
		pdb.gimp_display_new(img2)
	else:
		img2 = img
	
	pdb.gimp_undo_push_group_start(img2)
	
	img2.resize(img.width*countx,img.height*county,0,0)
	
	# Per tile, create new layer.
	majorg = major_group and gimp.GroupLayer(img2) or None
	if majorg:
		majorg.name = 'duplicates'
		pdb.gimp_image_insert_layer(img2,majorg,None,0)
	for i in range(0,county):
		rowg = row_groups and gimp.GroupLayer(img2) or None
		if rowg:
			rowg.name = 'row_%i' % i
			pdb.gimp_image_insert_layer(img2,rowg,majorg,0)
		for j in range(0,countx):
			inserts = []
			g = gimp.GroupLayer(img2)
			g.name = '%i,%i' % (i,j)
			for a in img_layers:
				layer,args,insert = clone_layer_tree(img2,a,prefix=g.name+'_',root=g)
				inserts.append(insert)
			pdb.gimp_image_insert_layer(img2,g,rowg,0)
			
			# NOTE: clone_layer_tree should be able to handle all the layers at
			#   once, so we can side-step this weird necessary reversal.
			for insert in reversed(inserts):
				insert()
				
			# Set offset of current layer group.
			g.set_offsets(img_width*j,img_height*i)
			
			# Update progress bar.
			gimp.progress_update(float(countx*i+j+1)/(countx*county))
	
	pdb.gimp_undo_push_group_end(img2)
	
	stdget(stdout,stderr)

def hueshift(img,draw):
	stdout,stderr = stdput(debug_path)
	
	class Win(PyWindow):
		def __init__(self,img,*args,**keys):
			
			class LowerWin(gtk.ScrolledWindow):
				def __init__(self,src,*args,**keys):
					if not hasattr(src,'layer_names'):
						raise 'ERROR: LowerWin src parameter must contain "layer_names" attribute'
					self.source = src
					
					gtk.ScrolledWindow.__init__(self,*args,**keys)
					self.set_policy(gtk.POLICY_AUTOMATIC,gtk.POLICY_ALWAYS)
					
					self.view = gtk.Viewport()
					self.vbox = gtk.VBox()
					
					self.view.add(self.vbox)
					self.add(self.view)
				
				def refresh(self):
					names = list(self.source.layer_names)
					for c in self.vbox.get_children():
						c.destroy()
					for n in self.source.layer_names:
						self.vbox.pack_start(self.init_row(n),expand=False)
				
				def init_row(self,name):
					frame = gtk.Frame()
					hb1 = gtk.HBox()
					hb1.set_property('height-request',36)
					
					label = gtk.Label(name)
					
					vb1  = gtk.VBox()
					up   = gtk.Button(label='^')
					up.set_size_request(24,18)
					down = gtk.Button(label='v')
					down.set_size_request(24,18)
					
					vb1.pack_start(up,expand=True,fill=True)
					vb1.pack_end(down,expand=True,fill=True)
					
					hb1.pack_start(label,expand=False)
					hb1.pack_end(vb1,expand=False,fill=False)
					frame.add(hb1)
					frame.show_all()
					
					return frame
					
			
			def def_layer_results():
				names = [[]]
				def get(w):
					return list(names[0])
				def set(w,v):
					w = widgetquery(w,lambda w:type(w) is gtk.VBox)[0]
					print 'set_layer_results',w,v
					names[0] = []
					for c in w.get_children():
						c.destroy()
					for a in v:
						print 'at ',a
						names[0].append(a.name)
						t = gtk.Label(a.name)
						t.set_justify(gtk.JUSTIFY_LEFT)
						t.set_size_request(100,13)
						# For some reason, this t.show() is necessary.
						t.show()
						w.pack_start(t,expand=False,fill=True)
					print 'w.children',w.get_children()
					sys.stdout.flush()
				return get,set			
			get_layer_results,set_layer_results = def_layer_results()
			
			ob = {
				'box': { '_widget':(gtk.VBox,),
					
					'layer_select': { '_widget':(-1,gtk.VBox,),
						'hbox1': { '_widget':(0,gtk.HBox,),
							'regex_label':(gtk.Label,['Regex']),
							'_regex_label':('pack_start',{'expand':False,'fill':False}),
							'regex':(gtk.Entry,),
							'_regex':('pack_end',{'expand':True,'fill':True})
						},
						'layer_results': { '_widget':(1,gtk.ScrolledWindow,),
							'viewport1': { '_widget':(gtk.Viewport,),
								'layer_results_box':(gtk.VBox,),
								'_layer_results_box':(None,{})
							}
						},
						'_layer_results':(None,{
							'_get':get_layer_results,
							'_set':set_layer_results}),
						'hbox2': { '_widget':(2,gtk.HBox,),
							'minus':(0,gtk.Button,{'label':'-'}),
							'_minus':('pack_start',{'expand':False}),
							'plus':(1,gtk.Button,{'label':'+'}),
							'_plus':('pack_start',{'expand':True,'fill':True})
						}
					},
					'_layer_select':('pack_start',{'expand':False,'fill':False}),
					
					'layer_edit':(11,LowerWin,[self]),
					'_layer_edit':('pack_end',{'expand':True,'fill':True}),
					
					'butt':(10,gtk.Button,{'label':'McGoog'}),
					'_butt':('pack_end',{'expand':False,'fill':False})
				}
			}
			
			self.image = img
			self.layer_names = []
			PyWindow.__init__(self,contents=ob,*args,**keys)
			
			t = self.widgets
			t['regex_label'].set_property('width-request',40)
			t['viewport1'].modify_bg(gtk.STATE_NORMAL,gtk.gdk.color_parse('white'))
			t['layer_results'].set_property('height-request',140)
			t['layer_results'].set_policy(gtk.POLICY_AUTOMATIC,gtk.POLICY_ALWAYS)
			t['minus'].set_property('width-request',40)
			
			def meh(w):
				layers = self.__layer_filter()
				self.value['layer_results'] = layers
				sys.stdout.flush()
			t['regex'].connect('changed',meh)
			t['regex'].connect('activate',meh)
			
			layer_table = {}
			def get_t():
				t = {}
				all = layerquery(img.layers,lambda a:True)
				for a,i in zip(all,range(len(all))):
					t[a.name] = i
				return t
			def add_these(w):
				t = get_t()
				r = [(t[n],n) for n in list(set(self.layer_names + self.value['layer_results']))]
				r.sort()
				self.layer_names = [a[1] for a in r]
				print 'added, now:',self.layer_names
				self.widgets['layer_edit'].refresh()
				sys.stdout.flush()
			def remove_these(w):
				t = get_t()
				r = [(t[n],n) for n in list(set(self.layer_names) - set(self.value['layer_results']))]
				r.sort()
				self.layer_names = [a[1] for a in r]
				print 'removed, now:',self.layer_names
				self.widgets['layer_edit'].refresh()
				sys.stdout.flush()
			t['plus'].connect('clicked',add_these)
			t['minus'].connect('clicked',remove_these)
			
			# Eh... minor first-time initializations?
			meh(None)
			self.widgets['layer_edit'].refresh()
			
			sys.stdout.flush()
		
		def __layer_filter(self):
			x = re.compile(self.value['regex'],re.IGNORECASE)
			layers = []
			def call(a,ob,i,param):
				param.append(a)
			layercrawl(self.image.layers,call=call,param=layers)
			return [a for a in layers if x.search(a.name)]
	
	print 'some thang'
	
	w = Win(
		img,
		title='Hue Shift - '+img.name,
		size=[240,600],
		resizable=False)
	
	print 'somer thangs'
	w.show_all()
	gtk.main()
	
	print 'somest thang'
	stdget(stdout,stderr)

register(
	"dupgrid",
	"Duplicate to Grid",
	"Duplicate the current image into a grid.",
	"Cesar Longoria",
	"Cesar Longoria",
	"2016-2017",
	"<Image>/_Pixel/_Duplicate to Grid",
	"RGB*",
	[
		(PF_INT,'countx','Columns',1),
		(PF_INT,'county','Rows',1),
		(PF_TOGGLE,'new_image','Render to new image',False),
		(PF_TOGGLE,'row_groups','Insert groups into row groups',False),
		(PF_TOGGLE,'major_group','Insert all groups into major group',False)
	],
	[],
	dupgrid,
	menu=None,
	domain=None,
	on_query=None,
	on_run=None
)

register(
	"hueshift",
	"Shift hues of matched groups.",
	"Provide a ring of hues and offsets applicable to each of several stated group name matches.",
	"Cesar Longoria",
	"Cesar Longoria",
	"2016-2017",
	"<Image>/_Pixel/_Hue Shift",
	"RGB*",
	[],
	[],
	hueshift,
	menu=None,
	domain=None,
	on_query=None,
	on_run=None
)

stdget(O,E)

main()
