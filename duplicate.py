
import sys
import json
from gimpfu import *
from pyfu import *

debug_path = 'd:\\tmp\\pyfu'

def dupright(img,draw,countx=1,county=1,new_image=False,row_groups=False,major_group=False):
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
	
	stdget(stdout,stderr)

register(
	"dupright",
	"Duplicate to Grid",
	"Duplicate the current image into a grid.",
	"Cesar Longoria",
	"Cesar Longoria",
	"2016-2017",
	"<Image>/_Pixel/_Duplicate to Grid",
	"RGB*",
	[
		(PF_INT,'countx','Grid width',1),
		(PF_INT,'county','Grid height',1),
		(PF_TOGGLE,'new_image','Render to new image',False),
		(PF_TOGGLE,'row_groups','Insert groups into row groups',False),
		(PF_TOGGLE,'major_group','Insert all groups into major group',False)
	],
	[],
	dupright,
	menu=None,
	domain=None,
	on_query=None,
	on_run=None
)

main()
