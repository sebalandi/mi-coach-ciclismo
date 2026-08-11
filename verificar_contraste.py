# verificar_contraste.py
"""
Comprueba que todos los pares de color texto/fondo de la interfaz tengan
contraste suficiente para leerse bien.

Existe porque ya pasó una vez: la pestaña activa quedó con fondo azul oscuro y
letra oscura encima, ilegible. Ese tipo de error es invisible leyendo el código
- hay que calcular la relación de luminancia entre los dos colores.

Correr con:  python verificar_contraste.py
La referencia (4.5:1 para texto normal) es la de las pautas WCAG.
"""

import re
css = re.search(r'<style>(.*?)</style>', open('app.py').read(), re.S).group(1)
variables = dict(re.findall(r'--([\w-]+)\s*:\s*(#[0-9A-Fa-f]{6})', css))

def a_rgb(v):
    v = (v or '').strip()
    m = re.match(r'var\(--([\w-]+)\)', v)
    if m: v = variables.get(m.group(1), '')
    m = re.match(r'#([0-9A-Fa-f]{6})', v)
    if not m: return None
    h = m.group(1)
    return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))

def lum(rgb):
    def ch(c):
        c /= 255
        return c/12.92 if c <= 0.03928 else ((c+0.055)/1.055)**2.4
    r, g, b = [ch(x) for x in rgb]
    return 0.2126*r + 0.7152*g + 0.0722*b

def contraste(fg, bg):
    l1, l2 = sorted([lum(fg), lum(bg)], reverse=True)
    return (l1+0.05)/(l2+0.05)

pares = [
    ('Boton principal', '#FFFFFF', 'var(--accent)'),
    ('Boton principal hover', '#FFFFFF', '#223C63'),
    ('Pestana activa', 'var(--accent)', 'var(--surface)'),
    ('Pestana inactiva', 'var(--ink-faint)', 'var(--surface)'),
    ('Titulo de seccion', 'var(--accent)', 'var(--paper)'),
    ('Texto principal', 'var(--ink)', 'var(--paper)'),
    ('Texto secundario', 'var(--ink-soft)', 'var(--paper)'),
    ('Texto tenue', 'var(--ink-faint)', 'var(--surface)'),
    ('Aviso amarillo', '#6B5518', '#FFF8E8'),
    ('Sesion: tipo', 'var(--ink)', 'var(--surface)'),
    ('Sesion: datos', 'var(--ink-soft)', 'var(--surface)'),
    ('Desplegable destacado', 'var(--accent)', '#F3F7FC'),
]
print(f"{'elemento':24} {'contraste':>10}   estado")
print('-' * 60)
problemas = 0
for nombre, fg, bg in pares:
    a, b = a_rgb(fg), a_rgb(bg)
    if not a or not b:
        print(f'{nombre:24} {"?":>10}   no resuelto'); continue
    r = contraste(a, b)
    if r >= 4.5: estado = 'OK'
    elif r >= 3.0: estado = 'justo (solo texto grande)'
    else: estado = 'INSUFICIENTE'; problemas += 1
    print(f'{nombre:24} {r:9.2f}:1   {estado}')
print()
print('Minimo recomendado para texto normal: 4.5:1')
print('Pares insuficientes:', problemas)
