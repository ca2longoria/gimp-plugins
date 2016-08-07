
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
			ob = {
				'box': { '_widget':(gtk.VBox,),
					
					'texty':(0,gtk.TextView,),
					'_texty':('pack_start',{'expand':False,'fill':False}),
					
					'colory':(1,gtk.ColorButton,),
					'_colory':('pack_start',{'expand':False,'fill':False,
						'_get':lambda w:w.get_color()}),
					
					'text2':(11,gtk.TextView,),
					# TODO: Let '_*' companion keys carry multiple lists of
					#   additional commands.
					'_text2':('pack_end',{'expand':False,'fill':False,
						'_get':lambda w:'Noodles'}),
					
					'butt':(10,gtk.Button,{'label':'McGoog'}),
					'_butt':('pack_end',{'expand':False,'fill':False})
				}
			}
			def do_thing(w):
				print 'thing be do!',self.value['colory']
				sys.stdout.flush()
			
			PyWindow.__init__(self,contents=ob,*args,**keys)
			t = self.widgets
			t['texty'].set_size_request(-1,24)
			t['butt'].connect('clicked',do_thing)
			
			# Get img layers, storing as self.layers.
			names = []
			def call(layer,ob,i,param):
				param.append(layer.name)
			layercrawl(img.layers,call=call,param=names)
			self.layers = names
			print 'self.layers', self.layers
			
			# Looks like this works well.
			self.value['texty'] = 'Saussagge'
			
			print 'color value:', self.value['colory']
			
			sys.stdout.flush()
	
	print 'some thang'
	
	w = Win(
		img,
		title='Hue Shift',
		size=[200,400],
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
