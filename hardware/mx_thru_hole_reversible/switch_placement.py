#!/usr/bin/env python3
import os,sys, pcbnew
from pcbnew import wxPoint, wxPointMM, wxSize, VECTOR2I, VECTOR2I_MM, FromMM, ToMM, F_Cu, B_Cu, LoadBoard, Save

#filename = sys.argv[1]
filename = [file for file in os.listdir('.') if file.endswith('.kicad_pcb')][0]
print(filename)
board = LoadBoard(filename)

def add_track(start, end, layer=F_Cu):
    #board = pcbnew.GetBoard()
    track = pcbnew.PCB_TRACK(board)
    track.SetStart(start)
    track.SetEnd(end)
    #track.SetWidth(FromMM(0.5)) # default 0.2mm
    track.SetLayer(layer)
    board.Add(track)
    
def add_via(pos, drill, width):
    #board = pcbnew.GetBoard()
    via = pcbnew.PCB_VIA(board)
    via.SetPosition(pos)
    via.SetDrill(FromMM(drill)) # defaults 0.4mm, 0.8mm
    via.SetWidth(FromMM(width))
    board.Add(via)

# Do all the things
# place switches and leds
sw_list = [fp.GetReference() for fp in board.GetFootprints() if fp.GetValue() == 'SW_Push']
col_offsets = [0, 0, -9, -11.5, -9, -6.5]
sw0_x = 60
sw0_y = 60
sw_x_spc = 17.5 #19.05
sw_y_spc = 17 #19.05
for sw_ref in sw_list: 
    sw_ref_row = int(sw_ref[2])
    sw_ref_col = int(sw_ref[3])
    if(sw_ref_col < 6): # 4 fingers
        sw_ref_x = sw0_x+sw_x_spc*sw_ref_col
        sw_ref_y = sw0_y+sw_y_spc*sw_ref_row + col_offsets[sw_ref_col]
    # thumb, respective to index bottom switch
    elif (sw_ref_col == 6): 
        sw_ref_x = sw0_x+sw_x_spc*5+2.9
        sw_ref_y = sw0_y+sw_y_spc*3+14.8 #21.3-6.5
    else: # 7 
        sw_ref_x = sw0_x+sw_x_spc*5+23.8
        sw_ref_y = sw0_y+sw_y_spc*3+19.8 #26.3-6.5
    # place switches
    sw_pos = pcbnew.VECTOR2I_MM(sw_ref_x, sw_ref_y)
    sw_fp = board.FindFootprintByReference(sw_ref)
    sw_fp.SetPosition(sw_pos)
    if(sw_ref_col == 6):
        sw_fp.SetOrientationDegrees(-23)
    elif(sw_ref_col == 7):
        sw_fp.SetOrientationDegrees(60)
    # place LEDs
    led_ref_x = sw_ref_x
    led_ref_y = sw_ref_y + 5.3
    led_pos = VECTOR2I_MM(led_ref_x, led_ref_y)
    led_ref = 'LED'+sw_ref[2:]
    led_fp = board.FindFootprintByReference(led_ref)
    led_fp.SetPosition(led_pos) 
    if(sw_ref_col < 6): 
        if(sw_ref_row % 2 == 0): # row0/row2
            led_fp.SetOrientationDegrees(180)
    elif(sw_ref_col == 6):
        led_fp.SetOrientationDegrees(-23)
    else: # 7
        led_fp.SetOrientationDegrees(60)
        
    if(sw_ref_col < 6):
        # connect col / row pins of each switch
        sw_pos = sw_fp.GetPosition()
        pad1_offset_x = 2.54 * 1000000
        pad1_offset_y = 5.08 * 1000000
        pad2_offset_x = 3.81 * 1000000
        pad2_offset_y = 2.54 * 1000000
        sw_pad1l_pos = pcbnew.VECTOR2I(int(sw_pos.x - pad1_offset_x), int(sw_pos.y-pad1_offset_y))
        sw_pad1r_pos = pcbnew.VECTOR2I(int(sw_pos.x + pad1_offset_x), int(sw_pos.y-pad1_offset_y))
        sw_pad2l_pos = pcbnew.VECTOR2I(int(sw_pos.x - pad2_offset_x), int(sw_pos.y-pad2_offset_y))
        sw_pad2r_pos = pcbnew.VECTOR2I(int(sw_pos.x + pad2_offset_x), int(sw_pos.y-pad2_offset_y))
        add_track(sw_pad1l_pos, sw_pad1r_pos, pcbnew.B_Cu)
        add_track(sw_pad2l_pos, sw_pad2r_pos, pcbnew.B_Cu)
        #connect led pads using via
        #via_offset_y = 5.3
        via_offset_x = [-3.4, -2.4, 2.4, 3.4] #57.1-/+.5; #62.9-/+.5
        for i in range(4): 
            via_pos = pcbnew.VECTOR2I(int(sw_pos.x - via_offset_x[i]*1000000), int(sw_pos.y+5.3*1000000))
            #self.add_via(via_pos, 0.2, 0.35)
            add_via(via_pos, 0.3, 0.4)
            led1_pos = pcbnew.VECTOR2I(int(sw_pos.x - via_offset_x[i]*1000000), int(sw_pos.y+4.51*1000000))
            led2_pos = pcbnew.VECTOR2I(int(sw_pos.x - via_offset_x[i]*1000000), int(sw_pos.y+6.09*1000000))
            if (i%2 == 0):
                add_track(led1_pos, via_pos, pcbnew.F_Cu)
                add_track(led2_pos, via_pos, pcbnew.B_Cu)
            else:
                add_track(led1_pos, via_pos, pcbnew.B_Cu)
                add_track(led2_pos, via_pos, pcbnew.F_Cu)

