"""Basically just a pygame wrapper, to make it easier to change it out later if need be."""

import math
import pygame
import pygame.ftfont


import Game.config.config as config
import Game.config.strings as strings

import Game.program.misc.exceptions as exceptions

# Initialise the pygame modules
pygame.ftfont.init()
pygame.display.init()
pygame.event.set_allowed(None)
pygame.event.set_allowed([pygame.QUIT, pygame.KEYDOWN, pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP, pygame.MOUSEMOTION])
pygame.key.set_repeat(config.KEY_REPEAT_DELAY, config.KEY_REPEAT)


class Surface(pygame.Surface):
    """An extended version of pygame.Surface. It includes several enhancements:
    - Non-subsurfaces can now have a notion of being offset
    - Can clip the region that is blitted, both by the in-built 'viewport' on the source surface, or by the 'dest'
        argument passed when calling the blit command.
    - Can treat another (independent) Surface as a subsurface of this one, via cutouts.

    Detailed description of new features:
    - Can give a non-subsurface a notion of being offset, via 'set_offset'. This will be reflected when calling
        'get_offset', or calling 'get_abs_offset' of a subsurface. Note that by default everything ignores offsets
        (both the usual subsurface offset and this new one): blitting and taking subsurfaces are alaways with respect to
        *this* surface, not its offset. The new functions - cutouts, viewports etc. - work the same way.
    - Can clip the region that is being displayed by setting the attribute 'viewport', which should be a Rect. It may
        be set either by passing a 'viewport' argument during initialisation or by assigning to it afterwards. Then
        blitting from this surface will use this clipped region.
    - If we have two surfaces, then we can make one behave as a subsurface of the other by calling 'cutout' on the
        'parent' surface, with a 'location' argument being a Rect specifying where on the parent surface the 'child'
        surface should be (in the same way as cutouts), and the second argument being the 'child' surface. Unlike true
        subsurfaces, blitting to one won't automatically update the other: 'update_cutouts' should be called on the
        parent surface to have it pick up changes made to the child. A converse hasn't yet been implemented.
    """

    def __init__(self, *args, viewport=None, offset=(0, 0), **kwargs):
        super(Surface, self).__init__(*args, **kwargs)
        self._init(viewport=viewport, is_subsurface=False)
        self.set_offset(offset)

    def _init(self, viewport, is_subsurface):
        """Pulled out as a separate function so that we can call it after subsurfaces have been created, as __init__ is
        not called on a subsurface when creating it."""

        if viewport is None:
            viewport = self.get_rect()
        self.viewport = viewport
        self._cutout_locations = []
        self._cutouts = []
        self._is_subsurface = is_subsurface
        self._is_cutout = False

    def cutout(self, location, target):
        """See description in Surface class docstring."""

        target.set_offset(location.topleft)
        target._is_cutout = True
        self._cutout_locations.append(location)
        self._cutouts.append(target)

    def update_cutouts(self):
        """See description in Surface class docstring."""

        for location, cutout in zip(self._cutout_locations, self._cutouts):
            cutout.update_cutouts()
            self.blit(cutout, location)

    def set_offset(self, offset):
        """Set the offset of a non-subsurface Surface."""

        if self._is_subsurface or self._is_cutout:
            raise exceptions.SdlException(strings.Exceptions.SUBSURFACE_OFFSET)
        else:
            self._offset = offset

    def subsurface(self, *args, viewport=None, **kwargs):
        return_surface = super(Surface, self).subsurface(*args, **kwargs)
        return_surface._init(viewport=viewport, is_subsurface=True)
        return return_surface

    def get_offset(self):
        if not self._is_subsurface:
            return self._offset
        else:
            return super(Surface, self).get_offset()

    def get_abs_offset(self):
        top_level_offset = self.get_abs_parent().get_offset()
        subsurface_offset = super(Surface, self).get_abs_offset()
        return top_level_offset[0] + subsurface_offset[0], top_level_offset[1] + subsurface_offset[1]

    def get_viewport_offset(self):
        return self.viewport.topleft

    def blit(self, source, dest=(0, 0), area=None, *args, **kwargs):  # Added default argument to dest.
        """Enhanced version of blit. If 'dest' is a Rect then the blitting will be clipped to the rectangular area it
        specifies. If 'area' is not passed as an argument then the blitting will be clipped to the viewport of the
        source."""

        # Instance check so that we don't try doing this with the original pygame.Surfaces which some pygame functions
        # still return.
        if isinstance(source, Surface) and area is None:
            area = source.viewport
        else:
            area = source.get_rect()
        # Reference to the original pygame.Rect so that any future extending by us of just Rect, below, won't break this
        if isinstance(dest, pygame.Rect):
            area = Rect(area.left, area.top, min(dest.width, area.width), min(dest.height, area.height))
        return super(Surface, self).blit(source, dest, area, *args, **kwargs)

    def blit_offset(self, source, dest=(0, 0), area=None, *args, **kwargs):
        """Blitting normally interprets the destination as being relative to the top left corner of the Surface. This
        blit takes into account the offset of the surface."""

        offset = self.get_offset()
        if isinstance(dest, pygame.Rect):
            dest = dest.move(-1 * offset[0], -1 * offset[1])
        else:
            dest = dest[0] - offset[0], dest[1] - offset[1]
        return self.blit(source, dest, area, *args, **kwargs)

    def blit_abs_offset(self, source, dest=(0, 0), area=None, *args, **kwargs):
        """Blitting normally interprets the destination as being relative to the top left corner of the Surface. This
        blit takes into account the absolute offset of the surface."""

        offset = self.get_abs_offset()
        if isinstance(dest, pygame.Rect):
            dest = dest.move(-1 * offset[0], -1 * offset[1])
        else:
            dest = dest[0] - offset[0], dest[1] - offset[1]
        return self.blit(source, dest, area, *args, **kwargs)

    def point_within(self, pos, offset=(0, 0)):
        """Whether or not a given point is within the Surface's Rect."""

        rect = self.get_rect(left=offset[0], top=offset[1])
        return rect.collidepoint(pos)

    def point_within_offset(self, pos):
        """Whether or not a given point is within the Surface's Rect, relative to its offset."""

        offset = self.get_offset()
        return self.point_within(pos, offset)

    def point_within_abs_offset(self, pos):
        """Whether or not a given point is within the Surface's Rect, relative to its absolute offset."""

        offset = self.get_abs_offset()
        return self.point_within(pos, offset)


