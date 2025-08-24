# playkit.py

import pygame
import sys

__all__ = [
    'start', 'sprite', 'when_key', 'when_click', 'when_update',
    'on_game_update', 'draw_circle', 'write',
    'on_game_start', 'game_over', 'control_arrows', 'projectile_from',
    'when_overlap', 'platform', 'enable_gravity', 'set_background'
]

# ——— Game-over / restart system ———
_game_start_handlers  = []
_game_over_flag       = False
_game_over_msg        = ""

def on_game_start(fn):
    """Run this function whenever the game (re)starts."""
    _game_start_handlers.append(fn)

def game_over(message):
    """Pause game, display message, wait for SPACE to restart."""
    global _game_over_flag, _game_over_msg
    _game_over_flag = True
    _game_over_msg  = message

# ——— Overlap events ———
_overlap_handlers = []
def when_overlap(a, b, fn):
    """Call fn(a,b) whenever two sprites overlap."""
    _overlap_handlers.append((a, b, fn))

# ——— Platforms & Gravity ———
_platforms = []
def platform(x, y, width, height, color=(100,100,100)):
    """Create a solid platform. Sprites with gravity land on it."""
    plat = sprite(None, x, y, width, height, color=color)
    _platforms.append(plat)
    return plat

def enable_gravity(sprite, gravity=800):
    """Enable gravity (px/s²) on a sprite."""
    sprite.gravity = gravity
    sprite.on_ground = False

# ——— Internal state ———
_screen               = None
_clock                = None
_sprites              = []
_key_handlers         = {}
_click_handlers       = {}
_update_handlers      = []
_game_update_handlers = []
_draw_commands        = []
_text_commands        = []
_image_cache          = {}

# Background state
_background_path   = None
_background_color  = (0, 0, 0)
_background_mode   = 'stretch'   # 'stretch' or 'tile'
_background_surface = None

def _prepare_background(width, height):
    """Load/scale background surface after window exists."""
    global _background_surface
    _background_surface = None
    if _background_path:
        try:
            img = pygame.image.load(_background_path).convert()
            if _background_mode == 'stretch':
                _background_surface = pygame.transform.smoothscale(img, (width, height))
            else:
                # 'tile' mode uses the original image size; keep as-is
                _background_surface = img
        except Exception:
            print(f'Oops! Can’t find "{_background_path}" for background. Using solid color instead.')
            _background_surface = None

def set_background(image_path=None, color=(0,0,0), mode='stretch'):
    """
    Set a background image or color.
      - image_path: path to an image (PNG/JPG). If None, uses color fill.
      - color: RGB tuple used if image is None or fails to load.
      - mode: 'stretch' (scale to window) or 'tile' (repeat the image).
    You can call this before or after start(); it will adapt automatically.
    """
    global _background_path, _background_color, _background_mode
    _background_path = image_path
    _background_color = color
    _background_mode  = mode
    if _screen is not None:
        # Window exists: try loading immediately with current size
        w, h = _screen.get_size()
        _prepare_background(w, h)

# ——— Sprite classes ———
class Sprite:
    def __init__(self, image, rect, color):
        self.image = image
        self.rect  = rect
        self.color = color

class GameSprite(Sprite):
    def __init__(self, image, rect, color, speed=(0,0), lifetime=None):
        super().__init__(image, rect, color)
        self.speed    = pygame.Vector2(speed)
        self.lifetime = lifetime
        self._age     = 0.0
        self._follow  = None
        self.bounce   = False
        self.alive    = True

    def set_speed(self, dx, dy):
        self.speed = pygame.Vector2(dx, dy)

    def velocity(self, dx, dy):
        """MakeCode-style velocity setter (px/sec)."""
        self.set_speed(dx, dy)

    def follow(self, target, speed):
        """Move toward target at given speed (px/sec)."""
        self._follow = (target, speed)

    def set_bounce(self, enable=True):
        """Bounce off window edges if enabled."""
        self.bounce = enable

    def destroy(self):
        self.alive = False