# place diode
diode_list = [fp.GetReference() for fp in board.GetFootprints() if fp.GetValue() == 'BAV70']
for d_ref in diode_list:
    # get left switch position
    sw_ref_l = 'SW'+d_ref[1:3]
    sw_fp_l = board.FindFootprintByReference(sw_ref_l)
    sw_pos_l_x = sw_fp_l.GetPosition().x
    sw_pos_l_y = sw_fp_l.GetPosition().y
    # get right switch position
    sw_ref_r = 'SW'+d_ref[3:5]
    sw_fp_r = board.FindFootprintByReference(sw_ref_r)
    sw_pos_r_x = sw_fp_r.GetPosition().x
    sw_pos_r_y = sw_fp_r.GetPosition().y
    # place diode in between switches
    d_pos_x = (sw_pos_l_x + sw_pos_r_x)/2
    d_pos_y = (sw_pos_l_y + sw_pos_r_y)/2 - 1500000 # -1.5mm
    d_pos = pcbnew.VECTOR2I(int(d_pos_x), int(d_pos_y))
    d_fp = board.FindFootprintByReference(d_ref)
    d_fp.SetPosition(d_pos)
    d_fp.SetLayerAndFlip(pcbnew.B_Cu)
    d_fp.SetOrientationDegrees(270)
    
    # draw tracks
    pad2_offset_x = 3.81 * 1000000
    pad2_offset_y = 2.54 * 1000000
    sw_l_pad2_pos = pcbnew.VECTOR2I(int(sw_pos_l_x + pad2_offset_x), int(sw_pos_l_y - pad2_offset_y))
    sw_r_pad2_pos = pcbnew.VECTOR2I(int(sw_pos_r_x - pad2_offset_x), int(sw_pos_r_y - pad2_offset_y))
    d_pad1_pos = d_fp.FindPadByNumber("1").GetPosition()
    d_pad2_pos = d_fp.FindPadByNumber("2").GetPosition()
    add_track(sw_l_pad2_pos, d_pad1_pos, pcbnew.B_Cu)
    add_track(sw_r_pad2_pos, d_pad2_pos, pcbnew.B_Cu)

Refresh()
