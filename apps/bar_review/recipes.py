"""Validated, ordered augmentation recipes for the local curriculum lab."""
from copy import deepcopy
import hashlib
import math
import re

import numpy as np
from PIL import Image


def number(label, default, low, high, step=1):
    return dict(label=label, default=default, min=low, max=high, step=step)


def choice(label, default, values):
    return dict(label=label, default=default, options=values)


SIDES = ['left', 'right', 'top', 'bottom']
EFFECTS = {
    'dirty_drum': dict(label='DirtyDrum', fields=dict(width=number('Stripe width (px)',3,1,20), concentration=number('Line concentration',.1,.01,1,.01), direction=choice('Direction','both',['horizontal','vertical','both','random']), intensity=number('Noise intensity',.5,.05,1,.05))),
    'dirty_rollers': dict(label='DirtyRollers', fields=dict(width=number('Line width (px)',10,2,40), background=choice('Scanline type','white',['white','dark']))),
    'dirty_screen': dict(label='DirtyScreen', fields=dict(clusters=number('Dirt clusters',50,1,200), samples=number('Points per cluster',10,1,40), spread=number('Cluster spread',3,1,15), value=number('Dirt brightness',180,0,254))),
    'lines_degradation': dict(label='LinesDegradation', description='Detects and damages existing lines. Can remove staff lines or notation; inspect label legibility.', fields=dict(probability=number('Replacement probability',.45,0,1,.05), split=number('Split probability',.3,0,1,.05), thickness=number('Replacement thickness (px)',2,1,8), min_length=number('Minimum line length (px)',30,5,200), value=number('Replacement brightness',250,0,255))),
    'low_ink_periodic': dict(label='LowInkPeriodicLines', fields=dict(count=number('Line count',3,1,30), period=number('Period (px)',20,2,100), noise=number('Noise probability',.1,0,1,.05), consistent=choice('Line appearance','consistent',['consistent','varied']))),
    'low_ink_random': dict(label='LowInkRandomLines', fields=dict(count=number('Line count',7,1,50), noise=number('Noise probability',.1,0,1,.05), consistent=choice('Line appearance','consistent',['consistent','varied']))),
    'markup': dict(label='Markup', description='Augraphy places marks on detected content; sparse pages may receive fewer or no marks. Marks are simulated interference, not added score labels.', fields=dict(kind=choice('Mark type','strikethrough',['strikethrough','highlight','underline','crossed']), ink=choice('Ink','pen',['pencil','pen','marker','highlighter']), count=number('Requested lines',3,1,12), length=number('Relative length',.75,.1,1,.05), thickness=number('Thickness (px)',2,1,10), value=number('Monochrome brightness',0,0,220))),
    'subtle_noise': dict(label='SubtleNoise', fields=dict(amount=number('Noise range',10,1,50))),
    'scanner_edge': dict(label='Scanner edge', fields=dict(side=choice('Side', 'right', SIDES), width=number('Width (%)',4.5,0,8,.1))),
    'page_border': dict(label='PageBorder', fields=dict(width=number('Border width (%)',3.5,0,8,.1), height=number('Border height (%)',.8,0,8,.1))),
    'framing': dict(label='Framing / padding', fields={**{s:number(s.title()+' (%)',v,0,8,.1) for s,v in zip(SIDES,[1.5,2.5,1,5.5])}, 'fill':choice('Canvas','white',['white','black'])}),
    'bindings': dict(label='BindingsAndFasteners', fields=dict(kind=choice('Type','punch_holes',['punch_holes','binding_holes','clips','triangle_clips']), side=choice('Edge','left',SIDES), count=number('Count',3,1,8), offset=number('Inset (pixels)',10,0,100))),
    'badphotocopy': dict(label='BadPhotoCopy', fields=dict(strength=number('Copy strength',1,0,3), side=choice('Noise location','none',['none','all',*SIDES]), noise_type=choice('Noise pattern','gaussian',['gaussian','blobs','perlin','worley','rectangular']))),
    'ink': dict(label='InkBleed', fields=dict(strength=number('Ink spread',1,1,3))),
    'rotation': dict(label='Antialiased rotation', fields=dict(angle=number('Angle (degrees)',-1,-3,3,.1))),
    'scan_dpi': dict(label='Scan resolution (DPI)', description='Assume the current canvas spans this physical width (including margins). Downsample to simulate scanner pixels. Higher DPI cannot add detail to the source. Keep scan pixels for realistic dimensions, or restore size to compare detail loss.', fields=dict(
        dpi=number('Target DPI',75,36,600),
        width_mm=number('Canvas width (mm)',210,50,600,.1),
        output=choice('Output size','scan_pixels',['scan_pixels','restore_size']))),
    'black_white': dict(label='Black & white scan', description='Threshold to pure black/white without dithering. Put this after DPI and rotation for a final 1-bit scan; later effects can reintroduce grey. Model resizing can also introduce grey edge pixels.', fields=dict(
        method=choice('Threshold method','fixed',['fixed','otsu','adaptive_gaussian']),
        threshold=number('Threshold (fixed only)',160,0,255),
        radius=number('Local radius px (adaptive only)',15,1,100),
        offset=number('Local offset (adaptive only)',10,-30,30))),
}


