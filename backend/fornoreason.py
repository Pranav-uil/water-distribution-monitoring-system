





import pygame
import math
import random
import sys
import time
import json
import paho.mqtt.client as mqtt

# ── MQTT Configuration ────────────────────────────────────────────────────────
MQTT_BROKER = "broker.hivemq.com"
MQTT_PORT = 1883
MQTT_TOPIC = "pipenetwork/sensors/pressure"

def on_connect(client, userdata, flags, reason_code, properties=None):  
    if reason_code == 0:
        print(f"✅ Python genuinely connected to HiveMQ Broker on port {MQTT_PORT}!")
    else:
        print(f"❌ Python failed to connect! Code: {reason_code}")

def on_disconnect(client, userdata, disconnect_flags, reason_code, properties=None):
    print(f"⚠️ Python disconnected from broker! Reason: {reason_code}")

client_id = f"pygame_sim_publisher_{random.randint(1000, 9999)}"
mqtt_client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=client_id)
mqtt_client.on_connect = on_connect
mqtt_client.on_disconnect = on_disconnect

try:
    print(f"Attempting to connect to {MQTT_BROKER}:{MQTT_PORT}...")
    mqtt_client.connect(MQTT_BROKER, MQTT_PORT, 60)
    mqtt_client.loop_start()
except Exception as e:
    print(f"Fatal error starting MQTT: {e}")

DIST_FROM_HUB = {
    "A": 4, "B": 3, "C": 4,
    "D": 2, "E": 1, "G": 1,
    "H": 0, "F": 3, "I": 4,
    "J": 4, "K": 2, "L": 1,
    "M": 2, "N": 2, "O": 3,
    "P": 3, "Q": 4
}

def calculate_and_publish_pressure(valve_open, pipe_leaks):
    nodes = list(valve_open.keys())
    total_open  = sum(valve_open.values())
    active_leaks = len(pipe_leaks)  

    base_pressure    = 120.0
    drop_from_open   = total_open   * 2.5
    # drop_from_leaks  = active_leaks * 18.5
    drop_from_leaks  = active_leaks * 60.0

    pressures = {}
    for n in nodes:
        dist_drop = DIST_FROM_HUB.get(n, 0) * 4.0
        noise     = random.uniform(-1.5, 1.5)
        p         = base_pressure - dist_drop - drop_from_open - drop_from_leaks + noise
        if valve_open[n]:
            p -= 10.0
        pressures[n] = max(0.0, round(p, 2))

    payload = {
        "timestamp":    int(time.time()),
        "actual_leaks": active_leaks,
        "pressures":    pressures
    }
    mqtt_client.publish(MQTT_TOPIC, json.dumps(payload), qos=1, retain=True)
    print(f"Published to {MQTT_TOPIC}: Leaks={active_leaks}, Open Valves={total_open}")


# ── Window & physics ──────────────────────────────────────────────────────────
WIDTH, HEIGHT = 1000, 750
FPS           = 60
GRAVITY       = 1100

PIPE_RADIUS   = 7
NODE_HIT_R    = 18
PIPE_HIT_R    = 14
LEAK_FIX_R    = 22
VALVE_RATE    = 2
LEAK_RATE     = 9
MAX_PARTICLES = 2800

# ── Palette ───────────────────────────────────────────────────────────────────
C_BG             = (6,   12,  26)
C_PIPE_DARK      = (20,  50, 112)
C_PIPE_MID       = (45, 105, 200)
C_PIPE_HIGHLIGHT = (110, 180, 255)
C_NODE_OUTER     = (25,  62, 150)
C_NODE_INNER     = (90,  170, 255)
C_NODE_OPEN      = (38,  215, 105)
C_NODE_OPEN_OUT  = (12,   96,  46)
C_FLOW_DOT       = (160, 220, 255)
C_LEAK_RED       = (255,  60,  40)
C_CRACK          = (255, 150,  25)
C_VALVE_BASE     = (55,  195, 255)
C_VALVE_LIGHT    = (175, 235, 255)
C_LEAK_BASE      = (28,  105, 255)
C_LEAK_LIGHT     = (215, 238, 255)
C_FIXED          = (80,  255, 120)
C_PATCH          = (120, 200,  80)

