#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import random
from typing import List, Tuple

# Simple generators returning list of (x,y)

def uniform(n:int, w:float, h:float) -> List[Tuple[float,float]]:
    return [(random.uniform(0,w), random.uniform(0,h)) for _ in range(n)]

def corridor(n:int, w:float, h:float, ratio:float=3.0) -> List[Tuple[float,float]]:
    # stretch along x if w>=h, else along y; enforce effective corridor by reducing variance in minor axis
    if w >= h:
        # reduce y variance
        return [(random.uniform(0,w), random.gauss(h/2, h/(ratio*4))) for _ in range(n)]
    else:
        # reduce x variance
        return [(random.gauss(w/2, w/(ratio*4)), random.uniform(0,h)) for _ in range(n)]

