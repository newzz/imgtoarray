import cv2
import collections
import numpy as np
import numpy.linalg as npla

# image to c/sv/hex array conversion using cv2 and numpy libraries.
# converts from png/jpg format ONLY

# C-style three dimensional array of an image
def c_array(imgname, varname):
    img =cv2.imread(imgname)
    # join into three-fold brackets.
    imgstr = '{'+','.join(['{'+','.join(
        [ '{'+','.join(
            [str(chan) for chan in col]
            )+'}'
          for col in row])
              +'}' for row in img])+'}'
    return 'unsigned char %s[%s][%s][%s] = %s;'%((varname,)+img.shape+(imgstr,))

# SystemVerilog-style three dimensional array of an image
def sv_array(imgname,varname,outputfolder):
    img =cv2.imread(imgname,flags=-1)
    # join into three-fold brackets. Reformat each value to 8'hXX hex form.
    imgstr = '{'+','.join([','.join(
        [ ','.join(
            ["8'h"+format(chan,'x') for chan in col]
            )
          for col in row])
               for row in img])+'}'
    filename = outputfolder+'var_'+varname+'.txt'
    with open(filename, "w") as f:            
        f.write(varname + ' = ' + imgstr + ';')
    print 'done'

# first prototype sprite converter. Not practical for Quartus II since compile time will be too large
def sv_sprite_array(imgname, width, numframes, varname, outputfolder):
    filename = outputfolder+'var_'+varname+'.txt'
    varwidthname = varname + '_width'
    varheightname = varname + '_height'
    varnumframes = varname + '_numframes'
    varlenname = varname + '_len'    
    with open(filename, "w") as f:
        img = cv2.imread(imgname,flags=-1)
        img_h, img_w, num_channels = img.shape
        f.write('parameter %s = %d;\n'%(varwidthname,width));
        f.write('parameter %s = %d;\n'%(varheightname,img_h));
        f.write('parameter %s = %d;\n'%(varnumframes,numframes));
        f.write('parameter %s = %d;\n'%(varlenname,img_w*img_h-1));        
        for i in xrange(numframes):            
            f.write('logic [0:%s][0:3][7:0] %s%s = {'%(width*img_h-1,varname,i))        
            startX = i * width
            first = True
            for y in xrange(img_h):
                for x in xrange(startX, startX + width):
                    for chan in img[y,x,:]:
                        if first:
                            first = False
                            f.write("8'h"+format(chan,'x'))
                        else:
                            f.write(", 8'h"+format(chan,'x'))                    
            f.write('};\n')        
    print 'done'

# practical ROM implemenation for a single character sprite, using .hex format.
# Quartus II compatible.
def hex_sprite_array(imgname, width, numframes, varname, outputfolder):
    hexname = outputfolder+'var_'+varname+'.hex'
    filename = outputfolder+'var_'+varname+'.txt'
    varwidthname = varname + '_width'
    varheightname = varname + '_height'
    varnumframes = varname + '_numframes'
    varlenname = varname + '_len'    
    with open(hexname, "w") as f:
        img = cv2.imread(imgname,flags=-1)
        print img.shape
        img_h, img_w, num_channels = img.shape
        addr = 0        
        for i in xrange(numframes):                        
            startX = i * width            
            for y in xrange(img_h):
                for x in xrange(startX, startX + width):
                    b,g,r,a = img[y,x]
                    hexsum = (int(r) + int(g) + int(b) + int(a) + 4 + (addr%256) +
                             ((addr/256)%256)) % 256
                    checksum = (256-hexsum)%256
                    f.write(':04%04X00%02X%02X%02X%02X%02X\n'%(addr,r,g,b,a,checksum))
                    addr = addr + 1
        f.write(':00000001FF\n')
    with open(filename,"w") as f:
        f.write('parameter %s = %d;\n'%(varwidthname,width));
        f.write('parameter %s = %d;\n'%(varheightname,img_h));
        f.write('parameter %s = %d;\n'%(varnumframes,numframes));
        f.write('parameter %s = %d;\n'%(varlenname,img_w*img_h-1));  
    print 'done'

# given an BGRA image "img" and color limit "n", outputs
# the tolerance-filtered histogram of the n most occuring color tones
# i.e. reduces to number of colors in an image to n
# return value is a list of tuples in the form if ((b,g,r,a),frequency).
def color_histogram(img,n):
    hist = {}
    for row in img:
        for col in row:            
            b,g,r,a = tuple(col)
            b,g,r = (b>>4)<<4, (g>>4)<<4,(r>>4)<<4
            pix = b,g,r,a
            if a <= 127:
                pix = 0,0,0,0
            if pix in hist.keys():
                hist[pix] = hist[pix] + 1
            else:
                hist[pix] = 1
    # sort the histogram of colors in descending order of frequency
    hOrd = list(reversed(sorted(hist.items(),key=lambda a: a[1])))
    #prepare return value
    res = []
    num_count = 0
    while len(hOrd) > 0 and num_count < n:
        # pop out the color with highest frequency
        cur, curamt = hOrd[0]
        cur = np.array(cur,dtype=int)
        hOrd.remove(hOrd[0])
        close_color = False
        # check if there is any other color that is "close" to current color
        for color in res:
            color = np.array(color,dtype=int)
            # color tolearance. Close colors count as the same color
            if npla.norm(color[:3]-cur[:3]) < 0x20:
                close_color = True
            if close_color:
                break
        # if current color is not close to any of the previously added colors,
        # add it to the result
        if not close_color:
            res.append(cur)
            num_count = num_count + 1
    return res