# ── Node label offsets ────────────────────────────────────────────────────────
# Each offset (dx, dy) is chosen so the label does NOT sit on any pipe segment.
# Connections per node (from seg_pairs):
#   A(660,55)  : B↓                          → label: right
#   B(660,140) : A↑  C→  D↓                  → label: left   (only clear side)
#   C(835,140) : B←                           → label: right
#   D(660,232) : B↑  E←  F↘                  → label: right  (no pipe straight right)
#   E(410,232) : D→  H↓                      → label: top-left
#   F(800,325) : D↖  I→  J↓                  → label: top    (no pipe straight up)
#   G(660,458) : H←  K→                      → label: top    (no pipe straight up)
#   H(410,458) : E↑  G→  L←                  → label: bottom (only clear side)
#   I(878,325) : F←                           → label: right
#   J(800,415) : F↑                           → label: right
#   K(748,458) : G←                           → label: top-right
#   L(272,458) : H→  M↖  N↓                  → label: top-right (no pipe top-right)
#   M(188,418) : L↘                           → label: left
#   N(272,555) : L↑  O←  P↓                  → label: right  (no pipe straight right)
#   O(188,555) : N→  Q↙                      → label: top-left
#   P(272,645) : N↑                           → label: right
#   Q(100,690) : O↗                           → label: left

NODE_LABEL_OFFSET = {
    "A": ( 16,  -8),   # right of node; pipe goes downward only
    "B": (-32, -22),   # left;  pipes go up / right / down
    "C": ( 16,  -8),   # right; pipe goes left only
    "D": ( 16, -22),   # top-right; pipes go up / left / lower-right
    "E": (-32, -22),   # top-left;  pipes go right / down
    "F": (  4, -26),   # top-centre; pipes go upper-left / right / down
    "G": (  4, -26),   # top-centre; pipes go left / right
    "H": (-16,  20),   # bottom;     pipes go up / right / left
    "I": ( 16,  -8),   # right; pipe goes left only
    "J": ( 16,   0),   # right; pipe goes up only
    "K": ( 16, -22),   # top-right; pipe goes left only
    "L": ( 16, -26),   # top-right; pipes go right / upper-left / down
    "M": (-32,  -8),   # left; pipe goes lower-right only
    "N": ( 16,  -8),   # right; pipes go up / left / down
    "O": (-32, -22),   # top-left;  pipes go right / lower-left
    "P": ( 16,   0),   # right; pipe goes up only
    "Q": (-32,  -8),   # left; pipe goes upper-right only
}

# ── Pipe network ──────────────────────────────────────────────────────────────
def build_network():
    nodes = {
        "A": (660,  55), "B": (660, 140), "C": (835, 140),
        "D": (660, 232), "E": (410, 232), "G": (660, 458),
        "H": (410, 458), "F": (800, 325), "I": (878, 325),
        "J": (800, 415), "K": (748, 458), "L": (272, 458),
        "M": (188, 418), "N": (272, 555), "O": (188, 555),
        "P": (272, 645), "Q": (100, 690),
    }
    seg_pairs = [
        ("A", "B"), ("B", "C"), ("B", "D"), ("D", "E"),
        ("E", "H"), ("H", "G"), ("D", "F"),
        ("F", "I"), ("F", "J"), ("G", "K"), ("H", "L"),
        ("L", "M"), ("L", "N"), ("N", "O"), ("N", "P"), ("O", "Q"),
    ]
    seg_coords = [(nodes[a], nodes[b]) for a, b in seg_pairs]
    return nodes, seg_coords

def pt_seg_closest(px, py, ax, ay, bx, by):
    dx, dy = bx - ax, by - ay
    denom  = dx * dx + dy * dy
    if denom == 0:
        return math.hypot(px - ax, py - ay), ax, ay
    t  = max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / denom))
    cx, cy = ax + t * dx, ay + t * dy
    return math.hypot(px - cx, py - cy), cx, cy


class Particle:
    __slots__ = ("x", "y", "vx", "vy", "life", "max_life", "r", "kind", "active")
    def __init__(self): self.active = False
    def spawn(self, x, y, vx, vy, life, r, kind):
        self.x, self.y   = float(x), float(y)
        self.vx, self.vy = float(vx), float(vy)
        self.life = self.max_life = life
        self.r, self.kind = r, kind
        self.active = True
    def step(self, dt):
        self.vy   += GRAVITY * dt
        self.x    += self.vx * dt
        self.y    += self.vy * dt
        self.life -= 1
        if self.life <= 0: self.active = False

