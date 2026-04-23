# -*- coding: utf-8 -*-
import os
import sys

sys.path.append(os.path.join(os.path.abspath(
    os.path.join(os.path.dirname(__file__))), 'external_libs/etotpverify_linux64'))

from . import models
from . import wizard