# ——— Public API ———
def sprite(image_path=None, x=100, y=100, width=50, height=50,
           color=(0,0,255), speed=(0,0), lifetime=None):
    """
    Create a sprite. If image_path is provided and loads, uses it (scaled);
    otherwise uses a colored rectangle. Friendly fallback on errors.
    """
    image = None
    if image_path:
        try:
            image = _image_cache.get((image_path, width, height))
            if not image:
                raw = pygame.image.load(image_path).convert_alpha()
                image = pygame.transform.smoothscale(raw, (width, height))
                _image_cache[(image_path, width, height)] = image
        except Exception:
            print(f'Oops! Can’t find "{image_path}". Here’s a rectangle instead.')
            image = None
    rect = pygame.Rect(x, y, width, height)
    spr  = GameSprite(image, rect, color, speed=speed, lifetime=lifetime)
    _sprites.append(spr)
    return spr

def when_key(key_name, fn):
    """Call fn() every frame while key is held."""
    code = pygame.key.key_code(key_name)
    _key_handlers.setdefault(code, []).append(fn)

def when_click(sprite_obj, fn):
    """Call fn() when the sprite is clicked."""
    _click_handlers.setdefault(sprite_obj, []).append(fn)

def when_update(fn):
    """Call fn() once per frame (after physics, before drawing)."""
    _update_handlers.append(fn)

def on_game_update(fn):
    """Call fn(dt) once per frame (before physics)."""
    _game_update_handlers.append(fn)

def draw_circle(x, y, radius):
    _draw_commands.append(('circle', x, y, radius))

def write(text, x, y, size=24):
    _text_commands.append((text, x, y, size))

def control_arrows(sprite, speed=200, bounds=None):
    """
    Arrow-key movement at `speed` px/sec. Optional bounds=(x0,y0,x1,y1).
    """
    sprite.control_speed = speed
    def handler(dt):
        spd = sprite.control_speed
        pressed = pygame.key.get_pressed()
        dx = dy = 0.0
        if pressed[pygame.K_LEFT]:  dx -= spd * dt
        if pressed[pygame.K_RIGHT]: dx += spd * dt
        if pressed[pygame.K_UP]:    dy -= spd * dt
        if pressed[pygame.K_DOWN]:  dy += spd * dt
        sprite.rect.x += dx
        sprite.rect.y += dy
        if bounds:
            x0,y0,x1,y1 = bounds
            sprite.rect.x = max(x0, min(sprite.rect.x, x1 - sprite.rect.width))
            sprite.rect.y = max(y0, min(sprite.rect.y, y1 - sprite.rect.height))
    on_game_update(handler)

def projectile_from(sprite_obj, vx, vy,
                    image_path=None, width=8, height=8,
                    color=(255,255,0), lifetime=2):
    """Spawn a projectile at sprite center moving at (vx,vy)."""
    x = sprite_obj.rect.centerx - width//2
    y = sprite_obj.rect.centery  - height//2
    return sprite(
        image_path, x, y, width, height,
        color=color, speed=(vx, vy), lifetime=lifetime
    )