Rect = pygame.Rect
quit = pygame.quit
error = pygame.error

# Event types
NOEVENT = pygame.NOEVENT
QUIT = pygame.QUIT
KEYDOWN = pygame.KEYDOWN
MOUSEBUTTONDOWN = pygame.MOUSEBUTTONDOWN
MOUSEBUTTONUP = pygame.MOUSEBUTTONUP
MOUSEMOTION = pygame.MOUSEMOTION
# And top-level keycodes
K_LSHIFT = pygame.K_LSHIFT
K_RSHIFT = pygame.K_RSHIFT
K_BACKSPACE = pygame.K_BACKSPACE
K_RETURN = pygame.K_RETURN
K_KP_ENTER = pygame.K_KP_ENTER
K_ESCAPE = pygame.K_ESCAPE
K_BACKSLASH = pygame.K_BACKSLASH
K_SLASH = pygame.K_SLASH
K_UP = pygame.K_UP
K_DOWN = pygame.K_DOWN
K_a = pygame.K_a
K_b = pygame.K_b
K_c = pygame.K_c
K_d = pygame.K_d
K_e = pygame.K_e
K_f = pygame.K_f
K_g = pygame.K_g
K_h = pygame.K_h
K_i = pygame.K_i
K_j = pygame.K_j
K_k = pygame.K_k
K_l = pygame.K_l
K_m = pygame.K_m
K_n = pygame.K_n
K_o = pygame.K_o
K_p = pygame.K_p
K_q = pygame.K_q
K_r = pygame.K_r
K_s = pygame.K_s
K_t = pygame.K_t
K_u = pygame.K_u
K_v = pygame.K_v
K_w = pygame.K_w
K_x = pygame.K_x
K_y = pygame.K_y
K_z = pygame.K_z


