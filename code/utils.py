import pygame
from OpenGL.GL import *
from OpenGL.GLU import *
from functools import reduce
import collections
import numpy as np
from twisted.internet import reactor, defer, task

class Trace(object):
    def __init__(self, color=(38,139,210), length=100):
        self.pos = np.zeros((length,2))
        self.width = np.zeros((length,1))
        self.color = color if reduce(lambda x, y: x and 0<y<1, color) else (color[0]/255,color[1]/255,color[2]/255)

    def update(self, pos, width):
        self.pos = np.roll(self.pos, 1, axis=0)
        self.width = np.roll(self.width, 1, axis=0)
        self.pos[0,:] = pos
        self.width[0] = width

    def draw(self):
        glDisable(GL_TEXTURE_2D)
        glBegin(GL_QUAD_STRIP)
        for i in range(len(self.width)):
            glColor4f(*self.color, 1-i/100)
            if i==0:
                continue
            x_old,y_old, x, y = self.pos[i-1:i+1, :].ravel()
            w = self.width[i]
            dx, dy = x-x_old, y-y_old
            if dx == 0 or dy == 0:
                continue
            c = w*1.0/np.sqrt(dx**2 + dy**2)
            nx, ny = -dy*c, dx*c
            glVertex2f(x_old+nx, y_old+ny)
            glVertex2f(x_old-nx, y_old-ny)
            glVertex2f(x+nx, y+ny)
            glVertex2f(x-nx, y-ny)
        glEnd()

class Symbol(object):
    def __init__(self, texture, pos, slice_rect=((0,0),(1,1)), size=(0.01, 0.01), color = (1,1,1)):
        self.highlighted = False
        self.pos = np.array(pos)
        self.texture = texture
        self.slice_rect = slice_rect
        self.size = np.array(size)
        self.color = np.hstack([color[:3], 0.25])

    def draw(self):
        color = self.color.copy()
        if self.highlighted:
            color[3] = 1.0
        glEnable(GL_TEXTURE_2D)
        glBindTexture(GL_TEXTURE_2D, self.texture)
        glBegin(GL_QUADS)
        glColor4fv(color)
        glTexCoord2f(self.slice_rect[0][0],self.slice_rect[1][1])
        glVertex2fv((self.pos+self.size*np.array([-0.5,-0.5])))
        glTexCoord2fv(self.slice_rect[1])
        glVertex2fv((self.pos+self.size*np.array([ 0.5,-0.5])))
        glTexCoord2f(self.slice_rect[1][0],self.slice_rect[0][1])
        glVertex2fv((self.pos+self.size*np.array([ 0.5,0.5])))
        glTexCoord2fv(self.slice_rect[0])
        glVertex2fv((self.pos+self.size*np.array([-0.5,0.5])))
        glEnd()
        glDisable(GL_TEXTURE_2D)
        glBindTexture(GL_TEXTURE_2D, 0)

class Grid(object):
    def __init__(self, num_rows, num_cols, symbols_img, img_rows=None, img_cols=None, coords=((-1,1), (1,-1)), space=0, point_size=10, point_color=(1.0, 0, 0, 1.0), base_color=(1.0, 1.0, 1.0, 1.0)):
        textureSurface = pygame.image.load(symbols_img)
        textureData = pygame.image.tostring(textureSurface, "RGBA", 0)

        img_rows = img_rows if img_rows else num_rows
        img_cols = img_cols if img_cols else num_cols

        assert img_rows*img_cols == num_rows*num_cols, "Number of symbols in image and grid must match!"

        # Create texture
        # <OPENGL>
        glEnable(GL_TEXTURE_2D)
        self.texid = glGenTextures(1)
        glBindTexture(GL_TEXTURE_2D, self.texid)
        glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, textureSurface.get_width(),textureSurface.get_height(), 0, GL_RGBA, GL_UNSIGNED_BYTE, textureData)
        glTexParameterf(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_REPEAT)
        glTexParameterf(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_REPEAT)
        glTexParameterf(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_NEAREST)
        glTexParameterf(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_NEAREST)
        # </OPENGL>

        size = np.zeros(2)
        size[0] = (coords[1][0] - coords[0][0])*(1-space)/num_cols
        size[1] =-(coords[1][1] - coords[0][1])*(1-space)/num_rows

        pos_xs = np.linspace(coords[0][0]+size[0]/2, coords[1][0]-size[0]/2, num_cols, endpoint=True)
        pos_ys = np.linspace(coords[0][1]+size[1]/2, coords[1][1]-size[1]/2, num_rows, endpoint=True)

        xs = np.linspace(0, 1, img_cols+1, endpoint=True)
        ys = np.linspace(0, 1, img_rows+1, endpoint=True)

        symbols = []
        for i,y in enumerate(ys[:-1]):
            for j,x in enumerate(xs[:-1]):
                symbols.append(Symbol(self.texid, (pos_xs[j], pos_ys[i]), ((x,y),(xs[j+1], ys[i+1])), size, color=base_color))

        self.symbols = np.array(symbols, dtype=object).reshape((num_rows, num_cols))
        self.coords = np.array(coords)
        self.point_size = point_size
        self.point_color = point_color

    def flash(self, rows=None, cols=None):
        if rows is None:
            rows = range(self.symbols.shape[0])
        if cols is None:
            cols = range(self.symbols.shape[1])
        if not isinstance(rows, collections.Iterable):
            rows = (rows,)
        if not isinstance(cols, collections.Iterable):
            cols = (cols,)

        flashed = np.zeros(self.symbols.shape, dtype=bool)
        for i,row in enumerate(self.symbols):
            for j,s in enumerate(row):
                flash = ((i in rows) and (j in cols))
                s.highlighted = flash
                flashed[i,j] = flash
        return flashed

    def draw(self):
        for s in self.symbols.ravel():
            s.draw()

        glPointSize(self.point_size)
        glBegin(GL_POINTS)
        glColor4fv(self.point_color)
        glVertex2fv(self.coords.mean(axis=0))
        glEnd()

def get_mouse_coords(width, height):
    x,y = pygame.mouse.get_pos()
    x/=width/2
    x-=1
    y/=height/2
    y-=1
    y*=-1
    return x,y

def boilerplate():
    """ Sets up an openGL window to use"""
    pygame.init()
    pygame.display.set_mode((0, 0), pygame.NOFRAME|pygame.DOUBLEBUF|pygame.OPENGLBLIT|pygame.OPENGL)
    height,width = pygame.display.Info().current_h, pygame.display.Info().current_w
    glClearColor(0.5, 0.5, 0.5 ,1)
    glEnable(GL_BLEND)
    glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
    glTexEnvi(GL_TEXTURE_ENV, GL_TEXTURE_ENV_MODE, GL_COMBINE);
    glTexEnvi(GL_TEXTURE_ENV, GL_COMBINE_RGB, GL_MODULATE)
    return width, height


def async_sleep(time):
    d = defer.Deferred()
    reactor.callLater(time, d.callback, None)
    return d

def reref_channels(data_in, electrode_id=1):
    """ rereference with respect to electrode `electrode_id` [1, ..., 9]"""
    assert 1 <= electrode_id <= 9, "Electrode ID out of range. [1,...,9]"

    cs = np.cumsum(np.hstack(([[0]],data_in)), 1)
    cs -= cs[0,electrode_id-1]
    cs = -cs
    return cs
