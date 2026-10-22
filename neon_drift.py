"""
NEON DRIFT: ULTIMATE EDITION
A polished, high-octane synthwave arcade game.

Dependencies:
    pip install pygame numpy

Controls:
    A / D or Left / Right : Move
    W / Up / Space       : Dash (Invulnerability Burst)
    P / Esc              : Pause
    Enter                : Start / Restart
"""

import math
import random
import sys
import pygame
import numpy as np

# Initialize Pygame & Audio Mixer
pygame.init()
pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)

WIDTH, HEIGHT = 960, 640
FPS = 60
SCREEN = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("NEON DRIFT: ULTIMATE")
CLOCK = pygame.time.Clock()

# Color Palette
BG_TOP = (6, 8, 22)
BG_BOTTOM = (18, 10, 40)
WHITE = (240, 245, 255)
MUTED = (140, 152, 185)
CYAN = (50, 240, 240)
PINK = (255, 65, 160)
PURPLE = (155, 80, 255)
GOLD = (255, 215, 0)
RED = (255, 70, 90)
GREEN = (60, 245, 140)

# Sound Effects Generator using Numpy
def generate_sound(freq_func, duration=0.2, volume=0.3):
    sample_rate = 44100
    n_samples = int(sample_rate * duration)
    t = np.linspace(0, duration, n_samples, False)
    
    freqs = freq_func(t)
    waveform = np.sin(2 * np.pi * freqs * t)
    
    # Envelope (Attack - Decay)
    envelope = np.exp(-3 * t / duration)
    audio = (waveform * envelope * 32767 * volume).astype(np.int16)
    
    # Stereo formatting
    stereo_audio = np.column_stack((audio, audio))
    return pygame.sndarray.make_sound(stereo_audio)

try:
    SND_COIN = generate_sound(lambda t: 523 + t * 2000, 0.12, 0.25)
    SND_DASH = generate_sound(lambda t: 300 - t * 800, 0.25, 0.4)
    SND_HIT = generate_sound(lambda t: 150 - t * 400 + np.random.uniform(-30, 30, len(t)), 0.3, 0.5)
    SND_POWERUP = generate_sound(lambda t: 400 + t * 1500, 0.25, 0.3)
    SOUND_ENABLED = True
except Exception:
    SOUND_ENABLED = False

def play_sound(snd):
    if SOUND_ENABLED:
        snd.play()

# UI Helpers & Font Cache
FONT_CACHE = {}
def font(size, bold=False):
    key = (size, bold)
    if key not in FONT_CACHE:
        FONT_CACHE[key] = pygame.font.SysFont("segoeui", size, bold=bold)
    return FONT_CACHE[key]

def clamp(val, low, high):
    return max(low, min(high, val))

def draw_text(surface, text, size, color, center, bold=False):
    image = font(size, bold).render(text, True, color)
    rect = image.get_rect(center=center)
    surface.blit(image, rect)
    return rect

def rounded_panel(surface, rect, color=(14, 18, 42, 225), border=(70, 86, 145), radius=16, width=1):
    panel = pygame.Surface((rect[2], rect[3]), pygame.SRCALPHA)
    pygame.draw.rect(panel, color, panel.get_rect(), border_radius=radius)
    surface.blit(panel, rect[:2])
    pygame.draw.rect(surface, border, rect, width, border_radius=radius)