# Emulate its modules
class display:
    # Note that set_mode will return a pygame.Surface, not the enhanced Surface defined above. It's not possible to
    # reassign its __class__ as Surface is a builtin type.
    set_mode = pygame.display.set_mode
    set_caption = pygame.display.set_caption
    update = pygame.display.update


class draw:
    circle = pygame.draw.circle
    rect = pygame.draw.rect


class event:
    clear = pygame.event.clear
    wait = pygame.event.wait
    poll = pygame.event.poll
    Event = pygame.event.Event

    @classmethod
    def get(cls, num=math.inf, discard_old=False):
        """
        A generator providing a stream of events as inputs. If no events are waiting then it will return a NOEVENT.

        :int num: is the number of events to return.
        :bool discard_old: is whether to discard those events which aren't returned.
        """
        if discard_old:
            if num == math.inf:
                events = pygame.event.get()
            else:
                events = pygame.event.get()[:num]
        else:
            events = []
            for i in range(num):
                event_ = cls.poll()
                if event_.type == NOEVENT:
                    break
                events.append(event_)

        if not events:
            events = [cls.Event(NOEVENT)]

        for event_ in events:
            if event_.type == QUIT:
                raise exceptions.CloseException()
            elif event_.type == KEYDOWN:
                if event_.key in K_SHIFT:
                    continue  # The modified key will be picked up on the next keystroke
                if event_.unicode == '\r':
                    event_.unicode = '\n'
            yield event_

    @staticmethod
    def is_key(event_):
        """Checks whether an event is a KEYDOWN event."""
        return event_.type == KEYDOWN

    @staticmethod
    def is_mouse(event_, valid_buttons=(1, 2, 3)):
        """Checks whether an event is a mouse event.

        Meaning of :valid_buttons: elements:
        1 - Left click
        2 - Middle click
        3 - Right click
        4 - Scroll wheel up
        5 - Scroll wheel down
        6 - Mouse 4
        7 - Mouse 5"""

        if event_.type not in MOUSEEVENTS:
            return False
        if event_.type != MOUSEMOTION and event_.button not in valid_buttons:
            return False
        return True


class ftfont:
    SysFont = pygame.ftfont.SysFont


class image:
    load = pygame.image.load
    tostring = pygame.image.tostring


class time:
    Clock = pygame.time.Clock


class transform:
    rotate = pygame.transform.rotate


class key:
    get_pressed = pygame.key.get_pressed
    name = pygame.key.name

    # I can't believe there is no better way to do this.
    _names_to_code = {
        'a': K_a, 'b': K_b, 'c': K_c, 'd': K_d, 'e': K_e, 'f': K_f, 'g': K_g, 'h': K_h, 'i': K_i, 'j': K_j, 'k': K_k,
        'l': K_l, 'm': K_m, 'n': K_n, 'o': K_o, 'p': K_p, 'q': K_q, 'r': K_r, 's': K_s, 't': K_w, 'u': K_u, 'v': K_v,
        'w': K_w, 'x': K_x, 'y': K_y, 'z': K_z,
    }

    @classmethod
    def code(cls, key_name):
        return cls._names_to_code[key_name]


# Custom stuff
K_SHIFT = (K_LSHIFT, K_RSHIFT)
K_ENTER = (K_KP_ENTER, K_RETURN)
MOUSEEVENTS = (MOUSEBUTTONUP, MOUSEBUTTONDOWN, MOUSEMOTION)
