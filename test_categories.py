#!/usr/bin/env python3
"""Test category detection"""
import sys
sys.path.insert(0, '/app')
from ui.gradio_app import _detect_category

print('Testing _detect_category():')
print(f'  Plátanos: {_detect_category("Quiero importar plátanos")}')
print(f'  Vehículos: {_detect_category("Necesito buses")}')
print(f'  Acero: {_detect_category("Láminas de acero")}')
print(f'  Textil: {_detect_category("Tela de algodón")}')
print(f'  Electrónica: {_detect_category("Smartphones")}')