def entry(effect_type, identity, **parameters):
    return dict(id=identity, type=effect_type, enabled=True, parameters={**{k:f['default'] for k,f in EFFECTS[effect_type]['fields'].items()}, **parameters})


PRESETS = {
    'clean': [],
    'light-copy': [entry('badphotocopy','copy')],
    'library-scan': [entry('scanner_edge','edge'),entry('page_border','border'),entry('badphotocopy','copy',side='right'),entry('framing','frame'),entry('rotation','rotate')],
    'bound-copy': [entry('page_border','border'),entry('framing','frame'),entry('bindings','bindings'),entry('badphotocopy','copy'),entry('rotation','rotate')],
}


def validate(recipe):
    if not isinstance(recipe,list) or len(recipe)>12:
        raise ValueError('Recipe must be a list of at most 12 effects')
    result, identities = [], set()
    for item in recipe:
        if not isinstance(item,dict) or item.get('type') not in EFFECTS:
            raise ValueError('Unknown recipe effect')
        identity = item.get('id')
        if not isinstance(identity,str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,64}',identity) or identity in identities:
            raise ValueError('Each effect needs a unique ID of letters, numbers, underscores or hyphens')
        identities.add(identity)
        if not isinstance(item.get('enabled',True),bool):
            raise ValueError('Effect enabled must be true or false')
        fields = EFFECTS[item['type']]['fields']
        parameters = item.get('parameters',{})
        if not isinstance(parameters,dict) or set(parameters)-set(fields):
            raise ValueError('Unknown effect parameter')
        normalized = {}
        for key,field in fields.items():
            value = parameters.get(key,field['default'])
            if 'options' in field:
                if value not in field['options']:
                    raise ValueError(f'Invalid {field["label"]}')
            else:
                if isinstance(value,bool) or not isinstance(value,(int,float)) or not math.isfinite(value) or not field['min']<=value<=field['max']:
                    raise ValueError(f'{field["label"]} must be between {field["min"]} and {field["max"]}')
                if field['step']==1 and not float(value).is_integer():
                    raise ValueError(f'{field["label"]} must be an integer')
                value = int(value) if field['step']==1 else float(value)
            normalized[key]=value
        result.append(dict(id=identity,type=item['type'],enabled=item.get('enabled',True),parameters=normalized))
    return result


