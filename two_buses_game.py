#verson 0 (perfect  ) but has life and ais route change issue 


import pygame
import random
import sys
from dataclasses import dataclass

# -----------------------------
# CONFIG
# -----------------------------
SCREEN_W, SCREEN_H = 900, 700
FPS = 60

ROAD_W = 520
LANES = 3
LANE_W = ROAD_W // LANES
ROAD_X = (SCREEN_W - ROAD_W) // 2

# units
KMH_TO_MPS = 1000.0 / 3600.0

# bus size
BUS_W = int(LANE_W * 0.8)
BUS_H = 60

# spawn rates
OBSTACLE_SPAWN_INTERVAL = 2.0
PEDESTRIAN_SPAWN_INTERVAL = 3.0

# race distance
FINISH_DIST = 2000.0  # meters


@dataclass
class RectObj:
    x: float
    y: float
    w: int
    h: int

    def rect(self):
        return pygame.Rect(int(self.x), int(self.y), self.w, self.h)


class Bus:
    def __init__(self, lane_idx, color, name="Bus", is_player=True):
        self.x = ROAD_X + lane_idx * LANE_W + (LANE_W - BUS_W) / 2
        self.y = SCREEN_H - 180
        self.w = BUS_W
        self.h = BUS_H
        self.color = color
        self.max_speed = 120.0  # km/h
        self.speed = 0.0
        self.accel = 40.0
        self.brake_power = 100.0
        self.lat_speed = 8.0   # left or right movement
        self.progress_m = 0.0
        self.name = name
        self.is_player = is_player
        # scoring & lives
        self.lives = 3
        self.score = 0
        self.dead = False
        self.time_alive = 0.0

    def update(self, dt, controls=None):
        if self.dead:
            return

        # Survival timer → +10 points per second
        self.time_alive += dt
        if self.time_alive >= 1.0:
            self.score += 10
            self.time_alive = 0

        # Acceleration and braking
        if controls:
            if controls.get("accel", False):
                self.speed += self.accel * dt
            elif controls.get("brake", False):
                self.speed -= self.brake_power * dt
            else:
                self.speed -= 5.0 * dt
        else:
            self.speed -= 3.0 * dt # accelerate slowly if no controls (AI)

        if self.speed < 0:
            self.speed = 0  # no reverse
        if self.speed > self.max_speed:
            self.speed = self.max_speed

        # Steering (left/right)
        if controls:
            if controls.get("left", False):
                self.x -= self.lat_speed
            if controls.get("right", False):
                self.x += self.lat_speed

        # Forward/backward small adjustments to avoid collision
        if controls:
            if controls.get("forward_adjust", False):
                self.y -= 2
            if controls.get("backward_adjust", False):
                self.y += 2

        # Road boundaries
        left_bound = ROAD_X + 6  # margin from edge of road
        right_bound = ROAD_X + ROAD_W - self.w - 6   # margin from edge of road
        if self.x < left_bound:
            self.x = left_bound
        if self.x > right_bound:
            self.x = right_bound

        # Keep buses on screen vertically
        if self.y < 100:
            self.y = 100
        if self.y > SCREEN_H - 100:
            self.y = SCREEN_H - 100     #👉 Basically: the bus always stays between a top margin of 100px and a bottom margin of 100px.

        # Distance progress
        v_mps = self.speed * KMH_TO_MPS
        self.progress_m += v_mps * dt    # keeps track of how far it has driven.

        if self.lives <= 0:                # if out of lives, dead
            self.dead = True
            self.speed = 0

    def crash(self):
        """Reduce life and score when crashing"""
        if not self.dead:
            self.lives -= 1
            self.score -= 5
            if self.score < 0:  # no negatives
                self.score = 0
            if self.lives <= 0:
                self.dead = True
                self.speed = 0

    def lane_index(self):
        return int((self.x - ROAD_X) // LANE_W)   #(self.x - ROAD_X) // LANE_W → Divides the distance from the road’s left edge by lane width → tells which lane number.

    def draw(self, surf):                  # draws the bus.
        rect = pygame.Rect(int(self.x), int(self.y), self.w, self.h)  # crt rectangle for the bus
        color = (100, 100, 100) if self.dead else self.color  # gray if dead
        pygame.draw.rect(surf, color, rect, border_radius=6)  # bus er design
        pygame.draw.rect(surf, (220, 240, 255), # bus er window 
                         (rect.x + 8, rect.y + 8, rect.w - 16, int(rect.h / 2)),
                         border_radius=3)
        font = pygame.font.SysFont(None, 18)   # bus er name
        lbl = font.render(self.name, True, (255, 255, 255))  # white text name of the   bus 
        surf.blit(lbl, (rect.centerx - lbl.get_width() / 2, rect.y - 18))

    def rect(self):#Returns the bus’s rectangle object so collisions can be detected easily.
        return pygame.Rect(int(self.x), int(self.y), self.w, self.h)


class Obstacle:
    def __init__(self, lane_idx, y=-100):
        self.x = ROAD_X + lane_idx * LANE_W + (LANE_W - 40) / 2
        self.y = y
        self.w = 40  # width of obstacle
        self.h = 40  # height of obstacle

    def update(self, scroll_speed, dt):
        self.y += scroll_speed * dt

    def draw(self, surf):
        r = pygame.Rect(int(self.x), int(self.y), self.w, self.h)
        pygame.draw.rect(surf, (120, 80, 20), r)


class Pedestrian:
    def __init__(self, lane_idx, y=-60):
        self.x = ROAD_X + lane_idx * LANE_W + LANE_W * 0.2  # start position for pedestrian
        self.y = y
        self.w = 16  # pedestrian size
        self.h = 28
        self.vx = random.choice([-1.0, 1.0])  # left or right 
        self.vy = 1.0  # downward speed

    def update(self, dt, scroll_speed):
        self.x += self.vx * dt * 50
        self.y += (self.vy * dt * 50) + scroll_speed * dt

    def draw(self, surf):  # Creates a rectangle for obstacle position/size.
        r = pygame.Rect(int(self.x), int(self.y), self.w, self.h)  # Draws a brown rectangle to represent the obstacle.
        pygame.draw.rect(surf, (0, 200, 0), r)
        


class SimpleBusAI:
    def __init__(self, bus: Bus):
        self.bus = bus
        self.target_speed = 100.0  # target speed that bus tries to reach

    def decide(self, world, other_bus):
        if self.bus.dead:
            return {}

        controls = {"left": False, "right": False, "accel": False, "brake": False,  # at first all false
                    "forward_adjust": False, "backward_adjust": False}

        # maintain speed
        if self.bus.speed < self.target_speed: 
            controls["accel"] = True

        current_lane = self.bus.lane_index()
        danger_ahead = None

        # look ahead 500m
        for obj in world["obstacles"] + world["pedestrians"]:
            olane = int((obj.x - ROAD_X) // LANE_W)   # which lane the object is in
            if olane == current_lane:                 # if in same lane
                dy = self.bus.y - obj.y              # vertical distance to object
                if 0 < dy < 500:                     # if object is ahead and within 500m
                    danger_ahead = obj               # mark as danger
                    break

        if danger_ahead:                           # if there is a danger ahead
            left_lane = current_lane - 1            # check left lane

            right_lane = current_lane + 1            # check right lane

            if left_lane >= 0 and self.lane_free(left_lane, world, other_bus): # if left lane is free
                controls["left"] = True
            elif right_lane < LANES and self.lane_free(right_lane, world, other_bus): # if right lane is free
                controls["right"] = True
            else:
                # try forward/backward maneuver to avoid collision
                if other_bus and not other_bus.dead:
                    if abs(self.bus.y - other_bus.y) < 80:
                        controls["forward_adjust"] = True
                    else:
                        controls["backward_adjust"] = True
                else:
                    controls["brake"] = True
                    controls["accel"] = False

        return controls

    def lane_free(self, lane, world, other_bus):
        if other_bus and not other_bus.dead and other_bus.lane_index() == lane:
            if abs(self.bus.y - other_bus.y) < 150: # if other bus is close in that lane in between 150px
                return False
        for obj in world["obstacles"] + world["pedestrians"]: # check all obstacles and pedestrians
            olane = int((obj.x - ROAD_X) // LANE_W)          # which lane the object is in
            if olane == lane and abs(self.bus.y - obj.y) < 150:
                return False
        return True


class Game:
    def __init__(self):
        pygame.init()
        pygame.display.set_caption("Race: Human vs AI Bus")
        self.screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont(None, 24)
        self.bigfont = pygame.font.SysFont(None, 64)
        self.running = True
        self.show_start = True
        self.reset()

    def reset(self): # jokhon reset hobe game tokhon sob kichu abar 1st theke start hobe
        self.game_time = 0.0  # track total game time

        self.buses = [
            Bus(lane_idx=0, color=(30, 144, 255), name="Human"),
            Bus(lane_idx=2, color=(200, 60, 60), name="AI", is_player=False),
        ]
        self.ai_agent = SimpleBusAI(self.buses[1])
        self.obstacles, self.peds = [], []              # lists to hold obstacles and pedestrians at first empty
        self.time, self.last_obs, self.last_ped = 0, 0, 0 
        self.winner = None

    def spawn_obstacle(self): # obstacle ke put korlam at a random lane 
        lane = random.randrange(0, LANES)
        self.obstacles.append(Obstacle(lane_idx=lane, y=-80))

    def spawn_pedestrian(self): # pedestrian ke put korlam at a random lane
        lane = random.randrange(0, LANES)
        self.peds.append(Pedestrian(lane_idx=lane, y=-40))

    def draw_road(self):
        pygame.draw.rect(self.screen, (50, 50, 50), (ROAD_X, 0, ROAD_W, SCREEN_H))
        for i in range(1, LANES):
            lx = ROAD_X + i * LANE_W
            for y in range(0, SCREEN_H, 40):
                pygame.draw.rect(self.screen, (230, 230, 230), (lx - 2, y + 10, 4, 20))  #  Result: draws the entire road background.

    def update(self, dt):
        self.time += dt # track timer for spawning of obstacles and pedestrians
        self.game_time += dt  # track timer for game duration

        if self.time - self.last_obs > OBSTACLE_SPAWN_INTERVAL: # spawn(put) obstacle every few seconds
            self.spawn_obstacle()
            self.last_obs = self.time
        if self.time - self.last_ped > PEDESTRIAN_SPAWN_INTERVAL: # spawn(put) pedestrian every few seconds
            self.spawn_pedestrian()
            self.last_ped = self.time

        # Player controls
        pressed = pygame.key.get_pressed()
        controls_p = {
            "left": pressed[pygame.K_LEFT],
            "right": pressed[pygame.K_RIGHT],
            "accel": pressed[pygame.K_UP],
            "brake": pressed[pygame.K_DOWN],
            "forward_adjust": pressed[pygame.K_w],
            "backward_adjust": pressed[pygame.K_s]
        }
        self.buses[0].update(dt, controls_p) # player bus update

        # AI controls
        ai_controls = self.ai_agent.decide({"obstacles": self.obstacles, "pedestrians": self.peds}, self.buses[0])
        self.buses[1].update(dt, ai_controls) # ai bus update

        # Road scroll aita hoy based on average speed of alive buses
        alive_buses = [b for b in self.buses if not b.dead]
        avg_speed = sum([b.speed for b in alive_buses]) / len(alive_buses) if alive_buses else 0
        scroll_speed = avg_speed * KMH_TO_MPS * 50 * dt

        for o in self.obstacles: # update obstacles and pedestrians position based on scroll speed
            o.update(scroll_speed, 1)
        for p in self.peds:
            p.update(dt, scroll_speed)

        # Collision check of buses with obstacles and pedestrians
        for b in self.buses:
            if b.dead:
                continue
            for o in self.obstacles:
                if b.rect().colliderect(pygame.Rect(o.x, o.y, o.w, o.h)):
                    b.crash()
            for p in self.peds:
                if b.rect().colliderect(pygame.Rect(p.x, p.y, p.w, p.h)):
                    b.crash()

        # Winner check
        for b in self.buses:
            if b.progress_m >= FINISH_DIST and not self.winner:
                self.winner = b.name
        if not self.winner:
            alive = [b for b in self.buses if not b.dead]
            if len(alive) == 1:
                self.winner = alive[0].name
            elif len(alive) == 0:
                self.winner = "Nobody"

    def draw(self):
        self.screen.fill((60, 160, 60)) # green background ja diye road er baire er jayga fill korlam
        self.draw_road()
        for o in self.obstacles:
            o.draw(self.screen) # draw obstacles
        for p in self.peds:
            p.draw(self.screen) # draw pedestrians
        for b in self.buses:
            b.draw(self.screen) # draw buses

        # HUD (head-up display) 
        for i, b in enumerate(self.buses):
            remaining = max(0, FINISH_DIST - b.progress_m)
            txt = f"{b.name}: Dist Left {int(remaining)}m | Speed {int(b.speed)} km/h | Score {b.score} | Lives {b.lives}"
            lbl = self.font.render(txt, True, (255, 255, 255))
            self.screen.blit(lbl, (20, 20 + i * 25))

        # Game Timer (top-right)
        time_lbl = self.font.render(f"Time: {int(self.game_time)}s", True, (255, 255, 0))
        self.screen.blit(time_lbl, (SCREEN_W - 150, 20))

        if self.winner:
            msg = self.bigfont.render(f"{self.winner} Wins!", True, (255, 220, 40))
            self.screen.blit(msg, (SCREEN_W // 2 - msg.get_width() // 2, SCREEN_H // 2)) # winner message ja horizontally +vertically dekhay

        pygame.display.flip()

    def start_screen(self):
        self.screen.fill((20, 20, 40))
        msg = self.bigfont.render("Race: Human vs AI Bus", True, (255, 220, 40))
        start = self.font.render("Press ENTER to Start", True, (255, 255, 255))
        self.screen.blit(msg, (SCREEN_W // 2 - msg.get_width() // 2, SCREEN_H // 3))
        self.screen.blit(start, (SCREEN_W // 2 - start.get_width() // 2, SCREEN_H // 2))
        pygame.display.flip()

        waiting = True
        while waiting:
            for e in pygame.event.get():
                if e.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
                if e.type == pygame.KEYDOWN:
                    if e.key == pygame.K_RETURN:
                        waiting = False

    def run(self):
        self.start_screen()
        while self.running:
            dt = self.clock.tick(FPS) / 1000.0
            for e in pygame.event.get():
                if e.type == pygame.QUIT: # to quit the game
                    self.running = False
                if e.type == pygame.KEYDOWN: # keydown events
                    if e.key in [pygame.K_ESCAPE, pygame.K_q]: #escape or q to quit the game
                        self.running = False
                    if e.key == pygame.K_r: # r key to reset the game
                        self.reset()
            if not self.winner: # if no winner yet, update and draw the game
                self.update(dt)
            self.draw()
        pygame.quit()
        sys.exit()


if __name__ == "__main__":
    Game().run()