class ParticlePool:
    def __init__(self, cap):
        self._pool = [Particle() for _ in range(cap)]
        self._idx  = 0
    def emit_valve(self, x, y):
        p = self._pool[self._idx % len(self._pool)]
        self._idx += 1
        p.spawn(x, y, random.uniform(-50, 50), random.uniform(30, 165),
                random.randint(80, 130), random.randint(2, 3), "valve")
    def emit_leak(self, x, y):
        p = self._pool[self._idx % len(self._pool)]
        self._idx += 1
        angle = random.uniform(0, 2 * math.pi)
        speed = random.uniform(100, 370)
        p.spawn(x, y, speed * math.cos(angle), speed * math.sin(angle) - 95,
                random.randint(100, 178), random.randint(2, 5), "leak")
    def step(self, dt):
        for p in self._pool:
            if p.active: p.step(dt)
    def draw(self, surf):
        for p in self._pool:
            if not p.active: continue
            a   = p.life / p.max_life
            col = (
                tuple(int(C_VALVE_BASE[i] + (C_VALVE_LIGHT[i] - C_VALVE_BASE[i]) * a) for i in range(3))
                if p.kind == "valve" else
                tuple(int(C_LEAK_BASE[i]  + (C_LEAK_LIGHT[i]  - C_LEAK_BASE[i])  * a) for i in range(3))
            )
            try: pygame.draw.circle(surf, col, (int(p.x), int(p.y)), p.r)
            except Exception: pass


def glow_circle(surf, colour, cx, cy, radius, layers=3, alpha_step=65):
    for i in range(layers, 0, -1):
        rf   = radius + i * 3
        alph = max(0, 255 - i * alpha_step)
        gs   = pygame.Surface((rf * 2 + 2, rf * 2 + 2), pygame.SRCALPHA)
        pygame.draw.circle(gs, (*colour, alph), (rf + 1, rf + 1), rf)
        surf.blit(gs, (cx - rf - 1, cy - rf - 1))
    pygame.draw.circle(surf, colour, (cx, cy), radius)