# ——— Main loop ———
def start(width, height, title):
    global _screen, _clock, _sprites, _game_over_flag

    pygame.init()
    _screen = pygame.display.set_mode((width, height))
    pygame.display.set_caption(title)
    _clock  = pygame.time.Clock()
    font_cache = {}

    # Prepare background now that display exists
    _prepare_background(width, height)

    # Run setup handlers
    for fn in _game_start_handlers:
        fn()

    running = True
    while running:
        dt = _clock.tick(60) / 1000.0

        # — Events —
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            elif event.type == pygame.KEYDOWN:
                if _game_over_flag and event.key == pygame.K_SPACE:
                    # reset state (keep handlers)
                    _sprites.clear()
                    _draw_commands.clear()
                    _text_commands.clear()
                    _game_over_flag = False
                    for fn in _game_start_handlers:
                        fn()
                    break

            elif event.type == pygame.MOUSEBUTTONDOWN and not _game_over_flag:
                pos = event.pos
                for spr, fns in _click_handlers.items():
                    if spr.rect.collidepoint(pos):
                        for fn in fns:
                            fn()

        # Game-over screen
        if _game_over_flag:
            # draw background behind overlay
            if _background_surface:
                if _background_mode == 'stretch':
                    _screen.blit(_background_surface, (0,0))
                else:  # tile
                    iw, ih = _background_surface.get_size()
                    for yy in range(0, height, ih):
                        for xx in range(0, width, iw):
                            _screen.blit(_background_surface, (xx, yy))
            else:
                _screen.fill(_background_color)

            font1 = pygame.font.Font(None, 64)
            txt1 = font1.render(_game_over_msg, True, (255,50,50))
            _screen.blit(txt1, ((width-txt1.get_width())//2, height//2-80))
            font2 = pygame.font.Font(None, 32)
            txt2 = font2.render("Press SPACE to Restart", True, (200,200,200))
            _screen.blit(txt2, ((width-txt2.get_width())//2, height//2+10))
            pygame.display.flip()
            continue

        # Continuous key handlers
        pressed = pygame.key.get_pressed()
        for code, fns in _key_handlers.items():
            if pressed[code]:
                for fn in fns:
                    fn()

        # on_game_update hooks
        for fn in _game_update_handlers:
            fn(dt)

        # Physics: follow, gravity, movement, bounce, platforms, lifetime
        for spr in list(_sprites):
            if not isinstance(spr, GameSprite):
                continue
            if not spr.alive:
                _sprites.remove(spr)
                continue

            # follow
            if spr._follow:
                targ, spd = spr._follow
                dirv = (pygame.Vector2(targ.rect.center)
                        - pygame.Vector2(spr.rect.center))
                if dirv.length() > 0:
                    vel = dirv.normalize() * spd * dt
                    spr.rect.x += vel.x
                    spr.rect.y += vel.y

            # gravity
            if hasattr(spr, 'gravity'):
                spr.speed.y += spr.gravity * dt

            # movement
            spr.rect.x += spr.speed.x * dt
            spr.rect.y += spr.speed.y * dt

            # edge bounce
            if spr.bounce:
                if spr.rect.left < 0 or spr.rect.right > width:
                    spr.speed.x *= -1
                    spr.rect.x = max(0, min(spr.rect.x, width - spr.rect.width))
                if spr.rect.top < 0 or spr.rect.bottom > height:
                    spr.speed.y *= -1
                    spr.rect.y = max(0, min(spr.rect.y, height - spr.rect.height))

            # platforms (land from above)
            if hasattr(spr, 'gravity') and spr.speed.y >= 0:
                spr.on_ground = False
                for plat in _platforms:
                    if spr.rect.colliderect(plat.rect):
                        spr.rect.bottom = plat.rect.top
                        spr.speed.y = 0
                        spr.on_ground = True
                        break

            # lifetime
            if spr.lifetime is not None:
                spr._age += dt
                if spr._age >= spr.lifetime:
                    spr.destroy()

        # overlap events
        for a, b, fn in _overlap_handlers:
            if a.alive and b.alive and a.rect.colliderect(b.rect):
                fn(a, b)

        # when_update hooks
        for fn in _update_handlers:
            fn()

        # — Drawing —
        # Background first
        if _background_surface:
            if _background_mode == 'stretch':
                _screen.blit(_background_surface, (0,0))
            else:  # tile
                iw, ih = _background_surface.get_size()
                for yy in range(0, height, ih):
                    for xx in range(0, width, iw):
                        _screen.blit(_background_surface, (xx, yy))
        else:
            _screen.fill(_background_color)

        # Sprites
        for spr in _sprites:
            if spr.image:
                _screen.blit(spr.image, spr.rect)
            else:
                pygame.draw.rect(_screen, spr.color, spr.rect)

        # Circles
        for _, x, y, r in _draw_commands:
            pygame.draw.circle(_screen, (255,255,255), (x, y), r)

        # Text
        for text, x, y, size in _text_commands:
            f = font_cache.get(size) or pygame.font.Font(None, size)
            font_cache[size] = f
            surf = f.render(text, True, (255,255,255))
            _screen.blit(surf, (x, y))

        pygame.display.flip()
        _draw_commands.clear()
        _text_commands.clear()

    pygame.quit()
    sys.exit()

