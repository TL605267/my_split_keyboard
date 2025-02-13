#!/usr/bin/env python3
import os, pcbnew
from pcbnew import VECTOR2I, VECTOR2I_MM, FromMM, ToMM, F_Cu, B_Cu
from math import sin, cos, radians

class kbd_place_n_route(pcbnew.ActionPlugin):
	def __init__(self):
		# Initialize column offsets and switch positions
		self.col_offsets = [0, 0, -9, -11.5, -9, -6.5]
		self.sw0_pos = VECTOR2I_MM(60,60)
		self.sw_x_spc = 19 # 17.5 #19.05
		self.sw_y_spc = 17 #19.05
		self.fp_dict = {} # footpint dictionary

	def load_board(self):
		# Load the board file
		if not hasattr(self, 'board'):
			self.filename = [file for file in os.listdir('.') if file.endswith('.kicad_pcb')][0]
			self.board = pcbnew.LoadBoard(self.filename)
		for fp in self.board.GetFootprints():
			self.fp_dict[fp.GetReference()]= {
				'fp': fp,
				'val': fp.GetValue(),
				#'pos': fp.GetPosition(), # position is not updated after placement
				'ref_inst': fp.Reference()
			}
			
	def remove_old_tracks(self):
		# Remove all existing tracks from the board
		for t in self.board.GetTracks():
			self.board.Delete(t)

	def defaults(self):
		# Set default values for the plugin
		self.name = "KBD Placement"
		self.category = "Category name"
		self.description = "Longer description of the plugin"
		self.board = pcbnew.GetBoard()

	def add_track(self, start, end, layer=F_Cu, width=0.2):
		# Add a track to the board
		track = pcbnew.PCB_TRACK(self.board)
		track.SetStart(start)
		track.SetEnd(end)
		track.SetWidth(FromMM(width)) # default 0.2mm
		track.SetLayer(layer)
		self.board.Add(track)

	def add_tracks(self, points): 
		# Add multiple tracks to the board
		# points is a list of tuple: 
		# [(coordinate(VECTOR2I), layer(F_Cu/B_Cu/-1(via))), (,)..]
		for i in range(len(points)-1):
			if (points[i+1][1] < 0): # via
				self.add_via(points[i+1][0], 0.3, 0.6)
				self.add_track(points[i][0], points[i+1][0], points[i][1])
			else: #F_Cu, B_Cu
				self.add_track(points[i][0], points[i+1][0], points[i+1][1])
	
	def add_via(self, pos, drill, width):
		# Add a via to the board
		via = pcbnew.PCB_VIA(self.board)
		via.SetPosition(pos)
		via.SetDrill(FromMM(drill)) # defaults 0.4mm, 0.8mm
		via.SetWidth(FromMM(width))
		self.board.Add(via)
	
	def is_thumb_cluster(self, ref):
		return (ref[-1] == '6' or ref[-1] == '7')

	def place_fp(self, pos, fp, orientation):
		# Place a footprint on the board
		fp.SetPosition(pos) 
		fp.SetOrientationDegrees(orientation)
	
	def rotate(self, origin, point, angle): # TODO
		# Rotate a point counterclockwise by a given angle around a given origin
		ox, oy = origin
		px, py = point
		angle_rad = radians(angle)
		qx = ox + cos(angle_rad) * (px - ox) - sin(angle_rad) * (py - oy)
		qy = oy + sin(angle_rad) * (px - ox) + cos(angle_rad) * (py - oy)
		return qx, qy

	def get_fp_ref_list(self, fp_val):
		# Get a list of footprint references with a specific value
		return [key for key, value in self.fp_dict.items() if value['val'] == fp_val]

	def gen_led_track(self, netname, s_offset = VECTOR2I_MM(0,0)): #TODO put the start point track at top
		# Generate LED track code
		# TODO if no start point is the same, then generate code using add_tracks
		s_list = []
		for t in self.board.GetTracks():
			if t.GetNetname() == netname:
				sx = round(ToMM((t.GetStart()-s_offset).x), 1)
				sy = round(ToMM((t.GetStart()-s_offset).y), 1)
				ex = round(ToMM((t.GetEnd()  -s_offset).x), 1)
				ey = round(ToMM((t.GetEnd()  -s_offset).y), 1)
				if (sx != ex): # remove led via connection
					s_list.append((sx, sy, ex, ey))
		s_list_sorted = sorted(s_list, key=lambda x: x[0])	
		for s in s_list_sorted:
			format_code = f"self.add_track(offset + VECTOR2I_MM({s[0]:>5.1f}, {s[1]:>5.1f}), offset + VECTOR2I_MM({s[2]:>5.1f}, {s[3]:>5.1f}), B_Cu)"
			print(format_code)
		
	def place_sw(self):
		# Place switches on the board
		for sw_ref in self.get_fp_ref_list('SW_Push'): 
			sw_row = int(sw_ref[2])
			sw_col = int(sw_ref[3])
			sw_orienation = 0
			if(sw_col < 6): # 4 fingers
				sw_offset = VECTOR2I_MM(self.sw_x_spc*sw_col, self.sw_y_spc*sw_row + self.col_offsets[sw_col])
				sw_orienation = 0
			# thumb, respective to index bottom switch
			elif (sw_col == 6): 
				sw_offset = VECTOR2I_MM(self.sw_x_spc*5+2.9, self.sw_y_spc*3+14.8)
				sw_orienation = -23
			else: # 7 
				sw_offset = VECTOR2I_MM(self.sw_x_spc*5+23.8, self.sw_y_spc*3+19.8)
				sw_orienation = -30
			# place switches
			self.place_fp(self.sw0_pos+sw_offset, self.fp_dict[sw_ref]['fp'], sw_orienation)
			self.fp_dict[sw_ref]['ref_inst'].SetTextPos(self.sw0_pos+sw_offset + VECTOR2I_MM(4.4, 7.1))
			for item in self.fp_dict[sw_ref]['fp'].GraphicalItems(): #TODO store graphical items in dict
				if type(item) == pcbnew.PCB_TEXT:
					item.SetPosition(self.sw0_pos+sw_offset+VECTOR2I_MM(-4.4,7.1))

	def place_led(self):
		# Place LEDs on the board
		for led_ref in self.get_fp_ref_list('SK6812MINI'):
			idx = led_ref[-2:]
			sw_row = int(idx[0])
			sw_col = int(idx[1])
			sw_pos = self.fp_dict['SW'+idx]['fp'].GetPosition()
			led_pos = sw_pos + VECTOR2I_MM(0, -4.7)
			led_orientation = 0
			if  (sw_col < 6): 
				#self.fp_dict[led_ref]['ref_inst'].SetTextPos(led_pos + VECTOR2I_MM(0, 2.3))
				#TODO separate thumb cluster placement
				if (sw_col == 0 or sw_col == 3 or sw_col == 5):
					led_orientation = 180
				else: # col1/2/5
					led_orientation = 0
			elif(sw_col == 6):
				led_orientation = -23
			else: # 7
				led_orientation = 60
			self.place_fp(led_pos, self.fp_dict[led_ref]['fp'], led_orientation)

	def place_diode(self):
		# Place diodes on the board
		for d_ref in self.get_fp_ref_list('BAV70'):
			# get left switch position
			sw_ref_l = 'SW'+d_ref[1:3]
			sw_pos_l_x = self.fp_dict[sw_ref_l]['fp'].GetPosition().x
			sw_pos_l_y = self.fp_dict[sw_ref_l]['fp'].GetPosition().y
			# get right switch position
			sw_ref_r = 'SW'+d_ref[3:5]
			sw_pos_r_x = self.fp_dict[sw_ref_r]['fp'].GetPosition().x
			sw_pos_r_y = self.fp_dict[sw_ref_r]['fp'].GetPosition().y
			# place diode in between switches
			d_pos = VECTOR2I((sw_pos_l_x + sw_pos_r_x)>>1, min(sw_pos_l_y, sw_pos_r_y))
			self.place_fp(d_pos, self.fp_dict[d_ref]['fp'], 90)
			self.fp_dict[d_ref]['ref_inst'].SetTextPos(d_pos + VECTOR2I_MM(0, 2.4))
			self.fp_dict[d_ref]['ref_inst'].SetTextAngleDegrees(180)

	def place_via_for_led(self): 
		# Place vias on the board
		via_pad_offset = 0.3
		for led_ref in self.get_fp_ref_list('SK6812MINI'):
			if not self.is_thumb_cluster(led_ref): # skip thumb cluster
				led_pos = self.fp_dict[led_ref]['fp'].GetPosition()
				# FIXME not sure why all pad.getlayer reurns F.Cu
				for pad in self.fp_dict[led_ref]['fp'].Pads():
					#print(led_ref, pad.GetNumber(), pad.GetLayer(), pad.IsOnLayer(F_Cu), pad.GetNetname())
					#skip GND net since it will be connected by copper pour
					if pad.IsOnLayer(F_Cu) and pad.GetNetname() != 'GND':
						pad_pos = pad.GetCenter()
						if   pad.GetNumber() == '1': # LED DIN
							# place via in the middle
							via_pos = VECTOR2I(pad_pos.x, led_pos.y)
						elif pad.GetNumber() == '3': # LED DOUT
							# place via in a bit left
							via_pos = VECTOR2I(pad_pos.x - FromMM(via_pad_offset), led_pos.y)
						elif pad.GetNumber() == '4': # +5V Net
							# place via in a bit right
							via_pos = VECTOR2I(pad_pos.x + FromMM(via_pad_offset), led_pos.y)

						track_start = VECTOR2I(via_pos.x, pad_pos.y)
						track_end   = VECTOR2I(via_pos.x, led_pos.y*2-pad_pos.y) # reflect
						self.add_track(track_start, via_pos, F_Cu)
						self.add_via(via_pos, 0.3, 0.4)
						self.add_track(track_end  , via_pos, B_Cu)

	#TODO def connect_thumb_cluster(self):
	#rotate thumb keys and connect
	def place_mcu(self):
		for mcu_ref in self.get_fp_ref_list('CH582'):
			self.place_fp(VECTOR2I_MM(168, 48), self.fp_dict[mcu_ref]['fp'], 0)
			
	def place_misc(self):
		# Place misc components on the board
		self.place_fp(VECTOR2I_MM(175.6, 50), self.fp_dict['R1']['fp'], 180)
		self.fp_dict['R1']['fp'].Flip(self.fp_dict['R1']['fp'].GetPosition(), False)
		self.place_fp(VECTOR2I_MM(175.6, 58), self.fp_dict['R2']['fp'], 0)
		self.fp_dict['R2']['fp'].Flip(self.fp_dict['R2']['fp'].GetPosition(), False)
		self.place_fp(VECTOR2I_MM(175.6, 54), self.fp_dict['JP1']['fp'], 0)
		self.fp_dict['JP1']['fp'].Flip(self.fp_dict['JP1']['fp'].GetPosition(), False)
		self.place_fp(VECTOR2I_MM(183.7, 131.6), self.fp_dict['JP2']['fp'], 180)

	def place_connector(self):
		# Place connectors on the board
		for conn_ref in self.get_fp_ref_list('Conn_01x12_MountingPin'):
			if 'LEFT' in conn_ref: # place and flip the left connector back
				self.fp_dict[conn_ref]['fp'].Flip(self.fp_dict[conn_ref]['fp'].GetPosition(), False)
				self.place_fp(self.sw0_pos + VECTOR2I_MM(116, 35), self.fp_dict[conn_ref]['fp'], -45)
			else: # place the right connector
				self.place_fp(self.sw0_pos + VECTOR2I_MM(116, 35), self.fp_dict[conn_ref]['fp'], 135)

	def place_via_for_connector(self):
		# Place vias on the board
		for conn_ref in self.get_fp_ref_list('Conn_01x12_MountingPin'):
			if 'RIGHT' in conn_ref: # doesn't metter left or right, just pick one to get the pad position
				for pad in self.fp_dict[conn_ref]['fp'].Pads():
					# skip mounting pad, GND and unconnected pad
					if pad.GetNumber() != 'MP' and pad.GetNumber() != '11' and pad.GetNumber != '12': 
						self.add_tracks([
							(pad.GetCenter(), F_Cu),
							(pad.GetCenter()+VECTOR2I_MM(1.6, -1.6), -1), #via
							(pad.GetCenter(), B_Cu)
						])

	def place_shift_register_and_resistor(self):
		for sr_ref in self.get_fp_ref_list('74HC165'):
			if 'LEFT' in sr_ref:
				self.fp_dict[sr_ref]['fp'].Flip(self.fp_dict[sr_ref]['fp'].GetPosition(), False) # flip back
				self.place_fp(self.sw0_pos + VECTOR2I_MM(119, 52), self.fp_dict[sr_ref]['fp'], 0)
			else:
				self.place_fp(self.sw0_pos + VECTOR2I_MM(114, 52), self.fp_dict[sr_ref]['fp'], 180)
		for r_ref in self.get_fp_ref_list('R_Pack08'):
			if 'LEFT' in r_ref:
				self.fp_dict[r_ref]['fp'].Flip(self.fp_dict[r_ref]['fp'].GetPosition(), False)
				self.place_fp(self.sw0_pos + VECTOR2I_MM(127.8  , 52), self.fp_dict[r_ref]['fp'], 0)
			else:
				self.place_fp(self.sw0_pos + VECTOR2I_MM(126, 52), self.fp_dict[r_ref]['fp'], 180)

	def connect_pad1(self):
		# Connect switch pad1 on both F_Cu and B_Cu layer
		for sw_ref in self.get_fp_ref_list('SW_Push'): 
			if not self.is_thumb_cluster(sw_ref): # skip thumb cluster
				sw_pos = self.fp_dict[sw_ref]['fp'].GetPosition()
				# pad1
				self.add_tracks([	
					(sw_pos+(VECTOR2I_MM( 3.3, 6.0)), B_Cu), 
					(sw_pos+(VECTOR2I_MM( 1.5, 4.0)), B_Cu),
					(sw_pos+(VECTOR2I_MM(-2.2, 4.0)), -1  ) #Via
				])

	def connect_diode_and_sw(self):
		# Connect diode and switches pad2 on both F_cu and B_Cu layer
		for d_ref in self.get_fp_ref_list('BAV70'):
			if not self.is_thumb_cluster(d_ref): # skip thumb cluster
				# each diode is named in the format of DXXYY, 
				# where YY is the left switch and YY is the right switch
				# connect diode to the switch on its left
				sw_ref_l = 'SW'+d_ref[1:3]
				sw_pos_l = self.fp_dict[sw_ref_l]['fp'].GetPosition()
				# Get pad2 y coordinate. 
				# There are two pad 2 on the switch footprint, 
				# but one of them is flipped to the back side for reverse mount. 
				# therefore their y coordinate is the same, we can use either one
				for pad in self.fp_dict[sw_ref_l]['fp'].Pads():
					if pad.GetNumber() == '2':
						sw_l_pad2_y = pad.GetCenter().y
						break
				d_p1_pos = self.fp_dict[d_ref]['fp'].FindPadByNumber('1').GetCenter()
				# Added hard-coded track to connect diode to the switch
				self.add_tracks([
					(VECTOR2I(d_p1_pos.x, sw_l_pad2_y), F_Cu),
					(d_p1_pos                         , F_Cu),
					(sw_pos_l+VECTOR2I_MM( 5.8, 2.0)  , B_Cu),
					(sw_pos_l+VECTOR2I_MM(-6.5, 2.0)  , B_Cu),
					(sw_pos_l+VECTOR2I_MM(-8.2, 3.6)  , B_Cu)
				])
				# connect diode to the switch on its right
				sw_ref_r = 'SW'+d_ref[3:5]
				sw_pos_r = self.fp_dict[sw_ref_r]['fp'].GetPosition()
				for pad in self.fp_dict[sw_ref_r]['fp'].Pads():
					if pad.GetNumber() == '2':
						sw_r_pad2_y = pad.GetCenter().y
						break
				d_p2_pos = self.fp_dict[d_ref]['fp'].FindPadByNumber('2').GetCenter()
				# Hard-coded track to connect diode to the switch
				self.add_tracks([
					(d_p2_pos                         , B_Cu),
					(VECTOR2I(d_p2_pos.x, sw_r_pad2_y), B_Cu),
					(sw_pos_r+VECTOR2I_MM(-6.5, 2.0)  , B_Cu),
					(sw_pos_r+VECTOR2I_MM( 8.2, 2.0)  ,   -1), # via
					(sw_pos_r+VECTOR2I_MM( 8.2, 3.6)  , F_Cu)
				])
		
	def connect_sw_col(self):
		# Connect column pads from top to bottom
		for col in range(6): # 6 column
			start = self.sw0_pos + VECTOR2I_MM(-2.2, 4.0) + VECTOR2I_MM(self.sw_x_spc*col, self.col_offsets[col])
			end   = self.sw0_pos + VECTOR2I_MM(-2.2, 5.2) + VECTOR2I_MM(self.sw_x_spc*col, self.col_offsets[col]+ self.sw_y_spc*3)
			self.add_track(start, end, F_Cu)

	def connect_rows(self):
		# Connect rows
		for diode_ref in self.get_fp_ref_list('BAV70'): 
			if diode_ref.endswith('1'): # left most col
				padk_pos = self.fp_dict[diode_ref]['fp'].FindPadByNumber('3').GetCenter() # offset
				# the following code is auto generated by gen_led_track
				self.add_track(padk_pos + VECTOR2I_MM(  0.0,   0.0), padk_pos + VECTOR2I_MM(  1.0,  -1.0), B_Cu)
				self.add_track(padk_pos + VECTOR2I_MM(  1.0,  -1.0), padk_pos + VECTOR2I_MM( 13.9,  -1.0), B_Cu)
				self.add_track(padk_pos + VECTOR2I_MM( 13.9,  -1.0), padk_pos + VECTOR2I_MM( 22.9, -10.0), B_Cu)
				self.add_track(padk_pos + VECTOR2I_MM( 22.9, -10.0), padk_pos + VECTOR2I_MM( 35.3, -10.0), B_Cu)
				self.add_track(padk_pos + VECTOR2I_MM( 35.3, -10.0), padk_pos + VECTOR2I_MM( 40.7, -12.5), B_Cu)
				self.add_track(padk_pos + VECTOR2I_MM( 40.7, -12.5), padk_pos + VECTOR2I_MM( 52.6, -12.5), B_Cu)
				self.add_track(padk_pos + VECTOR2I_MM( 52.6, -12.5), padk_pos + VECTOR2I_MM( 55.1, -10.0), B_Cu)
				self.add_track(padk_pos + VECTOR2I_MM( 55.1, -10.0), padk_pos + VECTOR2I_MM( 75.0, -10.0), B_Cu)
				self.add_track(padk_pos + VECTOR2I_MM( 75.0, -10.0), padk_pos + VECTOR2I_MM( 76.0,  -9.0), B_Cu)

	def connect_leds_by_col(self):
		# Connect LEDs by column
		for sw_ref in self.get_fp_ref_list('SW_Push'):
			if not self.is_thumb_cluster(sw_ref): # skip thumb cluster
				sw_col = int(sw_ref[-1])
				sw_row = int(sw_ref[-2])
				offset = self.fp_dict[sw_ref]['fp'].GetPosition()
				if sw_row == 0: # top row
					# power rail - left
					virtical_track_length = 3*self.sw_y_spc - (9.0-3.8)
					self.add_tracks([
						(offset + VECTOR2I_MM(-3.3, -5.5), F_Cu),	
						(offset + VECTOR2I_MM(-5.0, -5.5), F_Cu),	
						(offset + VECTOR2I_MM(-6.7, -3.8), F_Cu), 
						(offset + VECTOR2I_MM(-6.7, -3.8 + virtical_track_length), F_Cu) 
					])
					# power rail - right
					virtical_track_length = 3*self.sw_y_spc - (7.3-0.5)
					self.add_tracks([
						(offset + VECTOR2I_MM( 3.3, -3.9), F_Cu),
						(offset + VECTOR2I_MM( 6.7, -0.5), F_Cu),
						(offset + VECTOR2I_MM( 6.7, -0.5 + virtical_track_length), F_Cu)
					])
				else:
					# power rail - left
					self.add_track(offset + VECTOR2I_MM(-3.3, -5.6), offset + VECTOR2I_MM(-6.7, -9.0))	
					# power rail - right
					self.add_track(offset + VECTOR2I_MM(3.3, -3.9), offset + VECTOR2I_MM(6.7, -7.3))
					# led dout -> led din
					virtical_track_length = self.sw_y_spc - 2.6
					self.add_tracks([
						(offset + VECTOR2I_MM(-3.3, -5.5), B_Cu),
						(offset + VECTOR2I_MM(-1.9, -6.9), B_Cu),
						(offset + VECTOR2I_MM( 2.1, -6.9),   -1), # via
						(offset + VECTOR2I_MM( 2.1, -6.9-virtical_track_length), F_Cu),
						(offset + VECTOR2I_MM( 3.3,-22.5), F_Cu)
					])
				
	def connect_shift_register_and_resistor(self):
		for r_ref in self.get_fp_ref_list('R_Pack08'):
			pad9_pos  = self.fp_dict[r_ref]['fp'].FindPadByNumber( '9').GetCenter()
			pad16_pos = self.fp_dict[r_ref]['fp'].FindPadByNumber('16').GetCenter()
			if 'LEFT' in r_ref: # left hand componments are placed in the back
				self.add_track(pad9_pos, pad16_pos, B_Cu)
			else:
				self.add_track(pad9_pos, pad16_pos, F_Cu)
				# also connects left and right
				for pad in self.fp_dict[r_ref]['fp'].Pads():
					#print(pad.GetNumber())
					if pad.GetNumber().isdigit() and int(pad.GetNumber()) < 9: # pad 1-8
						pad_pos = pad.GetCenter()
						if int(pad.GetNumber()) %2 == 0 : #2/4/6/8
							self.add_track(pad_pos, pad_pos + VECTOR2I_MM(0.9, 0), B_Cu)
							self.add_via(pad_pos + VECTOR2I_MM(0.9, 0), 0.3, 0.4)
							self.add_track(pad_pos + VECTOR2I_MM(0.9, 0), pad_pos, F_Cu)
						else: #1/3/5/7
							self.add_track(pad_pos, pad_pos + VECTOR2I_MM(-0.9, 0), B_Cu)
							self.add_via(pad_pos + VECTOR2I_MM(-0.9, 0), 0.3, 0.4)
							self.add_track(pad_pos + VECTOR2I_MM(-0.9, 0), pad_pos, F_Cu)
			
	def place_edge_cut(self): 
		# Place edge cuts on the board
		# get highest y coordinate (column 3)
		upper_edge_y = self.fp_dict['SW03']['fp'].GetPosition().y - FromMM(10)
		# get top right corner
		right_edge_x = self.fp_dict['SW37']['fp'].GetPosition().x + FromMM(15)
		# get bottom left corner x coordinate (column 0)
		left_edge_x = self.sw0_pos.x - FromMM(10)
		# get bottom left corner x coordinate (column 0)
		lower_left_y = self.fp_dict['SW30']['fp'].GetPosition().y + FromMM(10)
		# get lower right y coordinate (column 7)
		lower_right_y = self.fp_dict['SW37']['fp'].GetPosition().y + FromMM(10)
		edge_cut_tracks = [
			VECTOR2I(right_edge_x, upper_edge_y ),
			VECTOR2I( left_edge_x, upper_edge_y ),
			VECTOR2I( left_edge_x, lower_left_y ),
			VECTOR2I(right_edge_x, lower_right_y),
			VECTOR2I(right_edge_x, upper_edge_y )
		]
		track = pcbnew.PCB_SHAPE(self.board)
		track.SetShape(pcbnew.SHAPE_T_POLY)
		track.SetFilled(False)
		track.SetLayer(pcbnew.Edge_Cuts)
		track.SetWidth(FromMM(0.1))
		track.SetStart(edge_cut_tracks[0])
		track.SetPolyPoints(edge_cut_tracks)
		self.board.Add(track)
	
	def place_mounting_hole(self): #TODO
		# Place mounting holes on the board
		mounting_hole = pcbnew.MODULE(self.board)
		mounting_hole.SetPosition(VECTOR2I_MM(0, 0))
		mounting_hole.SetOrientation(0)
		mounting_hole.SetFPID(pcbnew.FPID("MountingHole"))
		self.board.Add(mounting_hole)

	def place_cupper_pour(self): #TODO
		# Place copper pour on the board
		copper_pour = pcbnew.ZONE_CONTAINER(self.board)
		copper_pour.SetPosition(VECTOR2I_MM(0, 0))
		copper_pour.SetOrientation(0)
		copper_pour.SetFPID(pcbnew.FPID("CopperPour"))
		self.board.Add(copper_pour)

	# Do all the things
	def Run(self):
		# Execute the plugin
		self.load_board()
		self.remove_old_tracks()
		self.place_sw()
		self.place_led()
		self.place_via_for_led()
		self.place_diode()
		self.place_mcu()
		self.place_misc()
		self.place_shift_register_and_resistor()
		self.place_connector()
		self.place_via_for_connector()
		self.connect_diode_and_sw()
		#self.connect_thumb_cluster()
		self.connect_rows()
		self.connect_pad1()
		self.connect_sw_col()
		self.connect_leds_by_col()
		self.connect_shift_register_and_resistor()
		self.place_edge_cut()
		pcbnew.Refresh()
		pcbnew.SaveBoard(self.filename, self.board)
		
#kbd_place_n_route().register()

def main():
	plugin = kbd_place_n_route()
	'''
	print('# POWER RAIL TOP PAD')
	plugin.gen_led_track('+5V')
	print('# POWER RAIL BOTTOM PAD')
	plugin.gen_led_track('GND')
	for i in range(5):
		print(f'# LEDx{i}')
		plugin.gen_led_track(f'Net-(LED0{i}-DIN)')
	'''
	plugin.Run()
	#plugin.load_board()
	#plugin.remove_old_tracks()
	#plugin.place_via_for_led()
if __name__ == "__main__":
	main()