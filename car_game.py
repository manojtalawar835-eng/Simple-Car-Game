"""
Road Rush - A simple car dodging game built with Pygame.

Controls:
    LEFT / A   -> move car left
    RIGHT / D  -> move car right
    UP / W     -> speed boost
    DOWN / S   -> slow down
    P          -> pause / resume
    R          -> restart after game over
    ESC        -> quit

Goal:
    Dodge the oncoming traffic for as long as possible. Your score increases
    over time and the game gets progressively harder (more traffic, faster
    speeds). Colliding with another car ends the run.

Run:
    pip install pygame
    python car_game.py
"""

import pygame
import random
import sys
import os

# ----------------------------------------------------------------------------
# Configuration
# ----------------------------------------------------------------------------
SCREEN_WIDTH = 500
SCREEN_HEIGHT = 700
FPS = 60

ROAD_WIDTH = 360
ROAD_LEFT = (SCREEN_WIDTH - ROAD_WIDTH) // 2
ROAD_RIGHT = ROAD_LEFT + ROAD_WIDTH

LANE_COUNT = 3
LANE_WIDTH = ROAD_WIDTH // LANE_COUNT

CAR_WIDTH = 46
CAR_HEIGHT = 90

GRASS_COLOR = (34, 139, 34)
ROAD_COLOR = (50, 50, 55)
LANE_LINE_COLOR = (230, 230, 230)
SHOULDER_COLOR = (200, 200, 200)
WHITE = (255, 255, 255)
BLACK = (10, 10, 10)
RED = (220, 40, 40)
YELLOW = (255, 210, 0)
BLUE = (40, 120, 220)
GREEN = (40, 200, 90)
GRAY = (120, 120, 120)

HIGH_SCORE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "highscore.txt")


def load_high_score():
    try:
        with open(HIGH_SCORE_FILE, "r") as f:
            return int(f.read().strip())
    except (FileNotFoundError, ValueError):
        return 0


def save_high_score(score):
    try:
        with open(HIGH_SCORE_FILE, "w") as f:
            f.write(str(score))
    except OSError:
        pass


class PlayerCar:
    """The car controlled by the user."""

    def __init__(self):
        self.width = CAR_WIDTH
        self.height = CAR_HEIGHT
        self.x = SCREEN_WIDTH // 2 - self.width // 2
        self.y = SCREEN_HEIGHT - self.height - 30
        self.speed_x = 6
        self.color = BLUE

    @property
    def rect(self):
        return pygame.Rect(self.x, self.y, self.width, self.height)

    def move(self, keys):
        if keys[pygame.K_LEFT] or keys[pygame.K_a]:
            self.x -= self.speed_x
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            self.x += self.speed_x

        # Keep the car within the road boundaries
        if self.x < ROAD_LEFT + 6:
            self.x = ROAD_LEFT + 6
        if self.x + self.width > ROAD_RIGHT - 6:
            self.x = ROAD_RIGHT - 6 - self.width

    def draw(self, surface):
        draw_car(surface, self.rect, self.color, headlights=True)


class TrafficCar:
    """An obstacle car coming down the road."""

    def __init__(self, y, speed, color=None):
        lane = random.randint(0, LANE_COUNT - 1)
        self.width = CAR_WIDTH
        self.height = CAR_HEIGHT
        self.x = ROAD_LEFT + lane * LANE_WIDTH + (LANE_WIDTH - self.width) // 2
        self.y = y
        self.speed = speed
        self.color = color or random.choice([RED, YELLOW, GREEN, GRAY, (255, 140, 0)])

    @property
    def rect(self):
        return pygame.Rect(self.x, self.y, self.width, self.height)

    def update(self):
        self.y += self.speed

    def draw(self, surface):
        draw_car(surface, self.rect, self.color, headlights=False)


def draw_car(surface, rect, color, headlights=True):
    """Draw a simple stylized car (body, windows, wheels, lights)."""
    x, y, w, h = rect.x, rect.y, rect.width, rect.height

    body_rect = pygame.Rect(x, y, w, h)
    pygame.draw.rect(surface, color, body_rect, border_radius=10)
    pygame.draw.rect(surface, BLACK, body_rect, width=2, border_radius=10)

    # windshield / rear window
    windshield = pygame.Rect(x + 6, y + 10, w - 12, h * 0.28)
    rear_window = pygame.Rect(x + 6, y + h - h * 0.32, w - 12, h * 0.22)
    pygame.draw.rect(surface, (170, 220, 255), windshield, border_radius=4)
    pygame.draw.rect(surface, (170, 220, 255), rear_window, border_radius=4)

    # wheels
    wheel_w, wheel_h = 8, 18
    pygame.draw.rect(surface, BLACK, (x - 3, y + 10, wheel_w, wheel_h), border_radius=3)
    pygame.draw.rect(surface, BLACK, (x + w - wheel_w + 3, y + 10, wheel_w, wheel_h), border_radius=3)
    pygame.draw.rect(surface, BLACK, (x - 3, y + h - wheel_h - 10, wheel_w, wheel_h), border_radius=3)
    pygame.draw.rect(surface, BLACK, (x + w - wheel_w + 3, y + h - wheel_h - 10, wheel_w, wheel_h), border_radius=3)

    # lights
    if headlights:
        pygame.draw.circle(surface, (255, 255, 210), (x + 8, y + 4), 4)
        pygame.draw.circle(surface, (255, 255, 210), (x + w - 8, y + 4), 4)
    else:
        pygame.draw.circle(surface, (255, 60, 60), (x + 8, y + h - 4), 4)
        pygame.draw.circle(surface, (255, 60, 60), (x + w - 8, y + h - 4), 4)