def glow_circle(surface, pos, radius, color, strength=60):
    r_max = radius * 2
    glow = pygame.Surface((r_max * 2, r_max * 2), pygame.SRCALPHA)
    center = (r_max, r_max)
    for r in range(r_max, max(1, radius // 2), -4):
        alpha = int(strength * (1 - r / r_max) ** 2)
        pygame.draw.circle(glow, (*color, alpha), center, r)
    surface.blit(glow, (int(pos[0] - r_max), int(pos[1] - r_max)))
    pygame.draw.circle(surface, color, (int(pos[0]), int(pos[1])), max(2, radius // 2))

def make_gradient():
    surf = pygame.Surface((WIDTH, HEIGHT))
    for y in range(HEIGHT):
        t = y / HEIGHT
        c = tuple(int(BG_TOP[i] * (1 - t) + BG_BOTTOM[i] * t) for i in range(3))
        pygame.draw.line(surf, c, (0, y), (WIDTH, y))
    return surf

BACKGROUND = make_gradient()

class Star:
    def __init__(self):
        self.x = random.randrange(WIDTH)
        self.y = random.randrange(HEIGHT)
        self.speed = random.uniform(20, 110)
        self.size = random.choice((1, 1, 2))
        self.phase = random.random() * math.tau

    def update(self, dt, boost=1.0):
        self.y += self.speed * dt * boost
        self.phase += dt * 2
        if self.y > HEIGHT:
            self.y = -5
            self.x = random.randrange(WIDTH)

    def draw(self, surface, boost=1.0):
        length = int(self.size * (3 if boost > 1.5 else 1))
        a = int(100 + 100 * math.sin(self.phase))
        color = (a // 2, a // 2, min(255, a))
        if length > 2:
            pygame.draw.line(surface, color, (int(self.x), int(self.y)), (int(self.x), int(self.y - length)), self.size)
        else:
            pygame.draw.circle(surface, color, (int(self.x), int(self.y)), self.size)

class Particle:
    def __init__(self, x, y, color, velocity=None, life=None, size=None):
        self.x, self.y = x, y
        angle = random.random() * math.tau
        speed = random.uniform(40, 240)
        self.vx, self.vy = velocity if velocity else (math.cos(angle) * speed, math.sin(angle) * speed)
        self.life = self.max_life = life or random.uniform(0.25, 0.6)
        self.size = size or random.uniform(2, 5)
        self.color = color

    def update(self, dt):
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.vx *= 0.98
        self.vy *= 0.98
        self.life -= dt

    def draw(self, surface):
        if self.life <= 0:
            return
        r = max(1, int(self.size * (self.life / self.max_life)))
        alpha = int(240 * (self.life / self.max_life))
        s = pygame.Surface((r * 4, r * 4), pygame.SRCALPHA)
        pygame.draw.circle(s, (*self.color, alpha), (r * 2, r * 2), r)
        surface.blit(s, (int(self.x - r * 2), int(self.y - r * 2)))

class Shockwave:
    def __init__(self, x, y, color):
        self.x, self.y = x, y
        self.radius = 10
        self.max_radius = 90
        self.color = color
        self.life = 1.0

    def update(self, dt):
        self.radius += 280 * dt
        self.life -= 2.2 * dt

    def draw(self, surface):
        if self.life <= 0 or self.radius >= self.max_radius:
            return
        alpha = max(0, int(255 * self.life))
        s = pygame.Surface((self.radius * 2 + 10, self.radius * 2 + 10), pygame.SRCALPHA)
        pygame.draw.circle(s, (*self.color, alpha), (int(self.radius + 5), int(self.radius + 5)), int(self.radius), 3)
        surface.blit(s, (int(self.x - self.radius - 5), int(self.y - self.radius - 5)))

class Player:
    def __init__(self):
        self.x, self.y = WIDTH / 2, HEIGHT - 110
        self.radius = 16
        self.speed = 380
        self.dash_time = 0
        self.dash_cooldown = 0
        self.trail = []

    def update(self, dt, keys, particles, shockwaves):
        direction = int(keys[pygame.K_RIGHT] or keys[pygame.K_d]) - int(keys[pygame.K_LEFT] or keys[pygame.K_a])
        is_dashing = self.dash_time > 0
        speed = self.speed * (2.4 if is_dashing else 1)
        
        self.x = clamp(self.x + direction * speed * dt, 40, WIDTH - 40)
        self.dash_time = max(0, self.dash_time - dt)
        self.dash_cooldown = max(0, self.dash_cooldown - dt)

        self.trail.append((self.x, self.y))
        if len(self.trail) > (14 if is_dashing else 8):
            self.trail.pop(0)

        if random.random() < 0.8:
            particles.append(Particle(
                self.x + random.uniform(-6, 6), self.y + 14,
                GOLD if is_dashing else CYAN,
                velocity=(random.uniform(-40, 40), random.uniform(80, 160)),
                life=random.uniform(0.15, 0.35), size=random.uniform(2, 4)
            ))

    def dash(self, shockwaves):
        if self.dash_cooldown <= 0:
            self.dash_time = 0.25
            self.dash_cooldown = 1.4
            shockwaves.append(Shockwave(self.x, self.y, GOLD))
            play_sound(SND_DASH)
            return True
        return False

    def draw(self, surface):
        for i, (tx, ty) in enumerate(self.trail):
            alpha = int(120 * (i + 1) / max(1, len(self.trail)))
            r = int(3 + 8 * (i + 1) / max(1, len(self.trail)))
            ghost = pygame.Surface((r * 4, r * 4), pygame.SRCALPHA)
            pygame.draw.circle(ghost, (*(GOLD if self.dash_time > 0 else CYAN), alpha), (r * 2, r * 2), r)
            surface.blit(ghost, (int(tx - r * 2), int(ty - r * 2)))

        color = GOLD if self.dash_time > 0 else CYAN
        x, y = int(self.x), int(self.y)
        glow_circle(surface, (x, y), 28, color, 50)

        points = [(x, y - 22), (x - 16, y + 14), (x, y + 8), (x + 16, y + 14)]
        pygame.draw.polygon(surface, (240, 255, 255), points)
        pygame.draw.polygon(surface, color, points, 2)
        pygame.draw.circle(surface, WHITE, (x, y - 2), 4)

class FallingThing:
    def __init__(self, kind, speed):
        self.kind = kind  # coin, orb, slomo, multiplier, hazard, zigzag
        self.x = random.randint(60, WIDTH - 60)
        self.start_x = self.x
        self.y = -35
        self.speed = speed * random.uniform(0.85, 1.15)
        self.phase = random.random() * math.tau
        self.radius = 13 if kind in ("coin", "slomo", "multiplier") else (14 if kind == "orb" else random.randint(15, 21))
        self.spin = random.uniform(-2.5, 2.5)

    def update(self, dt, speed_mod=1.0):
        self.y += self.speed * speed_mod * dt
        self.phase += dt * self.spin
        if self.kind == "zigzag":
            self.x = self.start_x + math.sin(self.y * 0.02) * 60

    def draw(self, surface):
        x, y = int(self.x), int(self.y)
        if self.kind == "coin":
            glow_circle(surface, (x, y), 20, GOLD, 40)
            pygame.draw.circle(surface, GOLD, (x, y), 9, 3)
            pygame.draw.circle(surface, WHITE, (x, y), 3)
        elif self.kind == "orb":
            glow_circle(surface, (x, y), 22, PURPLE, 50)
            pygame.draw.circle(surface, (230, 210, 255), (x, y), 10, 2)
            pygame.draw.circle(surface, PURPLE, (x, y), 4)
        elif self.kind == "slomo":
            glow_circle(surface, (x, y), 20, CYAN, 45)
            pygame.draw.circle(surface, CYAN, (x, y), 10, 2)
            draw_text(surface, "S", 12, WHITE, (x, y), True)
        elif self.kind == "multiplier":
            glow_circle(surface, (x, y), 20, GREEN, 45)
            pygame.draw.circle(surface, GREEN, (x, y), 10, 2)
            draw_text(surface, "2X", 10, WHITE, (x, y), True)
        else:  # hazard / zigzag
            angle = self.phase
            pts = [(x + math.cos(angle + i * math.tau / 6) * self.radius,
                    y + math.sin(angle + i * math.tau / 6) * self.radius) for i in range(6)]
            col = RED if self.kind == "zigzag" else PINK
            glow_circle(surface, (x, y), 24, col, 35)
            pygame.draw.polygon(surface, col, pts)
            pygame.draw.polygon(surface, WHITE, pts, 2)

def circle_collision(x1, y1, r1, x2, y2, r2):
    return (x1 - x2) ** 2 + (y1 - y2) ** 2 < (r1 + r2) ** 2

def draw_background(surface, stars, time, boost):
    surface.blit(BACKGROUND, (0, 0))
    horizon = int(HEIGHT * 0.58)
    
    # Grid lines
    for i in range(14):
        y = horizon + i * i * 2.1 + ((time * 60) % 20)
        if y < HEIGHT:
            pygame.draw.line(surface, (28, 36, 80), (0, y), (WIDTH, y), 1)
    for x in range(-WIDTH, WIDTH * 2, 80):
        pygame.draw.line(surface, (25, 32, 70), (WIDTH // 2 + (x - WIDTH // 2) * 0.15, horizon), (x, HEIGHT), 1)
    pygame.draw.line(surface, (60, 70, 140), (0, horizon), (WIDTH, horizon), 2)

    for star in stars:
        star.update(1/60, boost)
        star.draw(surface, boost)

def draw_hud(surface, score, lives, combo, dash_cooldown, slomo_t, mult_t):
    rounded_panel(surface, (20, 20, 190, 72), (12, 16, 40, 210), (55, 70, 125), 14)
    surface.blit(font(12, True).render("SCORE", True, MUTED), (36, 28))
    surface.blit(font(26, True).render(f"{score:06d}", True, WHITE), (36, 42))

    rounded_panel(surface, (WIDTH - 196, 20, 176, 72), (12, 16, 40, 210), (55, 70, 125), 14)
    surface.blit(font(12, True).render("SHIELDS", True, MUTED), (WIDTH - 176, 28))
    for i in range(3):
        color = PINK if i < lives else (60, 50, 80)
        cx = WIDTH - 168 + i * 28
        pts = [(cx, 48), (cx - 8, 41), (cx - 14, 49), (cx, 63), (cx + 14, 49), (cx + 8, 41)]
        pygame.draw.polygon(surface, color, pts)

    # Dash bar
    bx, by, bw, bh = WIDTH // 2 - 70, 26, 140, 8
    pygame.draw.rect(surface, (35, 42, 75), (bx, by, bw, bh), border_radius=4)
    ready = 1 - clamp(dash_cooldown / 1.4, 0, 1)
    pygame.draw.rect(surface, GOLD if ready >= 1 else PURPLE, (bx, by, int(bw * ready), bh), border_radius=4)
    draw_text(surface, "DASH READY" if ready >= 1 else "CHARGING", 10, GOLD if ready >= 1 else MUTED, (WIDTH // 2, 45), True)

    # Combo & Active Powerup Indicators
    if combo > 1:
        draw_text(surface, f"{combo}x COMBO", 16, GOLD, (WIDTH // 2, 68), True)
    
    p_status = []
    if slomo_t > 0: p_status.append(f"SLO-MO ({slomo_t:.1f}s)")
    if mult_t > 0: p_status.append(f"2X SCORE ({mult_t:.1f}s)")
    if p_status:
        draw_text(surface, " • ".join(p_status), 12, GREEN, (WIDTH // 2, 92), True)

def new_game():
    return {
        "player": Player(), "things": [], "particles": [], "shockwaves": [],
        "score": 0, "lives": 3, "combo": 1, "combo_timer": 0, "spawn_timer": 0.3,
        "time": 0, "shake": 0, "chroma": 0, "invulnerable": 0, "best_chain": 0,
        "slomo_timer": 0, "mult_timer": 0
    }

def main():
    stars = [Star() for _ in range(100)]
    state = "menu"
    game = new_game()
    best_score = 0
    time = 0
    menu_particles = []

    while True:
        dt = min(CLOCK.tick(FPS) / 1000, 0.033)
        time += dt
        keys = pygame.key.get_pressed()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if event.type == pygame.KEYDOWN:
                if state in ("menu", "gameover") and event.key in (pygame.K_RETURN, pygame.K_SPACE):
                    game = new_game()
                    state = "playing"
                elif state == "playing":
                    if event.key in (pygame.K_p, pygame.K_ESCAPE):
                        state = "paused"
                    elif event.key in (pygame.K_SPACE, pygame.K_UP, pygame.K_w):
                        if game["player"].dash(game["shockwaves"]):
                            for _ in range(20):
                                game["particles"].append(Particle(game["player"].x, game["player"].y, GOLD))
                elif state == "paused" and event.key in (pygame.K_p, pygame.K_ESCAPE, pygame.K_RETURN):
                    state = "playing"
                elif state == "gameover" and event.key == pygame.K_ESCAPE:
                    state = "menu"

        if state == "playing":
            g = game
            g["time"] += dt
            g["invulnerable"] = max(0, g["invulnerable"] - dt)
            g["shake"] = max(0, g["shake"] - dt * 20)
            g["chroma"] = max(0, g["chroma"] - dt * 5)
            g["combo_timer"] = max(0, g["combo_timer"] - dt)
            g["slomo_timer"] = max(0, g["slomo_timer"] - dt)
            g["mult_timer"] = max(0, g["mult_timer"] - dt)

            if g["combo_timer"] <= 0:
                g["combo"] = 1

            p = g["player"]
            p.update(dt, keys, g["particles"], g["shockwaves"])

            speed_mod = 0.5 if g["slomo_timer"] > 0 else 1.0
            difficulty = min(2.5, 1 + g["time"] / 50)
            
            g["spawn_timer"] -= dt
            if g["spawn_timer"] <= 0:
                roll = random.random()
                if roll < 0.28: kind = "coin"
                elif roll < 0.34: kind = "orb"
                elif roll < 0.39: kind = "slomo"
                elif roll < 0.44: kind = "multiplier"
                elif roll < 0.65: kind = "zigzag"
                else: kind = "hazard"

                g["things"].append(FallingThing(kind, random.uniform(200, 270) * difficulty))
                g["spawn_timer"] = random.uniform(0.3, 0.65) / difficulty

            for thing in g["things"][:]:
                thing.update(dt, speed_mod)
                if thing.y > HEIGHT + 45:
                    g["things"].remove(thing)
                    continue

                if circle_collision(p.x, p.y, p.radius, thing.x, thing.y, thing.radius):
                    score_mult = 2 if g["mult_timer"] > 0 else 1
                    
                    if thing.kind == "coin":
                        g["score"] += 100 * g["combo"] * score_mult
                        g["combo"] = min(9, g["combo"] + 1)
                        g["combo_timer"] = 2.5
                        g["best_chain"] = max(g["best_chain"], g["combo"])
                        play_sound(SND_COIN)
                        for _ in range(12): g["particles"].append(Particle(thing.x, thing.y, GOLD))
                        g["things"].remove(thing)

                    elif thing.kind == "orb":
                        g["lives"] = min(3, g["lives"] + 1)
                        g["score"] += 200 * score_mult
                        play_sound(SND_POWERUP)
                        for _ in range(18): g["particles"].append(Particle(thing.x, thing.y, PURPLE))
                        g["things"].remove(thing)

                    elif thing.kind == "slomo":
                        g["slomo_timer"] = 4.0
                        play_sound(SND_POWERUP)
                        for _ in range(18): g["particles"].append(Particle(thing.x, thing.y, CYAN))
                        g["things"].remove(thing)

                    elif thing.kind == "multiplier":
                        g["mult_timer"] = 5.0
                        play_sound(SND_POWERUP)
                        for _ in range(18): g["particles"].append(Particle(thing.x, thing.y, GREEN))
                        g["things"].remove(thing)

                    elif g["invulnerable"] <= 0 and p.dash_time <= 0:
                        g["lives"] -= 1
                        g["invulnerable"] = 1.2
                        g["shake"] = 0.4
                        g["chroma"] = 1.0
                        g["combo"] = 1
                        play_sound(SND_HIT)
                        for _ in range(25): g["particles"].append(Particle(thing.x, thing.y, PINK))
                        g["things"].remove(thing)
                        
                        if g["lives"] <= 0:
                            state = "gameover"
                            best_score = max(best_score, g["score"])

            g["score"] += int(10 * dt * (2 if g["mult_timer"] > 0 else 1))

            for item in g["particles"][:] + g["shockwaves"][:]:
                item.update(dt)
                if item.life <= 0:
                    if item in g["particles"]: g["particles"].remove(item)
                    if item in g["shockwaves"]: g["shockwaves"].remove(item)

        else:
            if random.random() < 0.4:
                menu_particles.append(Particle(random.randrange(WIDTH), HEIGHT + 4, random.choice((CYAN, PURPLE, PINK)),
                                                velocity=(random.uniform(-15, 15), random.uniform(-90, -30)),
                                                life=random.uniform(2, 4), size=random.uniform(1, 3)))
            for particle in menu_particles[:]:
                particle.update(dt)
                if particle.life <= 0: menu_particles.remove(particle)

        # RENDER STAGE
        boost = 2.2 if (state == "playing" and game["player"].dash_time > 0) else 1.0
        draw_background(SCREEN, stars, time, boost)

        for particle in menu_particles: particle.draw(SCREEN)

        if state in ("playing", "paused", "gameover") and game["time"] > 0:
            for thing in game["things"]: thing.draw(SCREEN)
            for shockwave in game["shockwaves"]: shockwave.draw(SCREEN)
            for particle in game["particles"]: particle.draw(SCREEN)

            if game["invulnerable"] <= 0 or int(time * 16) % 2 == 0:
                game["player"].draw(SCREEN)

            draw_hud(SCREEN, game["score"], game["lives"], game["combo"],
                     game["player"].dash_cooldown, game["slomo_timer"], game["mult_timer"])

        # MENU OVERLAYS
        if state == "menu":
            draw_text(SCREEN, "NEON", 26, CYAN, (WIDTH // 2, 160), True)
            draw_text(SCREEN, "DRIFT", 80, WHITE, (WIDTH // 2, 220), True)
            pygame.draw.line(SCREEN, PURPLE, (WIDTH // 2 - 100, 270), (WIDTH // 2 + 100, 270), 2)
            draw_text(SCREEN, "SURVIVE THE GRID • DRIFT THROUGH DANGER", 16, MUTED, (WIDTH // 2, 305), True)

            rounded_panel(SCREEN, (WIDTH // 2 - 210, 345, 420, 120), (12, 16, 40, 225), (60, 75, 135), 18)
            draw_text(SCREEN, "←  →  or  A  D   MOVE", 15, CYAN, (WIDTH // 2, 372), True)
            draw_text(SCREEN, "SPACE / W / UP   DASH (INVULNERABLE)", 14, GOLD, (WIDTH // 2, 400), True)
            draw_text(SCREEN, "COLLECT SLOW-MO (S) & 2X MULTIPLIERS", 13, GREEN, (WIDTH // 2, 428), True)

            pulse = 0.75 + 0.25 * math.sin(time * 4)
            draw_text(SCREEN, "PRESS ENTER TO START", 20,
                      (int(WHITE[0] * pulse), int(WHITE[1] * pulse), int(WHITE[2] * pulse)),
                      (WIDTH // 2, 515), True)

        elif state == "paused":
            overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            overlay.fill((4, 6, 18, 175))
            SCREEN.blit(overlay, (0, 0))
            rounded_panel(SCREEN, (WIDTH // 2 - 180, HEIGHT // 2 - 80, 360, 160), (14, 18, 45, 245), (70, 88, 150), 20)
            draw_text(SCREEN, "PAUSED", 36, WHITE, (WIDTH // 2, HEIGHT // 2 - 30), True)
            draw_text(SCREEN, "Press P or ENTER to resume", 15, MUTED, (WIDTH // 2, HEIGHT // 2 + 25))

        elif state == "gameover":
            overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            overlay.fill((6, 4, 18, 190))
            SCREEN.blit(overlay, (0, 0))
            rounded_panel(SCREEN, (WIDTH // 2 - 220, 150, 440, 340), (14, 16, 42, 245), (95, 60, 120), 22)
            draw_text(SCREEN, "SIGNAL LOST", 36, PINK, (WIDTH // 2, 200), True)
            draw_text(SCREEN, "FINAL SCORE", 14, MUTED, (WIDTH // 2, 255), True)
            draw_text(SCREEN, f"{game['score']:06d}", 50, WHITE, (WIDTH // 2, 305), True)
            draw_text(SCREEN, f"Best Combo: {game['best_chain']}x  |  High Score: {best_score:06d}", 15, GOLD, (WIDTH // 2, 355))
            draw_text(SCREEN, "Press ENTER to try again", 17, CYAN, (WIDTH // 2, 415), True)
            draw_text(SCREEN, "ESC for main menu", 13, MUTED, (WIDTH // 2, 448))

        # Chromatic Aberration Effect on Hit
        if state == "playing" and game["chroma"] > 0:
            off = int(game["chroma"] * 6)
            r_surf = SCREEN.copy()
            b_surf = SCREEN.copy()
            r_surf.scroll(off, 0)
            b_surf.scroll(-off, 0)
            SCREEN.blit(r_surf, (0, 0), special_flags=pygame.BLEND_RGB_ADD)

        # Screen Shake
        if state == "playing" and game["shake"] > 0:
            dx, dy = random.randint(-5, 5), random.randint(-4, 4)
            frame = SCREEN.copy()
            SCREEN.fill(BG_TOP)
            SCREEN.blit(frame, (dx, dy))

        pygame.display.flip()

if __name__ == "__main__":
    main()