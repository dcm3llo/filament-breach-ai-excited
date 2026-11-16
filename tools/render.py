"""Original procedural illustration. Build dependency: Pillow; never run in grading.
SPDX-License-Identifier: MIT
"""
from pathlib import Path
import math
import random
from PIL import Image, ImageDraw, ImageFilter, ImageChops

SIZE = 1024
S = 2
RNG = random.Random(84173)
ROOT = Path(__file__).resolve().parents[1]

def curve(start, *segments, steps=60):
    points = [start]
    p = start
    for a, b, c in segments:
        for i in range(1, steps + 1):
            t = i / steps
            u = 1 - t
            points.append(tuple(u**3*p[k]+3*u*u*t*a[k]+3*u*t*t*b[k]+t**3*c[k] for k in (0, 1)))
        p = c
    return points

def coords(points):
    return [(round(x*S), round(y*S)) for x,y in points]

def line(draw, points, color, width: float=1):
    draw.line(coords(points), fill=color, width=max(1, round(width*S)), joint='curve')

def ellipse(draw, box, color, outline=None, width=1):
    draw.ellipse(tuple(round(v*S) for v in box), fill=color, outline=outline, width=round(width*S))

def glow(image, layer, radius=12, strength=1):
    haze = layer.filter(ImageFilter.GaussianBlur(radius*S))
    for _ in range(strength):
        image = ImageChops.screen(image, haze)
    return ImageChops.screen(image, layer)

def gradient():
    small = Image.new('RGB', (SIZE, SIZE))
    px = small.load()
    assert px is not None
    for y in range(SIZE):
        for x in range(SIZE):
            halo = math.exp(-(((x-615)/480)**2+((y-410)/380)**2)*2)
            amber = math.exp(-(((x-260)/230)**2+((y-795)/190)**2)*2)
            px[x,y] = (int(3+7*halo+29*amber), int(8+28*halo+13*amber), int(20+38*halo+5*amber))
    return small.resize((SIZE*S,SIZE*S), Image.Resampling.BICUBIC)