# extended version of histogram(). After finding reduced colors using the fn above,
# it replaces each pixel of the original image with the closest color in the palette
def reduce_palette(img,n):
    h,w = img.shape[:2]
    tHist = color_histogram(img,n) 
    for i in xrange(h):
        for j in xrange(w):
            b,g,r,a = img[i,j]
            nearestPix = (0,0,0,0)
            if a > 127:
                nearestPix = min(tHist,key=lambda x: npla.norm(x[:3]-img[i,j][:3]))
            img[i,j,:]= np.array(nearestPix)
    return img

# same as above, but the return value replaces BGRA value with a 4-bit palette index
# the second return value are the indexed colors the palette index stored
# in the first return value is an index into the second return value.
# The 32-bit GBRA color can be found using that index and the histogram.
def reduce_palette_indexed(img,n):
    h,w = img.shape[:2]
    tHist = color_histogram(img,n)
    res = np.zeros((h,w));
    for i in xrange(h):
        for j in xrange(w):
            b,g,r,a = img[i,j]
            nearestPalette = 0
            if a > 127:
                nearestPalette = min(range(min(n,len(tHist))),key=lambda k: npla.norm(tHist[k][:3]-img[i,j][:3]))
            res[i,j]= nearestPalette
    return res,tHist
                
# Reduces and partitions every image into frameWidthxframeHeight chunks with 16-color limit.
# writes .hex color file to outputFile.
# outputs .txt (SystemVerilog syntax) array for the palette to histFile
# outputs .txt mask file for the sprites in maskFile.
def hex_sprite_packAll(filenames,frameWidth,frameHeight,outputFile,histFile,maskFile):
    addr = 0
    hists = []
    files_masks = []
    with open(outputFile,'w') as f:        
        for filename in filenames:
            print "processing %s" % filename
            masks = []
            img = cv2.imread(filename,flags=-1)
            img,hist = reduce_palette_indexed(img,16)
            hists.append(hist)
            h,w =  img.shape
            hsteps = h/frameHeight
            wsteps = w/frameWidth
            for i in xrange(hsteps):
                for j in xrange(wsteps):
                    for distY in xrange(frameHeight):
                        mask = 0
                        for distXSteps in xrange(frameWidth/8):
                            adrval = 0
                            for distXOffset in xrange(8):
                                pix = img[i*frameHeight + distY,j*frameWidth+distXSteps*8+ distXOffset]
                                adrval = (adrval << 4) + int(pix)
                                #print hist[int(pix)][3]
                                if int(hist[int(pix)][3])==0:
                                    mask = mask*2
                                else:
                                    mask = mask*2 + 1
                            hexsum = 4 + (addr%256) + ((addr/256)%256) + (adrval%256) + ((adrval/256)%256) +\
                                    ((adrval/(256**2))%256) + ((adrval/(256**3))%256)
                            hexsum = hexsum % 256
                            checksum = (256-hexsum)%256
                            f.write(':04%04X00%08X%02X\n'%(addr,adrval,checksum))
                            addr = addr + 1
                        masks.append(mask)
            files_masks.append(masks)
        f.write(':00000001FF\n')
    with open(histFile,'w') as f:
        addr = 0
        f.write('{')
        first = True
        for hist in hists:
            for b,g,r,a in hist:
                if first:
                    f.write("32'h%02X%02X%02X%02X"%(r,g,b,a))
                    first=False
                else:
                    f.write(",32'h%02X%02X%02X%02X"%(r,g,b,a))
                addr = addr+1
            while addr % 16 !=0:
                f.write(",32'h00000000")
                addr = addr+1
        f.write('};')
    with open(maskFile,'w') as f:
        for masks in files_masks:
            f.write('{')
            first = True
            for m in masks:
                if first:
                    f.write("32'h%08X"%m)
                    first = False
                else:
                    f.write(",32'h%08X"%m)
            f.write('};\n')
    print 'done'
                            
# just for error checking... converts result from reduce_palette_indexed back to the
# original color-limited image.
def cvtback(paletteImg,palette):
    h,w = paletteImg.shape
    res = np.zeros((h,w,4))
    for i in xrange(h):
        for j in xrange(w):
            res[i,j,:] = np.array(palette[int(paletteImg[i,j])])
    return res

"""below are usage examples"""

hex_sprite_packAll([('sprites/%d.png'%i) for i in xrange(8)],32,32,
                   'sprites/pack.hex','sprites/palette.txt'
                   ,'sprites/mask.txt')

#hex_sprite_array('sprites/mainfish_test.png',32,10,'fish_test_x','sprites/')
#img = cv2.imread('sprites/mainfish_test.png',flags=-1)
#img,hist = reduce_palette_indexed(img,16)
#res = cvtback(img,hist)
#cv2.imwrite('sprites/fish_test_reduced_cvt.png',res)
