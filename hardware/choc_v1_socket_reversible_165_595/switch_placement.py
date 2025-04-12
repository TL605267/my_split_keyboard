#!/usr/bin/env python3
from os import listdir
from math import sin, cos, radians
from pcbnew import *
import sys

class kbd_place_n_route(ActionPlugin):
	def __init__(self, is_fast_mode=False):
		# Initialize column offsets and switch positions
		self.col_offsets = [0, 0, -9, -11.5, -9, -6.5]
		self.sw0_pos = VECTOR2I_MM(60,60)
		self.sw_x_spc = 19 # 17.5 #19.05
		self.sw_y_spc = 17 #19.05
		self.fp_dict = {} # footpint dictionary
		self.is_fast_mode = is_fast_mode

	def load_board(self):
		# Load the board file
		if not hasattr(self, 'board'):
			self.filename = [file for file in listdir('.') if file.endswith('.kicad_pcb') and 'auto' not in file][0]
			self.board = LoadBoard(self.filename)
		for fp in self.board.GetFootprints():
			ref = fp.GetReference()
			self.fp_dict[ref]= {
				'fp': fp,
				'ref': ref,
				'val': fp.GetValue(),
				'pos': VECTOR2I_MM(0,0),  # can't get shallow copy from fp.GetPosition()
				'ori': 0, # orientation is not updated after placement
				'ref_inst': fp.Reference(),
				'padF': {},
				'padB': {}
			}

	def update_pad_pos(self):
		for pad in self.board.GetPads():
			if pad.GetNumber() != '': # skip mounting pad
				if pad.IsOnLayer(F_Cu):
					self.fp_dict[pad.GetParentAsString()]['padF'][pad.GetNumber()] = {
						'pos': pad.GetCenter(),
						'net': pad.GetNetname()
					}
				elif pad.IsOnLayer(B_Cu):	
					self.fp_dict[pad.GetParentAsString()]['padB'][pad.GetNumber()] = {
						'pos': pad.GetCenter(),
						'net': pad.GetNetname()
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
		self.board = GetBoard()

	def add_track(self, start, end, layer=F_Cu, width=0.2):
		# Add a track to the board
		track = PCB_TRACK(self.board)
		track.SetStart(start)
		track.SetEnd(end)
		if (width != 0.2):
			track.SetWidth(FromMM(width)) # default 0.2mm
		if (layer != F_Cu):
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
		via = PCB_VIA(self.board)
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
		# update fp_dict
		self.fp_dict[fp.GetReference()]['pos'] = pos
		self.fp_dict[fp.GetReference()]['ori'] = orientation
	
	def rotate(self, origin, point, angle): 
		# Rotate a point counterclockwise by a given angle around a given origin
		if angle == 0:
			return point
		translated_point = point - origin
		angle_rad = radians(angle)
		rotated_x = translated_point.x * cos(angle_rad) + translated_point.y * sin(angle_rad)
		rotated_y = -(translated_point.x * sin(angle_rad) - translated_point.y * cos(angle_rad))
		return VECTOR2I(int(origin.x + rotated_x), int(origin.y + rotated_y))
	
	def get_fp(self, fp_val):
		# Get a list of footprint references with a specific value
			results = [value for value in self.fp_dict.values() if fp_val in value['val']]
			if not results:
				raise ValueError(f"No matching footprints found for value: {fp_val}")
			return results

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
		
	def gen_fp_placement(self):
		# Place switches on the board
		for sw in self.get_fp('SW_Push'): 
			sw_row = int(sw['ref'][2])
			sw_col = int(sw['ref'][3])
			sw_orienation = 0
			if(sw_col < 6): # 4 fingers
				sw_offset = VECTOR2I_MM(self.sw_x_spc*sw_col, self.sw_y_spc*sw_row + self.col_offsets[sw_col])
				sw_orienation = 0
			# thumb, respective to index bottom switch
			elif (sw_col == 6): 
				if sw_row == 2: # thumb cluster
					sw_offset = VECTOR2I_MM(self.sw_x_spc*5+2.9, self.sw_y_spc*3+14.8)
					sw_orienation = -23
				elif sw_row == 3: # thumb cluster
					sw_offset = VECTOR2I_MM(self.sw_x_spc*5+23.8, self.sw_y_spc*3+19.8)
					sw_orienation = -30
			sw['pos'] = self.sw0_pos+sw_offset
			sw['ori'] = sw_orienation
			led_ref = 'LED'+sw['ref'][-2:]
			self.fp_dict[led_ref]['pos'] = self.rotate(sw['pos'], sw['pos'] + VECTOR2I_MM(0,-4.7), sw['ori'])
			self.fp_dict[led_ref]['ori'] = sw_orienation

	def place_sw(self):
		# Place switches on the board
		for sw in self.get_fp('SW_Push'): 
			# place switches
			self.place_fp(sw['pos'], sw['fp'], sw['ori'])
			# Move text
			sw['ref_inst'].SetTextPos(sw['pos'] + VECTOR2I_MM(4.4, 7.1))
			for item in sw['fp'].GraphicalItems(): #TODO store graphical items in dict
				if type(item) == PCB_TEXT:
					item.SetPosition(sw['pos']+VECTOR2I_MM(-4.4,7.1))

	def place_led(self):
		# Place LEDs on the board
		for led in self.get_fp('SK6812MINI'):
			self.place_fp(led['pos'], led['fp'], led['ori'])

	def place_diode(self):
		# Place diodes on the board
		for diode in self.get_fp('BAW56DW'):
			# get top switch position
			sw_ref_t = 'SW3'+diode['ref'][1:3]
			sw_pos_t = self.fp_dict[sw_ref_t]['pos']
			if not self.is_thumb_cluster(diode['ref']):
				# place diode in between switches
				d_pos = sw_pos_t + VECTOR2I_MM(-7.5, 8.2)
			else :
				d_pos = sw_pos_t + VECTOR2I_MM(-10, 5)
			diode['pos'] = d_pos
			self.place_fp(diode['pos'], diode['fp'], 180)
			diode['fp'].Flip(d_pos, False)
			diode['ref_inst'].SetTextPos(d_pos + VECTOR2I_MM(0, 2.4))
			diode['ref_inst'].SetTextAngleDegrees(180)
				

	def place_via_for_led(self): 
		# Place vias on the board
		for led in self.get_fp('SK6812MINI'):
			#skip GND net since it will be connected by copper pour
			via_offset = {'1': 3.3, '3': -3, '4': -3.6}
			for i in ['1', '3', '4']:
				via_pos = self.rotate(led['pos'], led['pos'] + VECTOR2I_MM(via_offset[i],0), led['ori'])
				start_pos = self.rotate(led['pos'], VECTOR2I(led['pos'].x+FromMM(via_offset[i]), led['padF'][i]['pos'].y), led['ori'])
				end_pos   = self.rotate(led['pos'], VECTOR2I(led['pos'].x+FromMM(via_offset[i]), led['padB'][i]['pos'].y), led['ori'])
				#self.add_track(start_pos, via_pos, F_Cu)
				#self.add_track(end_pos, via_pos, B_Cu)
				self.add_track(led['padF'][i]['pos'], via_pos, F_Cu)
				self.add_track(led['padB'][i]['pos'], via_pos, B_Cu)
				self.add_via(via_pos, 0.3, 0.4)

	def place_via_for_diode(self):
		for diode in self.get_fp('BAW56DW'):
			# place via
			for i in range(-2, 3):
				self.add_via(diode['pos']+VECTOR2I_MM(0,i*0.65), 0.3, 0.4)
			# connect 
			for i in ['1', '2', '3']:
				self.add_track(diode['padF'][i]['pos'], diode['padF'][i]['pos']+VECTOR2I_MM( 0.95,-0.65), F_Cu)	
				self.add_track(diode['padF'][i]['pos'], diode['padF'][i]['pos']+VECTOR2I_MM( 0.95, 0.65), B_Cu)	
			for i in ['4', '5', '6']:
				self.add_track(diode['padF'][i]['pos'], diode['padF'][i]['pos']+VECTOR2I_MM(-0.95, 0.65), F_Cu)	
				self.add_track(diode['padF'][i]['pos'], diode['padF'][i]['pos']+VECTOR2I_MM(-0.95,-0.65), B_Cu)	

	#TODO def connect_thumb_cluster(self):
	#rotate thumb keys and connect
	def place_mcu(self):
		for mcu in self.get_fp('CH582'):
			self.place_fp(VECTOR2I_MM(168, 48), mcu['fp'], 0)
			
	def place_misc(self):
		# Place misc components on the board
		self.place_fp(VECTOR2I_MM(175.6, 50), self.fp_dict['R1']['fp'], 180)
		self.fp_dict['R1']['fp'].Flip(self.fp_dict['R1']['fp'].GetPosition(), False)
		self.place_fp(VECTOR2I_MM(175.6, 58), self.fp_dict['R2']['fp'], 0)
		self.fp_dict['R2']['fp'].Flip(self.fp_dict['R2']['fp'].GetPosition(), False)
		self.place_fp(VECTOR2I_MM(175.6, 54), self.fp_dict['JP1']['fp'], 0)
		self.fp_dict['JP1']['fp'].Flip(self.fp_dict['JP1']['fp'].GetPosition(), False)
		# self.place_fp(VECTOR2I_MM(183.7, 131.6), self.fp_dict['JP2']['fp'], 180) JP2 is removed

	def place_connector(self):
		# Place connectors on the board
		self.fp_dict['J_LEFT1']['fp'].Flip(self.fp_dict['J_LEFT1']['fp'].GetPosition(), False)
		self.place_fp(self.sw0_pos + VECTOR2I_MM(116, 35), self.fp_dict['J_LEFT1']['fp'], 135)
		self.place_fp(self.sw0_pos + VECTOR2I_MM(116, 35), self.fp_dict['J_RIGHT1']['fp'], -45)

	def place_via_for_connector(self):
		# Place vias on the board
		for conn in self.get_fp('FPC'):
			if 'RIGHT' in conn['ref']: # doesn't metter left or right, just pick one to get the pad position
				for pad in conn['fp'].Pads():
					# skip mounting pad, GND and unconnected pad
					if pad.GetNumber().isdigit(): # and int(pad.GetNumber()) %2:
						if pad.GetNetname() == 'GND': # handled by copper pour
							pass
						elif 'unconnected' not in pad.GetNetname():
							self.add_tracks([
								(pad.GetCenter(), F_Cu),
								(pad.GetCenter()+VECTOR2I_MM(1.6, -1.6), -1), #via
								(pad.GetCenter(), B_Cu),
							])

	def place_shift_register_and_resistor(self):
		# shift register
		self.fp_dict['SR_LEFT1']['fp'].Flip(self.fp_dict['SR_LEFT1']['fp'].GetPosition(), False)
		self.place_fp(self.sw0_pos + VECTOR2I_MM(119, 52), self.fp_dict['SR_LEFT1']['fp'], 0)
		self.place_fp(self.sw0_pos + VECTOR2I_MM(114, 52), self.fp_dict['SR_RIGHT1']['fp'], 180)
		# resistor network
		for k, v in enumerate(['5', '4', '3', '2', '1', '0', '6', '7']):
			rl_ref = 'R_L' + v
			self.fp_dict[rl_ref]['fp'].Flip(self.fp_dict[rl_ref]['fp'].GetPosition(), False)
			rr_ref = 'R_R' + v
			self.place_fp(self.fp_dict['SR_LEFT1']['pos'] + VECTOR2I_MM(11, (k-3.5)*3), self.fp_dict[rl_ref]['fp'], 180)
			self.place_fp(self.fp_dict['SR_LEFT1']['pos'] + VECTOR2I_MM( 9, (k-3.5)*3), self.fp_dict[rr_ref]['fp'], 0)
			''' TODO move silkscreen text
			for item in self.fp_dict[rl_ref]['fp'].GraphicalItems():
				if type(item) == PCB_TEXT:
					item.SetPosition(self.fp_dict[rl_ref]['pos']+VECTOR2I_MM(-3.9, 0))
			for item in self.fp_dict[rr_ref]['fp'].GraphicalItems():
				print(item)
				if type(item) == PCB_TEXT:
					item.SetPosition(self.fp_dict[rr_ref]['pos']+VECTOR2I_MM( 3.9, 0))
			'''

	def connect_pad1(self):
		# Connect switch pad1 on both F_Cu and B_Cu layer
		for sw in self.get_fp('SW_Push'):
			self.add_tracks([
				(self.rotate(sw['pos'], sw['pos'] + VECTOR2I_MM( 3.3, 6.0), sw['ori']), B_Cu),
				(self.rotate(sw['pos'], sw['pos'] + VECTOR2I_MM( 1.5, 4.0), sw['ori']), B_Cu),
				(self.rotate(sw['pos'], sw['pos'] + VECTOR2I_MM(-2.7, 4.0), sw['ori']), -1),
				(self.rotate(sw['pos'], sw['pos'] + VECTOR2I_MM(-2.7, 5.4), sw['ori']), F_Cu)
			])

	def connect_pad2(self):
		# Connect switch pad2 on both F_Cu and B_Cu layer
		for sw in self.get_fp('SW_Push'):
			self.add_tracks([
				(self.rotate(sw['pos'], sw['pos'] + VECTOR2I_MM(-8.2, 3.6), sw['ori']), B_Cu),
				(self.rotate(sw['pos'], sw['pos'] + VECTOR2I_MM(-6.5, 2.0), sw['ori']), B_Cu),
				(self.rotate(sw['pos'], sw['pos'] + VECTOR2I_MM( 7.5, 2.0), sw['ori']),   -1), # via
				(self.rotate(sw['pos'], sw['pos'] + VECTOR2I_MM( 8.2, 3.6), sw['ori']), F_Cu)
			])
			# connect via to sw on the right
			if sw['ref'][-1] != '5' and sw['ref'][-1] != '6':
				sw_r = sw['ref'][:-1]+str(int(sw['ref'][-1])+1)
				self.add_tracks([
					(sw['pos']+VECTOR2I_MM( 7.5, 2.0),   B_Cu), # via
					(self.fp_dict[sw_r]['padB']['2']['pos'], B_Cu)
				])
				
	def connect_diode_and_sw(self):
		# Connect diode and switches pad1 on both F_cu and B_Cu layer
		for diode in self.get_fp('BAW56DW'):
			if not self.is_thumb_cluster(diode['ref']): # skip thumb cluster
				# ROW0
				sw_r0_ref = 'SW0'+diode['ref'][-1]
				self.add_tracks([
					(diode['padF']['1']['pos']+VECTOR2I_MM(0.95,-0.65), F_Cu),
					(diode['padF']['1']['pos']+VECTOR2I_MM(0.95,-48.4), F_Cu),
					(self.fp_dict[sw_r0_ref]['padF']['1']['pos'], F_Cu)
				])
				# ROW1
				sw_r1_ref = 'SW1'+diode['ref'][-1]
				self.add_tracks([
					(diode['padF']['1']['pos']+VECTOR2I_MM(0.95, 0), F_Cu),
					(diode['padF']['1']['pos']+VECTOR2I_MM(1.35,-0.4), F_Cu),
					(diode['padF']['1']['pos']+VECTOR2I_MM(1.35,-31.8), F_Cu),
					(self.fp_dict[sw_r1_ref]['padF']['1']['pos'], F_Cu)
				])
				# ROW2
				sw_r2_ref = 'SW2'+diode['ref'][-1]
				self.add_tracks([
					(diode['padF']['5']['pos'], F_Cu),
					(diode['padF']['5']['pos']+VECTOR2I_MM( 0.6,-0.2), F_Cu),
					(diode['padF']['5']['pos']+VECTOR2I_MM( 0.6,-0.9), F_Cu),
					(diode['padF']['5']['pos']+VECTOR2I_MM(-0.2,-1.6), F_Cu),
					(diode['padF']['5']['pos']+VECTOR2I_MM(-0.2,-15.7), F_Cu),
					(self.fp_dict[sw_r2_ref]['padF']['1']['pos'], F_Cu)
				])
				# ROW3
				sw_r3_ref = 'SW3'+diode['ref'][-1]
				self.add_tracks([
					(diode['padF']['4']['pos']+VECTOR2I_MM(0.2,0), F_Cu),
					(self.fp_dict[sw_r3_ref]['padF']['1']['pos'], F_Cu)
				])

	def connect_sw_col(self):
		# Connect column pads (anode of diode) to shift register
		p1_offset = VECTOR2I_MM(165.6, 114.1)
		for i in range(5,-1,-1): # index finger to ring finger
			p0 = self.fp_dict['SR_RIGHT1']['padF']['11']['pos'] + VECTOR2I_MM(-1.9, 0.635*(5-i))
			p1 = p1_offset + VECTOR2I_MM((5-i)*0.3, (5-i)*0.3)
			d_ref = 'D' + str(i) # diode connected to SR
			p2 = VECTOR2I(0,0)
			p2.y = p1.y
			if i <= 1: # pinky finger
				p2.x = FromMM(92-0.2*i)
				# FIXME p3
				# TODO p4 p5
				# TODO p6 = 	self.fp_dict[d_ref]['padB']['3']['pos']
				self.add_tracks([
					(p0, B_Cu),
					(p1, B_Cu),
					(p2, B_Cu),
					# FIXME (p3, B_Cu),
				])
			else:
				p2.x = self.fp_dict[d_ref]['pos'].x + FromMM(5)
				p3 = 	self.fp_dict[d_ref]['padB']['3']['pos']
				self.add_tracks([
					(p0, B_Cu),
					(p1, B_Cu),
					(p2, B_Cu),
					(p3, B_Cu),
				])

	def connect_rows(self):
		# Connect rows
		for i in range(4):
			t = []
			sw_ref = 'SW'+str(i)+'5'
			for padname,pad in self.fp_dict['U1']['padF'].items():
				if pad['net'] == 'ROW'+str(i):
					mcu_pad_pos = pad['pos']
					break
			switch_pad_pos = self.fp_dict[sw_ref]['padF']['2']['pos']
			t.append((switch_pad_pos, F_Cu))
			if i > 0: # row1-3
				p1 = switch_pad_pos+VECTOR2I_MM(2.8+i*0.3, -2.8-i*0.3)
				p2 = VECTOR2I_MM(0,0)
				p2.x = p1.x
				p2.y = mcu_pad_pos.y+FromMM(1.5)
				t.append((p1, F_Cu))
				t.append((p2, F_Cu))
			t.append((mcu_pad_pos, F_Cu))
			self.add_tracks(t)

	def connect_leds_by_col(self):
		# Connect LEDs by column
		for sw in self.get_fp('SW_Push'):
			if not self.is_thumb_cluster(sw['ref']): # skip thumb cluster
				sw_col = int(sw['ref'][-1])
				sw_row = int(sw['ref'][-2])
				offset = sw['pos']
				if sw_row != 0: # route from bottom up. ie row1 -> row0, row2 -> row1...
					# power rail - left
					self.add_tracks([
						(offset+VECTOR2I_MM(-3.3, -5.5), F_Cu),
						(offset+VECTOR2I_MM(-3.3, -6.9), F_Cu),
						(offset+VECTOR2I_MM(-1.7, -8.5), F_Cu),
						(offset+VECTOR2I_MM(-1.7,-14.7), F_Cu),
						(offset+VECTOR2I_MM(-4.4,-17.4), F_Cu),
						(offset+VECTOR2I_MM(-4.4,-21.9), F_Cu),
						(offset+VECTOR2I_MM(-3.3,-22.5), F_Cu),
					])
					# led dout -> led din
					if sw_col %2 == 0: # even column
						self.add_tracks([
							(offset+VECTOR2I_MM( 3.3, -5.5), F_Cu),
							(offset+VECTOR2I_MM( 3.3,-10.2), F_Cu),
							(offset+VECTOR2I_MM( 3.3,-10.2), F_Cu),
							(offset+VECTOR2I_MM(-3.3,-16.8), F_Cu),
							(offset+VECTOR2I_MM(-3.3,-20.9), F_Cu),
						])
					else: # odd column
						self.add_tracks([
							(offset+VECTOR2I_MM(-3.3, -3.9), F_Cu),
							(offset+VECTOR2I_MM(-2.1, -4.4), F_Cu),
							(offset+VECTOR2I_MM(-2.1, -6.5), F_Cu),
							(offset+VECTOR2I_MM( 2.1,-10.8), F_Cu),
							(offset+VECTOR2I_MM( 2.1,-21.9), F_Cu),
							(offset+VECTOR2I_MM( 3.3,-22.5), F_Cu),
						])
				
	def connect_led_5v(self):
		for i in range(6):
			led_ref = 'LED0'+str(i) # first row
			t = []
			t.append((self.fp_dict[led_ref]['padB']['4']['pos'], B_Cu))
			t.append((self.fp_dict[led_ref]['padB']['4']['pos']+VECTOR2I_MM(-1.2, -1.2), B_Cu))
			t.append((self.fp_dict[led_ref]['padB']['4']['pos']+VECTOR2I_MM(-1.2, -2.7), B_Cu))
			t.append((self.fp_dict[led_ref]['padB']['4']['pos']+VECTOR2I_MM(10.0, -2.7), B_Cu))
			if i < 5:
				next_led_ref = 'LED0'+str(i+1)
				t.append((self.fp_dict[next_led_ref]['padB']['4']['pos']+VECTOR2I_MM(-1.2, -2.7), B_Cu))
			else:
				t.append((self.fp_dict[led_ref]['padB']['4']['pos']+VECTOR2I_MM(21.6, -2.7), B_Cu))
				t.append((self.fp_dict['R1']['padB']['1']['pos'], B_Cu))
			self.add_tracks(t)
				
			
	def connect_shift_register_and_resistor(self):
		# connect resistor array 3V3 net
		self.add_track(self.fp_dict['R_R5']['padF']['1']['pos'], self.fp_dict['R_R7']['padF']['1']['pos'], F_Cu)
		self.add_track(self.fp_dict['R_L5']['padB']['1']['pos'], self.fp_dict['R_L7']['padB']['1']['pos'], B_Cu)
		# connect resistor array col pad
		for i in range(8):
			rl_pv = self.fp_dict['R_L' + str(i)]['padB']['2']['pos']
			self.add_via(rl_pv + VECTOR2I_MM(1,0), 0.3, 0.4)
			self.add_track(rl_pv, rl_pv + VECTOR2I_MM(1,0), B_Cu)
			self.add_track(rl_pv, rl_pv + VECTOR2I_MM(1,0), F_Cu)
		# connect shift register left and right
		for i in [str(n) for n in range(9,17)]: #pad 9-16
			if (i != '10'): # skip pad 10
				pad_pos = self.fp_dict['SR_RIGHT1']['padF'][i]['pos']
				via_pos = pad_pos +VECTOR2I_MM(-1.9,0)
				self.add_via(via_pos, 0.3, 0.4)
				self.add_track(pad_pos, via_pos, F_Cu)
		for i in [str(n) for n in range(1,9)]: # pad 1-6
			if (i != '7'): # skip pad 7
				pad_pos = self.fp_dict['SR_RIGHT1']['padF'][i]['pos']
				via_pos = pad_pos +VECTOR2I_MM(1.5,0)
				self.add_via(via_pos, 0.3, 0.4)
				self.add_track(pad_pos, via_pos, F_Cu)
				self.add_track(pad_pos, via_pos, B_Cu)
		# R - SR: COL net
		r_pack_track_step = (self.fp_dict['SR_LEFT1']['padB']['15']['pos'] - self.fp_dict['SR_LEFT1']['padB']['14']['pos'])/2
		for i in range(8):
			net_name = 'COL'+str(i)
			for rl in self.get_fp('R_US'):
				if '2' in rl['padB'] and rl['padB']['2']['net'] == net_name:
					p0 = rl['padB']['2']['pos']
					break
			for v in self.fp_dict['SR_LEFT1']['padB'].values(): # shift register pads
				if v['net']	== net_name:
					if v['pos'].x < self.fp_dict['SR_LEFT1']['pos'].x: # left side pads
						p1 = v['pos'] + VECTOR2I_MM(6, 0) + r_pack_track_step
					else: # right side pads
						p1 = v['pos'] + VECTOR2I_MM(1, 0)
					p2 = p1 + VECTOR2I_MM(-2, 0)
					p3 = p2 + VECTOR2I(FromMM(-2.5), -r_pack_track_step.y)
					p4 = VECTOR2I(self.fp_dict['SR_RIGHT1']['padF']['9']['pos'].x - FromMM(1.2), p3.y)
					p5 = VECTOR2I(p4.x - FromMM(0.7), p2.y)
					break
			if i == 7: 
				self.add_tracks([
					(p0, B_Cu),
					(p1, B_Cu),
					(p2, B_Cu),
					(p3, B_Cu),
				])
			else:
				self.add_tracks([
					(p0, B_Cu),
					(p1, B_Cu),
					(p2, B_Cu),
					(p3, B_Cu),
					(p4, B_Cu),
					(p5, B_Cu),
				])
		for i in ['9', '10', '15', '16']:
			p0 = self.fp_dict['SR_LEFT1']['padB'][i]['pos']
			p1 = p0 + VECTOR2I_MM(-1, 0)
			p2 = p1 + VECTOR2I_MM(-2.5, 0) - r_pack_track_step
			p3 = VECTOR2I(self.fp_dict['SR_RIGHT1']['padF'][i]['pos'].x - FromMM(1.2), p2.y)
			if i in ['9', '10']:
				#p4 = VECTOR2I(p3.x - FromMM(0.7), p3.y-r_pack_track_step.y)
				p4 = p3 + VECTOR2I_MM(-0.7, 0) - r_pack_track_step
			else:
				p4 = VECTOR2I(p3.x - FromMM(0.7), p1.y)
			self.add_tracks([
				(p0, B_Cu),
				(p1, B_Cu),
				(p2, B_Cu),
				(p3, B_Cu),
				(p4, B_Cu),
			])
				
	def connect_connector_and_mcu(self):
		# Connect connector and MCU
		#nets_to_connect = ['+5V', '+3V3', 'ROW0', 'ROW1', 'SCS', 'SCK0', 'ROW2', 'ROW3']
		nets_to_connect = ['ROW3', 'ROW2', 'SCK0', 'SCS', 'ROW1', 'ROW0', '+3V3', 'LED_R', '+5V']
		c0 = VECTOR2I_MM(184.6,79)
		for i, net in enumerate(nets_to_connect):
			for padname,pad in self.fp_dict['J_RIGHT1']['padF'].items():
				if pad['net'] == net: # and int(padname) %2 == 1:
					p1 = c0 + VECTOR2I_MM(0.3*i, 0.3*i)
					self.add_tracks([
						(pad['pos']+VECTOR2I_MM(1.6, -1.6), F_Cu),
						(p1, F_Cu),
					])
			if net == 'LED_R': # 1 extra track for LED_R
				self.add_tracks([	
					(p1, F_Cu),
					(p1+VECTOR2I_MM(0,-24.3), F_Cu),
					(p1+VECTOR2I_MM(-2.4,-26.7), F_Cu),
					(self.fp_dict['JP1']['padB']['3']['pos']+VECTOR2I_MM(2.5,0), -1),
					(self.fp_dict['JP1']['padB']['3']['pos'], B_Cu),
				])
			else: 
				for padname,pad in self.fp_dict['U1']['padF'].items():
					if pad['net'] == net:
						p2 = VECTOR2I(0,0)
						p3 = VECTOR2I(0,0)
						if int(padname) > 12: # right cloumn of MCU pin
							p3.x = p1.x
							p3.y = pad['pos'].y + (p1.x-pad['pos'].x) # 45deg
							self.add_tracks([
								(p1, F_Cu),
								(p3, F_Cu),
								(pad['pos'], F_Cu)
							])
						else :
							p3.x = pad['pos'].x + FromMM(16)
							p3.y = pad['pos'].y - FromMM(1.27)# in between two pads
							p2.x = p1.x
							p2.y = p3.y + (p1.x-p3.x) # 45deg
							self.add_tracks([
								(p1, F_Cu),
								(p2, F_Cu),
								(p3, F_Cu),
								(pad['pos'], F_Cu)
							])

	def place_edge_cut(self): 
		# Place edge cuts on the board
		# get highest y coordinate (column 3)
		upper_edge_y = self.fp_dict['SW03']['fp'].GetPosition().y - FromMM(10)
		# get top right corner
		right_edge_x = self.fp_dict['SW36']['fp'].GetPosition().x + FromMM(15)
		# get bottom left corner x coordinate (column 0)
		left_edge_x = self.sw0_pos.x - FromMM(10)
		# get bottom left corner x coordinate (column 0)
		lower_left_y = self.fp_dict['SW30']['fp'].GetPosition().y + FromMM(15)
		# get lower right y coordinate (column 7)
		lower_right_y = self.fp_dict['SW36']['fp'].GetPosition().y + FromMM(15)
		edge_cut_tracks = [
			VECTOR2I(right_edge_x, upper_edge_y ),
			VECTOR2I( left_edge_x, upper_edge_y ),
			VECTOR2I( left_edge_x, lower_left_y ),
			VECTOR2I(right_edge_x, lower_right_y),
			VECTOR2I(right_edge_x, upper_edge_y )
		]
		track = PCB_SHAPE(self.board)
		track.SetShape(SHAPE_T_POLY)
		track.SetFilled(False)
		track.SetLayer(Edge_Cuts)
		track.SetWidth(FromMM(0.1))
		track.SetStart(edge_cut_tracks[0])
		track.SetPolyPoints(edge_cut_tracks)
		self.board.Add(track)
		''' 
		#TODO fillet corner
		chain = SHAPE_POLY_SET()
		chain.NewOutline()
		for point in edge_cut_tracks:
			chain.Append(point)
		#chain.SetClosed(False)
		#chain.SetLayer(Edge_Cuts)
		#chain.SetWidth(FromMM(0.1))
		chain.Fillet(8,1)
		self.board.Add(chain)
		'''

	'''	
	def place_mounting_hole(self): #TODO
		# Place mounting holes on the board
		mounting_hole = MODULE(self.board)
		mounting_hole.SetPosition(VECTOR2I_MM(0, 0))
		mounting_hole.SetOrientation(0)
		mounting_hole.SetFPID(FPID("MountingHole"))
		self.board.Add(mounting_hole)
	'''	
		
	def place_copper_pour(self):
		# Place copper pour on the board
		top_left = VECTOR2I_MM( 30, 30)
		bottom_right = VECTOR2I_MM(210,160)
		points = [
			top_left,
			VECTOR2I(top_left.x, bottom_right.y),
			bottom_right,
			VECTOR2I(bottom_right.x, top_left.y)
		]
		chain = SHAPE_LINE_CHAIN()
		for point in points:
			chain.Append(point)
		chain.SetClosed(True)
		# set pour on both F_Cu and B_Cu
		layers = LSET()
		layers.AddLayer(F_Cu)
		layers.AddLayer(B_Cu)
		zone = ZONE(self.board)
		zone.AddPolygon(chain)  # Add the polygon points
		# pour on GND
		net_code = self.board.GetNetcodeFromNetname('GND') 
		zone.SetNetCode(net_code)
		zone.SetLayerSet(layers)  # Set the layer
		# fill it
		zones = ZONES()
		zones.append(zone)
		filler = ZONE_FILLER(self.board)
		filler.Fill(zones)
		self.board.Add(zone)

	# Do all the things
	def Run(self):
		# Execute the plugin
		self.load_board()
		self.remove_old_tracks()
		self.gen_fp_placement()
		self.place_sw()
		self.place_led()
		self.place_diode()
		self.place_mcu()
		self.place_misc()
		self.place_shift_register_and_resistor()
		self.place_connector()
		self.update_pad_pos()
		self.place_via_for_led()
		self.place_via_for_diode()
		self.place_via_for_connector()
		#self.connect_thumb_cluster()
		self.connect_rows()
		self.connect_pad1()
		self.connect_pad2()
		self.connect_diode_and_sw()
		self.connect_sw_col()
		self.connect_leds_by_col()
		self.connect_led_5v()
		self.connect_shift_register_and_resistor()
		self.connect_connector_and_mcu()
		self.place_edge_cut()
		if (self.is_fast_mode == False): # copper pour is slow
			self.place_copper_pour()
		Refresh()
		#SaveBoard(self.filename, self.board)
		SaveBoard('autogen.kicad_pcb', self.board)
		
	def unit_test(self):
		self.place_copper_pour()
		

#kbd_place_n_route().register()

def main():
	if len(sys.argv) > 1:
		if sys.argv[1] == '-q':
			# run in fast mode, ie no copper pour
			is_fast_mode = True
	else:
		is_fast_mode = False
	plugin = kbd_place_n_route(is_fast_mode)
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