def render():
    image = gradient()
    stars = Image.new('RGB', image.size)
    d = ImageDraw.Draw(stars)
    for _ in range(430):
        x,y = RNG.uniform(30,1000),RNG.uniform(20,910)
        r = RNG.choices([.35,.65,1.1,1.7], [50,35,13,2])[0]
        v = RNG.randint(35,125)
        ellipse(d,(x-r,y-r,x+r,y+r),(v//2,v,v))
    image = glow(image, stars, 3)
    # Long displaced ocean currents: a vortex, not an explosion.
    sea = Image.new('RGB',image.size)
    d = ImageDraw.Draw(sea)
    for i in range(37):
        f=i/36
        pts=curve((140+f*90,826),((490+f*210,770-f*50),(890-f*60,690-f*80),(790-f*190,530-f*50)),((650-f*180,400-f*100),(400-f*120,560-f*140),(530,365)))
        line(d,pts,(12+int(f*30),45+int(f*65),62+int(f*55)),.7+f*.8)
    image=glow(image,sea,13)
    # The emergent filament is a narrow golden ribbon, widening into a living tail.
    tail=curve((238,793),((380,775),(679,816),(696,660)),((712,530),(532,558),(609,421)))
    tail_layer=Image.new('RGB',image.size)
    d=ImageDraw.Draw(tail_layer)
    for width,color in [(28,(7,49,66)),(15,(10,112,132)),(5,(255,166,54)),(1.5,(255,241,170))]:
        line(d,tail,color,width)
    image=glow(image,tail_layer,14,2)
    # A single closed manta silhouette; wing roots join the central body.
    silhouette=curve((727,270),((780,260),(909,172),(972,99)),((942,260),(992,465),(844,713)),((827,574),(749,473),(665,455)),((615,492),(533,489),(477,449)),((288,483),(162,357),(91,139)),((298,151),(406,270),(579,287)),((607,225),(660,217),(692,258)),((705,251),(717,257),(727,270)))
    mask=Image.new('L',image.size)
    md=ImageDraw.Draw(mask)
    md.polygon(coords(silhouette),fill=255)
    skin=Image.new('RGB',(SIZE,SIZE))
    p=skin.load()
    assert p is not None
    for y in range(SIZE):
        for x in range(SIZE):
            light=math.exp(-(((x-620)/270)**2+((y-350)/130)**2))
            gold=math.exp(-(((x-370)/310)**2+((y-230)/160)**2)*2)
            p[x,y]=(int(5+14*light+19*gold),int(27+94*light+11*gold),int(44+101*light))
    skin=skin.resize(image.size,Image.Resampling.BICUBIC)
    image.paste(skin,(0,0),mask)
    # Fine curved ribs make the wings feel like translucent deep-sea sails.
    ribs=Image.new('RGB',image.size)
    d=ImageDraw.Draw(ribs)
    for i in range(28):
        f=i/27
        target=(105+f*400,153+291*f**.65)
        pts=curve((639,342+f*80),((510-f*60,343+f*115),(330-f*90,251+f*210),target))
        line(d,pts,(15+int(60*(1-f)),93+int(42*(1-f)),118),.65)
    for i in range(27):
        f=i/26
        target=(972-128*f,113+590*f)
        pts=curve((675,344+f*68),((772,346+f*38),(850+100*(1-f),255+f*350),target))
        line(d,pts,(18,113-int(f*37),142-int(f*26)),.8)
    ribs=ImageChops.multiply(ribs,Image.merge('RGB',(mask,mask,mask)))
    image=ImageChops.screen(image,ribs)
    # Revision: broad bioluminescent caustics establish mass at thumbnail size.
    # Unlike extra outline detail these illuminate surfaces and pull the gaze
    # from the left wing through the animal's face into the falling right wing.
    caustics=Image.new('RGB',image.size)
    d=ImageDraw.Draw(caustics)
    crest=curve((112,156),((307,178),(413,343),(628,325)),
                ((755,306),(801,407),(852,626)))
    for width,color in [(44,(20,36,32)),(23,(48,48,29)),
                        (9,(106,84,37)),(2,(239,186,91))]:
        line(d,crest,color,width)
    for j in range(7):
        f=j/6
        wave=curve((153+20*j,235+16*j),
                   ((301+16*j,251+21*j),(448,414+8*j),(622,359+13*j)))
        line(d,wave,(11,48+5*j,55+7*j),2.5)
    caustics=ImageChops.multiply(caustics,Image.merge('RGB',(mask,mask,mask)))
    surface_haze=caustics.filter(ImageFilter.GaussianBlur(11*S))
    surface_haze=ImageChops.multiply(surface_haze,Image.merge('RGB',(mask,mask,mask)))
    image=ImageChops.screen(ImageChops.screen(image,surface_haze),caustics)
    # Golden, inward-facing cells along the leading edge imply a living sail.
    cells=Image.new('RGB',image.size)
    d=ImageDraw.Draw(cells)
    left_samples = curve((91,139),((298,151),(406,270),(579,287)),steps=180)
    for i in range(9,160,4):
        x,y=left_samples[i]
        end=(x+12,y+15+13*i/180)
        line(d,[(x,y+6),end],(135+int(i/2),121,53),1.3)
    cells=ImageChops.multiply(cells,Image.merge('RGB',(mask,mask,mask)))
    image=glow(image,cells,5)
    rim=Image.new('RGB',image.size)
    d=ImageDraw.Draw(rim)
    line(d,silhouette,(24,192,205),2.2)
    left_edge=curve((91,139),((298,151),(406,270),(579,287)))
    line(d,left_edge,(255,182,66),4)
    line(d,left_edge,(255,243,188),1.3)
    right_edge=curve((727,270),((780,260),(909,172),(972,99)))
    line(d,right_edge,(255,207,100),3)
    line(d,curve((972,99),((942,260),(992,465),(844,713))),(49,219,232),2)
    image=glow(image,rim,10,2)
    # Body, mouth, paired cephalic lobes and eyes: animal rather than aircraft.
    body=Image.new('RGB',image.size)
    d=ImageDraw.Draw(body)
    keel=curve((650,268),((613,319),(618,388),(666,453)))
    line(d,keel,(38,192,195),3)
    for i in range(5):
        y=351+i*13
        line(d,curve((664,y),((681,y+10),(707,y+7),(722,y-5))),(4,29,42),3)
    for pts in [curve((627,268),((616,238),(628,205),(652,213)),((665,225),(652,237),(650,247))),curve((702,268),((706,239),(736,229),(745,245)),((743,259),(724,265),(722,279)))]:
        line(d,pts,(14,62,74),12)
        line(d,pts,(242,182,82),2)
    line(d,curve((645,282),((669,271),(695,278),(716,288))),(1,12,25),4)
    for x,y in [(619,291),(728,295)]:
        ellipse(d,(x-7,y-4,x+7,y+4),(255,176,48))
        ellipse(d,(x-2,y-3,x+2,y+3),(255,253,224))
    image=glow(image,body,4)
    # Sparse constellations inside the skin, deliberately subordinate to silhouette.
    d=ImageDraw.Draw(image)
    for _ in range(155):
        x,y=RNG.uniform(110,970),RNG.uniform(160,670)
        if mask.getpixel((int(x*S),int(y*S))):
            r=RNG.choice([.5,.7,1.1])
            ellipse(d,(x-r,y-r,x+r,y+r),(116,207,207))
    # Desk horizon and the fallen glass bulb anchor the impossible scale.
    line(d,[(0,921),(1024,921)],(22,44,52),1)
    ellipse(d,(72,876,449,940),(2,6,12))
    glass=Image.new('RGB',image.size)
    d=ImageDraw.Draw(glass)
    outline=curve((144,813),((131,750),(196,715),(254,733)),((338,758),(354,844),(298,884)),((256,916),(188,889),(171,861)))
    line(d,outline,(74,142,154),2)
    line(d,curve((153,798),((146,759),(191,733),(224,739))),(178,219,215),3)
    line(d,curve((306,807),((326,840),(306,865),(279,873))),(35,91,107),2)
    line(d,[(152,827),(221,799),(248,801)],(185,134,70),2)
    line(d,[(162,847),(230,817),(248,801)],(185,134,70),2)
    filament=curve((219,800),((231,787),(240,825),(250,797)),((259,775),(269,805),(279,785)))
    line(d,filament,(255,207,116),3)
    image=glow(image,glass,10,2)
    d=ImageDraw.Draw(image)
    base=[(91,827),(148,806),(176,868),(116,890),(99,875)]
    d.polygon(coords(base),fill=(24,38,47))
    for i in range(6):
        line(d,[(97+i*4,831+i*8),(151+i*4,815+i*8)],(92,113,115),2.5)
    line(d,[(93,847),(86,852),(96,876),(107,876)],(170,130,65),3)
    # A human reaching from the glass rim; readable as a scale witness.
    ellipse(d,(289,736,300,748),(1,9,17))
    line(d,[(294,748),(294,768),(281,784)],(1,9,17),6)
    line(d,[(294,765),(308,780)],(1,9,17),4)
    line(d,[(294,754),(307,748),(313,733)],(1,9,17),4)
    line(d,[(292,754),(283,763)],(1,9,17),4)
    line(d,[(299,749),(308,745),(313,733)],(255,201,112),1)
    # Small ascending embers tie the object, witness and immense creature together.
    sparks=Image.new('RGB',image.size)
    d=ImageDraw.Draw(sparks)
    for _ in range(85):
        t=RNG.random()
        x=267+315*t+RNG.gauss(0,20+30*t)
        y=785-360*t+RNG.gauss(0,15)
        r=RNG.uniform(.5,1.8)
        ellipse(d,(x-r,y-r,x+r,y+r),(255,RNG.randint(135,226),78))
    image=glow(image,sparks,5)
    image=image.resize((SIZE,SIZE),Image.Resampling.LANCZOS)
    out=ROOT/'art'/'entry.png'
    out.parent.mkdir(exist_ok=True)
    image.save(out,optimize=True,compress_level=9)
    print(f'Rendered {out.relative_to(ROOT)}: {out.stat().st_size} bytes')

if __name__=='__main__':
    render()