def draw_patch(surf, cx, cy, size=10):
    pygame.draw.rect(surf, C_PATCH,       (cx - size, cy - size // 2, size * 2, size),     border_radius=3)
    pygame.draw.rect(surf, (200, 255, 160),(cx - size + 2, cy - size // 2 + 2, size * 2 - 4, size - 4), border_radius=2)


# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("Pipe Network - MQTT Publisher")
    clock  = pygame.time.Clock()

    nodes, seg_coords = build_network()
    pool  = ParticlePool(MAX_PARTICLES)
    frame = 0

    valve_open  = {key: False for key in nodes}
    pipe_leaks  = []   # [cx, cy, age]
    fixed_anims = []   # [cx, cy, timer]

    flow_dots = [
        {"seg": seg, "t": random.random(), "spd": random.uniform(0.003, 0.007)}
        for seg in seg_coords
    ]
    node_list = list(nodes.items())

    font_sm   = pygame.font.SysFont("monospace", 15)
    font_med  = pygame.font.SysFont("monospace", 17, bold=True)
    font_node = pygame.font.SysFont("monospace", 19, bold=True)   # node labels

    def hit_node(mx, my):
        for key, pos in node_list:
            if math.hypot(mx - pos[0], my - pos[1]) <= NODE_HIT_R: return key
        return None

    def hit_pipe_point(mx, my):
        best_d, best_cx, best_cy = 1e9, 0.0, 0.0
        for seg in seg_coords:
            d, cx, cy = pt_seg_closest(mx, my, seg[0][0], seg[0][1], seg[1][0], seg[1][1])
            if d < best_d: best_d, best_cx, best_cy = d, cx, cy
        return (best_cx, best_cy) if best_d <= PIPE_HIT_R else None

    running = True
    while running:
        dt     = clock.tick(FPS) / 1000.0
        frame += 1

        if frame % FPS == 0:
            calculate_and_publish_pressure(valve_open, pipe_leaks)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            if event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_q, pygame.K_ESCAPE): running = False
                if event.key == pygame.K_r:
                    for k in valve_open: valve_open[k] = False

            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                mx, my = event.pos
                nk = hit_node(mx, my)
                if nk is not None:
                    valve_open[nk] = not valve_open[nk]
                else:
                    fix_idx = next(
                        (i for i, lk in enumerate(pipe_leaks)
                         if math.hypot(mx - lk[0], my - lk[1]) < LEAK_FIX_R),
                        None
                    )
                    if fix_idx is not None:
                        lk = pipe_leaks.pop(fix_idx)
                        fixed_anims.append([lk[0], lk[1], 72])
                    else:
                        pt = hit_pipe_point(mx, my)
                        if pt is not None:
                            cx, cy = pt
                            if not any(math.hypot(cx - lk[0], cy - lk[1]) < 14 for lk in pipe_leaks):
                                pipe_leaks.append([cx, cy, 0])

        for key, pos in node_list:
            if valve_open[key]:
                for _ in range(VALVE_RATE): pool.emit_valve(pos[0], pos[1])
        for lk in pipe_leaks:
            lk[2] += 1
            for _ in range(LEAK_RATE): pool.emit_leak(lk[0], lk[1])

        pool.step(dt)

        for fd in flow_dots:
            fd["t"] += fd["spd"]
            if fd["t"] > 1.0: fd["t"] = 0.0

        for fa in fixed_anims: fa[2] -= 1
        fixed_anims = [fa for fa in fixed_anims if fa[2] > 0]

        # ── Draw ──────────────────────────────────────────────────────────────
        screen.fill(C_BG)

        # Pipes
        for seg in seg_coords:
            p1 = (int(seg[0][0]), int(seg[0][1]))
            p2 = (int(seg[1][0]), int(seg[1][1]))
            pygame.draw.line(screen, C_PIPE_DARK,      p1, p2, PIPE_RADIUS + 4)
            pygame.draw.line(screen, C_PIPE_MID,       p1, p2, PIPE_RADIUS)
            pygame.draw.line(screen, C_PIPE_HIGHLIGHT, p1, p2, max(1, PIPE_RADIUS - 4))

        # Flow dots
        for fd in flow_dots:
            seg, t = fd["seg"], fd["t"]
            fx = int(seg[0][0] + t * (seg[1][0] - seg[0][0]))
            fy = int(seg[0][1] + t * (seg[1][1] - seg[0][1]))
            pygame.draw.circle(screen, C_FLOW_DOT, (fx, fy), 2)

        pool.draw(screen)

        # Nodes + labels
        for key, pos in node_list:
            px, py  = int(pos[0]), int(pos[1])
            is_open = valve_open[key]

            pygame.draw.circle(screen, C_NODE_OPEN_OUT if is_open else C_NODE_OUTER, (px, py), 12)
            pygame.draw.circle(screen, C_NODE_OPEN     if is_open else C_NODE_INNER, (px, py),  9)

            if is_open:
                pulse_r = 13 + int(3 * math.sin(frame * 0.12))
                glow_circle(screen, C_NODE_OPEN, px, py, pulse_r, layers=2, alpha_step=80)
                arr_y = py + 14
                pygame.draw.polygon(screen, C_NODE_OPEN,
                                    [(px, arr_y + 7), (px - 5, arr_y), (px + 5, arr_y)])

            # ── Node label (per-node offset keeps it off every pipe) ──────────
            dx, dy = NODE_LABEL_OFFSET.get(key, (16, -22))
            lx, ly = px + dx, py + dy
            # dark shadow for readability over pipe colours
            shadow = font_node.render(key, True, (0, 0, 0))
            screen.blit(shadow, (lx + 1, ly + 1))
            lbl = font_node.render(key, True, (230, 230, 255))
            screen.blit(lbl, (lx, ly))

        # Leaks
        for lk in pipe_leaks:
            lx, ly, age = int(lk[0]), int(lk[1]), lk[2]
            for i in range(8):
                ang = i * math.pi / 4 + age * 0.012
                ex  = lx + int((PIPE_RADIUS + 7) * math.cos(ang))
                ey  = ly + int((PIPE_RADIUS + 7) * math.sin(ang))
                pygame.draw.line(screen, C_CRACK, (lx, ly), (ex, ey), 1)
            pulse = PIPE_RADIUS + 4 + int(3 * math.sin(age * 0.18))
            glow_circle(screen, C_LEAK_RED, lx, ly, pulse, layers=2, alpha_step=75)
            if age < 90:
                lbl = font_sm.render("BURST!", True, (255, 200, 80))
                lbl.set_alpha(max(0, 255 - int(age * 2.8)))
                screen.blit(lbl, (lx + 12, ly - 16))
            if 30 < age < 300:
                hint = font_sm.render("click to fix", True, (180, 255, 160))
                hint.set_alpha(min(180, (age - 30) * 3))
                screen.blit(hint, (lx - hint.get_width() // 2, ly + PIPE_RADIUS + 10))

        # Fixed animations
        for fa in fixed_anims:
            fx_x, fx_y, timer = fa
            draw_patch(screen, int(fx_x), int(fx_y))
            lbl = font_med.render("✔ FIXED!", True, C_FIXED)
            lbl.set_alpha(min(255, timer * 5))
            screen.blit(lbl, (int(fx_x) - lbl.get_width() // 2,
                               int(fx_y) - 22 - int((72 - timer) * 0.6)))

        pygame.display.flip()

    mqtt_client.loop_stop()
    mqtt_client.disconnect()
    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()