def apply(image, recipe, seed, rotate):
    from augraphy import BadPhotoCopy, BindingsAndFasteners, Geometric, InkBleed, PageBorder
    from augraphy import DirtyDrum, DirtyRollers, DirtyScreen, LinesDegradation, LowInkPeriodicLines, LowInkRandomLines, Markup, SubtleNoise
    from experiments.scan_degradation.generate import PROFILES, LIBRARY_SCAN, _seeded
    output, records = image.copy(), []
    for position,item in enumerate(validate(recipe)):
        if not item['enabled']:
            continue
        if output.width*output.height > 16_000_000:
            raise ValueError('Recipe canvas is too large; reduce padding or border steps')
        kind, p = item['type'], item['parameters']
        # Stable identity keeps each effect's random stream when reordering it.
        effect_seed = int.from_bytes(hashlib.sha256(f'{seed}:{item["id"]}'.encode()).digest()[:4],'big')
        before = list(output.size)
        if kind=='black_white':
            import cv2
            gray=np.asarray(output.convert('L'))
            if p['method']=='adaptive_gaussian':
                binary=cv2.adaptiveThreshold(gray,255,cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                             cv2.THRESH_BINARY,2*p['radius']+1,p['offset'])
                params=dict(method=p['method'],window_pixels=2*p['radius']+1,offset=p['offset'])
            else:
                flags=cv2.THRESH_BINARY | (cv2.THRESH_OTSU if p['method']=='otsu' else 0)
                threshold,binary=cv2.threshold(gray,p['threshold'] if p['method']=='fixed' else 0,255,flags)
                params=dict(method=p['method'],threshold=threshold)
            params.update(dithering=False,white_rule='luminance > threshold',opencv_version=cv2.__version__)
            output=Image.fromarray(binary).convert('RGB')
            name,backend='BlackWhiteScan','OpenCV'
        elif kind=='scan_dpi':
            input_size=output.size
            requested_width=max(1,round(p['width_mm']/25.4*p['dpi']))
            scan_width=min(output.width,requested_width)
            scan_height=max(1,round(output.height*scan_width/output.width))
            if scan_width < output.width:
                # Pixel-area averaging models integration over a larger scanner
                # pixel; this removes detail, rather than just changing metadata.
                output=output.resize((scan_width,scan_height),Image.Resampling.BOX)
                if p['output']=='restore_size':
                    output=output.resize(input_size,Image.Resampling.BILINEAR)
            params=dict(target_dpi=p['dpi'],assumed_canvas_width_mm=p['width_mm'],
                        input_effective_dpi=input_size[0]*25.4/p['width_mm'],
                        effective_scan_dpi=scan_width*25.4/p['width_mm'],
                        scan_dimensions=[scan_width,scan_height],output=p['output'],
                        downsample='box-area',restore_resampling='bilinear',
                        source_limited=requested_width>input_size[0])
            name,backend='ScanResolution','Pillow'
        elif kind=='rotation':
            params=dict(angle_degrees=p['angle'],supersampling=2,upsample='bicubic',rotation_resampling='bicubic',downsample='lanczos',expand=True,fill='white')
            output=rotate(output,p['angle'])
            name,backend='AntialiasedRotation','Pillow'
        else:
            if kind=='dirty_drum':
                cls,params=DirtyDrum,dict(line_width_range=(p['width'],p['width']),line_concentration=p['concentration'],direction={'horizontal':0,'vertical':1,'both':2,'random':-1}[p['direction']],noise_intensity=p['intensity'],noise_value=(0,30),ksize=(3,3),sigmaX=0,p=1)
            elif kind=='dirty_rollers':
                cls,params=DirtyRollers,dict(line_width_range=(p['width'],p['width']),scanline_type=0 if p['background']=='white' else 1,numba_jit=0,p=1)
            elif kind=='dirty_screen':
                cls,params=DirtyScreen,dict(n_clusters=(p['clusters'],p['clusters']),n_samples=(p['samples'],p['samples']),std_range=(p['spread'],p['spread']),value_range=(p['value'],p['value']+1),p=1)
            elif kind=='lines_degradation':
                cls,params=LinesDegradation,dict(line_roi=(0.,0.,1.,1.),line_gradient_range=(32,255),line_gradient_direction=(0,2),line_split_probability=(p['split'],p['split']),line_replacement_value=(p['value'],p['value']),line_min_length=(p['min_length'],p['min_length']),line_long_to_short_ratio=(5,7),line_replacement_probability=(p['probability'],p['probability']),line_replacement_thickness=(p['thickness'],p['thickness']),p=1)
            elif kind in {'low_ink_periodic','low_ink_random'}:
                cls=LowInkPeriodicLines if kind=='low_ink_periodic' else LowInkRandomLines
                params=dict(count_range=(p['count'],p['count']),use_consistent_lines=p['consistent']=='consistent',noise_probability=p['noise'],p=1)
                if kind=='low_ink_periodic': params['period_range']=(p['period'],p['period'])
            elif kind=='markup':
                cls,params=Markup,dict(num_lines_range=(p['count'],p['count']),markup_length_range=(p['length'],p['length']),markup_thickness_range=(p['thickness'],p['thickness']),markup_type=p['kind'],markup_ink=p['ink'],markup_color=(p['value'],)*3,large_word_mode=True,single_word_mode=False,repetitions=1,p=1)
            elif kind=='subtle_noise':
                cls,params=SubtleNoise,dict(subtle_range=p['amount'],p=1)
            elif kind=='scanner_edge':
                padding=[0.0]*4; padding[SIDES.index(p['side'])]=p['width']/100
                cls,params=Geometric,dict(padding=padding,padding_type='fill',padding_value=(0,0,0),p=1)
            elif kind=='framing':
                fill=255 if p['fill']=='white' else 0
                cls,params=Geometric,dict(padding=[p[s]/100 for s in SIDES],padding_type='fill',padding_value=(fill,)*3,p=1)
            elif kind=='page_border':
                cls,params=PageBorder,deepcopy(LIBRARY_SCAN['page_border'])
                params['page_border_width_height']=(p['width']/100,p['height']/100)
            elif kind=='bindings':
                cls,params=BindingsAndFasteners,dict(effect_type=p['kind'],edge=p['side'],ntimes=(p['count'],p['count']),edge_offset=(p['offset'],p['offset']),overlay_types='darken',foreground=None,use_figshare_library=0,angle_range=(-10,10),nscales=(1.,1.),p=1)
            elif kind=='badphotocopy':
                cls,params=BadPhotoCopy,deepcopy(PROFILES['light-copy'])
                params.update(noise_value=[(245,255),(190,240),(140,210),(80,180)][p['strength']],noise_side=p['side'],noise_type={'blobs':1,'gaussian':2,'perlin':3,'worley':4,'rectangular':5}[p['noise_type']])
            else:
                level=p['strength']
                cls,params=InkBleed,dict(intensity_range=(.1*level,.2*level),kernel_size=(3,3),severity=(.1*level,.15*level),p=1)
            with _seeded(effect_seed):
                effect=cls(**params)
                if kind=='dirty_rollers':
                    # Augraphy decorates this static method at import time;
                    # numba_jit=0 alone does not unwrap an existing dispatcher.
                    # Use its original Python body for seedable, JIT-free work.
                    method=effect.create_scanline_mask
                    effect.create_scanline_mask=getattr(method,'py_func',method)
                result=effect(np.array(output.convert('L')),force=True)
            if result is None:
                raise ValueError(f'{cls.__name__} returned no image')
            output=Image.fromarray(result).convert('RGB')
            name,backend=cls.__name__,'Augraphy'
        if output.width*output.height>16_000_000:
            raise ValueError('Recipe canvas is too large; reduce padding or border steps')
        records.append(dict(id=item['id'],position=position,name=name,backend=backend,parameters=params,seed=effect_seed,
                            execution='python-no-jit' if kind=='dirty_rollers' else 'default',
                            input_dimensions=before,output_dimensions=list(output.size),
                            geometry_changed=kind in {'scanner_edge','framing','page_border'} or (kind=='rotation' and p['angle']!=0) or (kind=='scan_dpi' and before!=list(output.size))))
    return output,records