class RoadRushGame:
    def __init__(self):
        pygame.init()
        pygame.display.set_caption("Road Rush - Car Dodging Game")
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        self.clock = pygame.time.Clock()

        self.font_large = pygame.font.SysFont("arial", 48, bold=True)
        self.font_medium = pygame.font.SysFont("arial", 28, bold=True)
        self.font_small = pygame.font.SysFont("arial", 20)

        self.high_score = load_high_score()
        self.reset()

    def reset(self):
        self.player = PlayerCar()
        self.traffic = []
        self.road_scroll = 0
        self.base_scroll_speed = 6
        self.score = 0.0
        self.spawn_timer = 0
        self.spawn_interval = 70  # frames between spawns, decreases over time
        self.game_over = False
        self.paused = False

    # -- spawning & difficulty -------------------------------------------------
    def current_traffic_speed(self):
        # Traffic speed scales up slowly with score
        return self.base_scroll_speed + min(self.score / 15, 8)

    def maybe_spawn_traffic(self):
        self.spawn_timer += 1
        interval = max(28, self.spawn_interval - int(self.score / 8))
        if self.spawn_timer >= interval:
            self.spawn_timer = 0
            new_car = TrafficCar(y=-CAR_HEIGHT, speed=self.current_traffic_speed())
            # Avoid spawning directly overlapping another car in the same lane
            overlap = any(
                abs(new_car.x - c.x) < CAR_WIDTH and c.y < CAR_HEIGHT * 1.5
                for c in self.traffic
            )
            if not overlap:
                self.traffic.append(new_car)

    # -- update ------------------------------------------------------------
    def update(self):
        if self.game_over or self.paused:
            return

        keys = pygame.key.get_pressed()
        self.player.move(keys)

        speed_mult = 1.0
        if keys[pygame.K_UP] or keys[pygame.K_w]:
            speed_mult = 1.6
        elif keys[pygame.K_DOWN] or keys[pygame.K_s]:
            speed_mult = 0.5

        scroll_speed = self.base_scroll_speed * speed_mult
        self.road_scroll = (self.road_scroll + scroll_speed) % 40

        self.maybe_spawn_traffic()

        for car in self.traffic:
            car.speed = self.current_traffic_speed() * (speed_mult if speed_mult > 1 else 1)
            car.update()

        self.traffic = [c for c in self.traffic if c.y < SCREEN_HEIGHT + CAR_HEIGHT]

        # collision detection
        for car in self.traffic:
            if self.player.rect.colliderect(car.rect):
                self.end_game()
                break

        self.score += 0.12 * speed_mult

    def end_game(self):
        self.game_over = True
        if self.score > self.high_score:
            self.high_score = int(self.score)
            save_high_score(self.high_score)

    # -- drawing -------------------------------------------------------------
    def draw_road(self):
        self.screen.fill(GRASS_COLOR)
        pygame.draw.rect(self.screen, ROAD_COLOR, (ROAD_LEFT, 0, ROAD_WIDTH, SCREEN_HEIGHT))

        # road shoulders
        pygame.draw.rect(self.screen, SHOULDER_COLOR, (ROAD_LEFT - 6, 0, 6, SCREEN_HEIGHT))
        pygame.draw.rect(self.screen, SHOULDER_COLOR, (ROAD_RIGHT, 0, 6, SCREEN_HEIGHT))

        # lane markers (dashed, scrolling)
        for lane in range(1, LANE_COUNT):
            x = ROAD_LEFT + lane * LANE_WIDTH
            y = int(self.road_scroll) - 40
            while y < SCREEN_HEIGHT:
                pygame.draw.rect(self.screen, LANE_LINE_COLOR, (x - 3, y, 6, 24))
                y += 40

    def draw_hud(self):
        score_text = self.font_medium.render(f"Score: {int(self.score)}", True, WHITE)
        high_text = self.font_small.render(f"Best: {self.high_score}", True, WHITE)
        self.screen.blit(score_text, (12, 12))
        self.screen.blit(high_text, (12, 46))

        hint = self.font_small.render("P: Pause  |  Arrows/WASD: Drive", True, WHITE)
        self.screen.blit(hint, (12, SCREEN_HEIGHT - 28))

    def draw_center_message(self, lines, color=WHITE):
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 160))
        self.screen.blit(overlay, (0, 0))

        total_height = len(lines) * 50
        start_y = SCREEN_HEIGHT // 2 - total_height // 2
        for i, (text, font) in enumerate(lines):
            rendered = font.render(text, True, color)
            rect = rendered.get_rect(center=(SCREEN_WIDTH // 2, start_y + i * 50))
            self.screen.blit(rendered, rect)

    def draw(self):
        self.draw_road()
        for car in self.traffic:
            car.draw(self.screen)
        self.player.draw(self.screen)
        self.draw_hud()

        if self.paused and not self.game_over:
            self.draw_center_message([
                ("PAUSED", self.font_large),
                ("Press P to resume", self.font_small),
            ])

        if self.game_over:
            self.draw_center_message([
                ("GAME OVER", self.font_large),
                (f"Score: {int(self.score)}", self.font_medium),
                (f"Best: {self.high_score}", self.font_small),
                ("Press R to restart", self.font_small),
            ], color=(255, 90, 90))

        pygame.display.flip()

    # -- main loop -----------------------------------------------------------
    def run(self):
        running = True
        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        running = False
                    elif event.key == pygame.K_p and not self.game_over:
                        self.paused = not self.paused
                    elif event.key == pygame.K_r and self.game_over:
                        self.reset()

            self.update()
            self.draw()
            self.clock.tick(FPS)

        pygame.quit()
        sys.exit()


if __name__ == "__main__":
    RoadRushGame().run()
