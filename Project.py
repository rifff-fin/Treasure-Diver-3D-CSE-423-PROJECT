from OpenGL.GL import *
from OpenGL.GLUT import *
from OpenGL.GLU import *
import math
import random
import time
import sys


WINDOW_W = 1000
WINDOW_H = 800


score = 0
lives = 3
oxygen = 100.0
game_over = False
game_started = False
paused = False
current_level = 1
max_levels = 5
level_depth = 300  


player_pos = [0.0, 0.0, 0.0]
player_speed = 20 
player_rotation = 0.0
player_invincible = False
invincibility_timer = 0.0
speed_boost_timer = 0.0


camera_pos = [0.0, 500.0, 500.0]
camera_mode = "follow"  
camera_angle_x = 0.0
camera_angle_y = 0.0


treasures = []
enemies = []
powerups = []
bubbles = []

challenges = []
current_challenge = None
challenge_timer = 0
challenge_duration = 0
challenge_active = False
challenge_failed = False
challenge_fail_timer = 0
completed_challenges = 0 

magnet_active = False
magnet_timer = 0.0
MAGNET_DURATION = 8.0  
completed_challenges = 0

GRID_SIZE = 1500  # Increased grid size for more space
WATER_DEPTH = level_depth * max_levels
MAX_OXYGEN = 100.0
INVINCIBILITY_DURATION = 5  # seconds
SPEED_BOOST_DURATION = 5    # seconds
# Make oxygen drain visible but tunable (per second baseline)
OXYGEN_DRAIN_RATE = 0.9   # baseline per second
last_time = time.time()

# Water colors for different levels (RGB values) -- opaque colors (no blending)
water_colors = [
    (0.0, 0.5, 0.8),   # Level 1 - Light blue
    (0.0, 0.4, 0.7),   # Level 2
    (0.0, 0.3, 0.6),   # Level 3
    (0.0, 0.2, 0.5),   # Level 4
    (0.0, 0.1, 0.4)    # Level 5 - Dark blue
]

random.seed(time.time())

def generate_level_content(level):
    global treasures, enemies, powerups, bubbles
    treasures = []
    enemies = []
    powerups = []
    bubbles = []
    level_z_min = -(level * level_depth)
    level_z_max = -((level - 1) * level_depth)

    # Normal treasures
    for _ in range(5):
        treasures.append({
            'pos': [random.randint(-GRID_SIZE//3, GRID_SIZE//3),
                    random.randint(-GRID_SIZE//3, GRID_SIZE//3),
                    random.randint(level_z_min + 50, level_z_max - 50)],
            'type': 'normal',
            'collected': False,
            'bob_offset': random.random() * 10,
            'rotation': random.random() * 360
        })

    # Sharks
    for _ in range(5 + level):
        angle = random.random() * 2 * math.pi
        radius = GRID_SIZE//2 * 0.6
        enemies.append({
            'pos': [radius * math.cos(angle), radius * math.sin(angle), random.randint(level_z_min + 100, level_z_max - 100)],
            'type': 'shark',
            'direction': angle + math.pi/2,
            'speed': random.uniform(0.5, 0.8 + level * 0.1),
            'size': random.uniform(30, 40)
        })

    # Jellyfish
    for _ in range(4 + level):
        enemies.append({
            'pos': [random.randint(-GRID_SIZE//2, GRID_SIZE//2),
                    random.randint(-GRID_SIZE//2, GRID_SIZE//2),
                    random.randint(level_z_min + 50, level_z_max - 50)],
            'type': 'jellyfish',
            'pulse': 0.0,
            'pulse_dir': 1,
            'size': random.uniform(15, 25)
        })

    # Powerups
    for _ in range(10 + level):
        powerups.append({
            'pos': [random.randint(-GRID_SIZE//2, GRID_SIZE//2),
                    random.randint(-GRID_SIZE//2, GRID_SIZE//2),
                    random.randint(level_z_min + 50, level_z_max - 50)],
            'type': random.choice(['oxygen', 'speed', 'shield']),
            'active': True,
            'size': 25
        })

    # Bubbles
    for _ in range(30):
        bubbles.append({
            'pos': [random.randint(-GRID_SIZE//2, GRID_SIZE//2),
                    random.randint(-GRID_SIZE//2, GRID_SIZE//2),
                    random.randint(level_z_min, 0)],
            'size': random.uniform(3, 10),
            'speed': random.uniform(0.5, 2.0)
        })

def generate_challenge():
    challenge_types = [
        {
            'type': 'collect',
            'description': 'Collect 2 treasures in 40 seconds!',
            'required': 2,
            'time': 40,
            'reward': 50
        },
        {
            'type': 'avoid',
            'description': 'Avoid sharks for 20 seconds!',
            'time': 20,
            'reward': 40
        },
       
    ]
    return random.choice(challenge_types)

def init_game():
    global current_level, oxygen, lives, score, game_over, last_time, player_pos, player_speed, player_invincible, paused, current_challenge, challenge_active, challenge_failed
    current_level = 1
    oxygen = MAX_OXYGEN
    lives = 3
    score = 0
    game_over = False
    paused = False
    player_pos[0], player_pos[1], player_pos[2] = 0.0, 0.0, 0.0
    player_speed = 5.0
    player_invincible = False
    current_challenge = None
    challenge_active = False
    challenge_failed = False
    last_time = time.time()
    generate_level_content(current_level)

def check_level_completion():
    global current_level, oxygen, game_over
    remaining_treasures = sum(1 for t in treasures if not t['collected'])
    if remaining_treasures == 0:
        if current_level >= max_levels:
            current_level += 1
            return True
        current_level += 1
        oxygen = MAX_OXYGEN
        player_pos[2] = -((current_level - 1) * level_depth) + 50
        generate_level_content(current_level)
    return False

def draw_text(x, y, text, font=GLUT_BITMAP_HELVETICA_18):
    glColor3f(1.0, 1.0, 1.0)
    glRasterPos2f(x, y)
    for ch in text:
        glutBitmapCharacter(font, ord(ch))

def draw_shark(size):
    # Body
    glColor3f(0.6, 0.6, 0.7)
    glPushMatrix()
    glRotatef(90, 0, 1, 0)
    quad = gluNewQuadric()
    gluCylinder(quad, size * 0.5, size * 0.3, size * 2, 16, 16)
    glPopMatrix()

    # Nose 
    glColor3f(0.5, 0.5, 0.6)
    glPushMatrix()
    glRotatef(-90, 0, 1, 0)
    glutSolidCone(size * 0.5, size * 0.7, 16, 16)
    glPopMatrix()

    # Fins
    glColor3f(0.5, 0.5, 0.6)
    glPushMatrix()
    glTranslatef(size * 0.5, 0, size * 0.5)
    glRotatef(-45, 1, 0, 0)
    glutSolidCone(size * 0.2, size * 0.7, 10, 10)
    glPopMatrix()

    glPushMatrix()
    glTranslatef(size * 0.5, 0, -size * 0.5)
    glRotatef(45, 1, 0, 0)
    glutSolidCone(size * 0.2, size * 0.7, 10, 10)
    glPopMatrix()

def draw_jellyfish(size, pulse):
    glColor3f(0.8, 0.5, 0.8)
    glPushMatrix()
    glScalef(1 + pulse * 0.2, 1 + pulse * 0.2, 0.6)
    glutSolidSphere(size, 16, 16)
    glPopMatrix()

    # Tentacles
    glColor3f(0.7, 0.3, 0.7)
    for i in range(8):
        angle = i * (360 / 8) 
        glPushMatrix()
        glTranslatef(0, 0, -size * 0.6)
        glRotatef(angle, 0, 0, 1)
        glTranslatef(size * 0.5, 0, 0)
        glRotatef(-90, 1, 0, 0)
        quad = gluNewQuadric()
        gluCylinder(quad, 1.5, 1.0, size * 1.5 * (1 + pulse * 0.1), 8, 8)
        glPopMatrix()


def draw_treasure(t_type, rotation):
    if t_type == 'normal':
        glColor3f(1.0, 0.84, 0.0)  
        glPushMatrix()
        glRotatef(rotation, 1, 0, 0)
        size = 12
        # Draw cube
        glBegin(GL_QUADS)
        # Top face
        glVertex3f(-size, size, -size)
        glVertex3f(size, size, -size)
        glVertex3f(size, size, size)
        glVertex3f(-size, size, size)
        # Bottom face
        glVertex3f(-size, -size, -size)
        glVertex3f(size, -size, -size)
        glVertex3f(size, -size, size)
        glVertex3f(-size, -size, size)
        # Front face
        glVertex3f(-size, -size, size)
        glVertex3f(size, -size, size)
        glVertex3f(size, size, size)
        glVertex3f(-size, size, size)
        # Back face
        glVertex3f(-size, -size, -size)
        glVertex3f(size, -size, -size)
        glVertex3f(size, size, -size)
        glVertex3f(-size, size, -size)
        # Left face
        glVertex3f(-size, -size, -size)
        glVertex3f(-size, -size, size)
        glVertex3f(-size, size, size)
        glVertex3f(-size, size, -size)
        # Right face
        glVertex3f(size, -size, -size)
        glVertex3f(size, -size, size)
        glVertex3f(size, size, size)
        glVertex3f(size, size, -size)
        glEnd()
        glPopMatrix()
    else:
        glColor3f(0.8, 0.8, 1.0)
        glPushMatrix()
        glRotatef(rotation, 0, 1, 0)
        quad = gluNewQuadric()
        gluCylinder(quad, 10, 10, 10, 12, 12)
        glPopMatrix()

def draw_powerup(p_type, size):
    if p_type == 'oxygen':
        glColor3f(0.0, 0.7, 1.0)
        glutSolidSphere(size, 20, 20)
    elif p_type == 'speed':
        glColor3f(0.0, 1.0, 0.0)
        glutSolidSphere(size, 20, 20)
    elif p_type == 'shield':
        glColor3f(1.0, 1.0, 0.0)
        glutSolidSphere(size, 20, 20)

def draw_player():
    # Main body 
    glColor3f(0.0, 0.5, 1.0) 
    glPushMatrix()
    glTranslatef(0, 0, -10)
    quad = gluNewQuadric()
    gluCylinder(quad, 8, 8, 25, 16, 16)  
    glPopMatrix()
    
    # Oxygen tank 
    glColor3f(0.3, 0.3, 0.3) 
    glPushMatrix()
    glTranslatef(0,13, -7)  
    glRotatef(90, 0, 0, 1)  
    quad = gluNewQuadric()
    gluCylinder(quad, 5, 5, 20, 16, 16)  
    glTranslatef(0, 0, 20)  
    glutSolidSphere(4, 16, 16)  
    glPopMatrix()
    
    # Head
    glColor3f(1.0, 0.8, 0.6)  
    glPushMatrix()
    glTranslatef(0, 0, 20)
    glutSolidSphere(7, 16, 16)
    glPopMatrix()
    

    # Arms 
    glColor3f(0.0, 0.0, 1.0) 
    # Right
    glPushMatrix()
    glTranslatef(8, 0, 5)  
    glRotatef(90, 0, 1, 0)  
    quad = gluNewQuadric()
    gluCylinder(quad, 3, 2, 15, 12, 12)  
    glPopMatrix()
    
    # Left
    glPushMatrix()
    glTranslatef(-8, 0, 5)  
    glRotatef(-90, 0, 1, 0)  
    quad = gluNewQuadric()
    gluCylinder(quad, 3, 2, 15, 12, 12)  
    glPopMatrix()
    
    # Legs 
    glColor3f(0.2, 0.5, 1.0) 
    # Right
    glPushMatrix()
    glTranslatef(4, 0, -10) 
    glRotatef(180, 1, 0, 0)  
    quad = gluNewQuadric()
    gluCylinder(quad, 4, 3, 15, 12, 12)  
    glPopMatrix()
    
    # Left
    glPushMatrix()
    glTranslatef(-4, 0, -10) 
    glRotatef(180, 1, 0, 0) 
    quad = gluNewQuadric()
    gluCylinder(quad, 4, 3, 15, 12, 12) 
    glPopMatrix()
    
    # Fins 
    glColor3f(0.8, 0.8, 0.8) 
    # Right 
    glPushMatrix()
    glTranslatef(4, 0, -25)  
    glRotatef(90, 1, 0, 0)  
    glutSolidCone(6, 10, 12, 12) 
    glPopMatrix()
    
    # Left fin
    glPushMatrix()
    glTranslatef(-4, 0, -25) 
    glRotatef(90, 1, 0, 0)  
    glutSolidCone(6, 10, 12, 12)  
    glPopMatrix()
    
    # invincibility shield
    if player_invincible:
        glColor3f(1.0, 1.0, 0.6)
        glPushMatrix()
        glTranslatef(0, 0, 5)
        glutSolidSphere(20, 16, 16)
        glPopMatrix()

def draw_environment():
    level_z = -(current_level * level_depth)
    glColor3f(0.4, 0.3, 0.1)  
    glBegin(GL_QUADS)
    glVertex3f(-GRID_SIZE/2, -GRID_SIZE/2, level_z)
    glVertex3f(GRID_SIZE/2, -GRID_SIZE/2, level_z)
    glVertex3f(GRID_SIZE/2, GRID_SIZE/2, level_z)
    glVertex3f(-GRID_SIZE/2, GRID_SIZE/2, level_z)
    glEnd()

    glColor3f(0.5, 0.4, 0.2)
    glBegin(GL_LINES)
    for i in range(-GRID_SIZE//2, GRID_SIZE//2 + 1, 100):
        glVertex3f(i, -GRID_SIZE/2, level_z)
        glVertex3f(i, GRID_SIZE/2, level_z)
        glVertex3f(-GRID_SIZE/2, i, level_z)
        glVertex3f(GRID_SIZE/2, i, level_z)
    glEnd()

    r, g, b = water_colors[min(current_level - 1, len(water_colors)-1)]
    glColor3f(r, g, b)
    glBegin(GL_QUADS)
    glVertex3f(-GRID_SIZE/2, -GRID_SIZE/2, 0)
    glVertex3f(GRID_SIZE/2, -GRID_SIZE/2, 0)
    glVertex3f(GRID_SIZE/2, GRID_SIZE/2, 0)
    glVertex3f(-GRID_SIZE/2, GRID_SIZE/2, 0)
    glEnd()

    wall_col = 0.3
    glColor3f(wall_col, wall_col, 0.5)
    # front
    glBegin(GL_QUADS)
    glVertex3f(-GRID_SIZE/2, -GRID_SIZE/2, level_z)
    glVertex3f(GRID_SIZE/2, -GRID_SIZE/2, level_z)
    glVertex3f(GRID_SIZE/2, -GRID_SIZE/2, 0)
    glVertex3f(-GRID_SIZE/2, -GRID_SIZE/2, 0)
    glEnd()
    # back
    glBegin(GL_QUADS)
    glVertex3f(-GRID_SIZE/2, GRID_SIZE/2, level_z)
    glVertex3f(GRID_SIZE/2, GRID_SIZE/2, level_z)
    glVertex3f(GRID_SIZE/2, GRID_SIZE/2, 0)
    glVertex3f(-GRID_SIZE/2, GRID_SIZE/2, 0)
    glEnd()
    # left
    glBegin(GL_QUADS)
    glVertex3f(-GRID_SIZE/2, -GRID_SIZE/2, level_z)
    glVertex3f(-GRID_SIZE/2, GRID_SIZE/2, level_z)
    glVertex3f(-GRID_SIZE/2, GRID_SIZE/2, 0)
    glVertex3f(-GRID_SIZE/2, -GRID_SIZE/2, 0)
    glEnd()
    # right
    glBegin(GL_QUADS)
    glVertex3f(GRID_SIZE/2, -GRID_SIZE/2, level_z)
    glVertex3f(GRID_SIZE/2, GRID_SIZE/2, level_z)
    glVertex3f(GRID_SIZE/2, GRID_SIZE/2, 0)
    glVertex3f(GRID_SIZE/2, -GRID_SIZE/2, 0)
    glEnd()

def draw_bubbles():
    glColor3f(1.0, 1.0, 1.0)
    for bubble in bubbles:
        glPushMatrix()
        glTranslatef(bubble['pos'][0], bubble['pos'][1], bubble['pos'][2])
        glutSolidSphere(bubble['size'], 8, 8)
        glPopMatrix()

def draw_ui():
   
    was_depth = glIsEnabled(GL_DEPTH_TEST)
    if was_depth:
        glDisable(GL_DEPTH_TEST)

    draw_text(20, WINDOW_H - 40, f"Score: {score}")
    draw_text(20, WINDOW_H - 70, f"Lives: {lives}")
    draw_text(20, WINDOW_H - 100, f"Level: {min(current_level, max_levels)}/{max_levels}")
    draw_text(20, WINDOW_H - 130, "Oxygen:")

    bar_x = 120
    bar_y = WINDOW_H - 135
    bar_w = 200  
    bar_h = 10
    glColor3f(0.6, 0.0, 0.0)
    glBegin(GL_QUADS)
    glVertex2f(bar_x, bar_y + bar_h)
    glVertex2f(bar_x + bar_w, bar_y + bar_h)
    glVertex2f(bar_x + bar_w, bar_y)
    glVertex2f(bar_x, bar_y)
    glEnd()

    oxy_ratio = max(0.0, min(oxygen / MAX_OXYGEN, 1.0))
    fill_w = bar_w * oxy_ratio 
    r, g, b = water_colors[min(current_level - 1, len(water_colors)-1)]
    fill_color = (1.0 - r, 1.0 - g, 1.0 - b)
    glColor3f(*fill_color)
    glBegin(GL_QUADS)
    glVertex2f(bar_x, bar_y + bar_h)
    glVertex2f(bar_x + fill_w, bar_y + bar_h)
    glVertex2f(bar_x + fill_w, bar_y)
    glVertex2f(bar_x, bar_y)
    glEnd()

    # Challenge 
    if current_challenge and challenge_active:
        # Challenge background
        glColor3f(0.2, 0.2, 0.2)
        glBegin(GL_QUADS)
        glVertex2f(WINDOW_W/2 - 200, WINDOW_H - 180)
        glVertex2f(WINDOW_W/2 + 200, WINDOW_H - 180)
        glVertex2f(WINDOW_W/2 + 200, WINDOW_H - 150)
        glVertex2f(WINDOW_W/2 - 200, WINDOW_H - 150)
        glEnd()
        
        draw_text(WINDOW_W/2 - 190, WINDOW_H - 165, f"CHALLENGE: {current_challenge['description']}")
        
        # Timer bar
        timer_width = 380 * (challenge_timer / current_challenge['time'])
        glColor3f(0.8, 0.8, 0.0)
        glBegin(GL_QUADS)
        glVertex2f(WINDOW_W/2 - 190, WINDOW_H - 175)
        glVertex2f(WINDOW_W/2 - 190 + timer_width, WINDOW_H - 175)
        glVertex2f(WINDOW_W/2 - 190 + timer_width, WINDOW_H - 180)
        glVertex2f(WINDOW_W/2 - 190, WINDOW_H - 180)
        glEnd()

    if challenge_failed:
        draw_text(WINDOW_W/2 - 100, WINDOW_H - 200, "CHALLENGE FAILED!", GLUT_BITMAP_HELVETICA_18)

    # Draw Pause and Exit
    btn_w = 120
    btn_h = 30
    padding = 10
    # Pause 
    pause_x = WINDOW_W - btn_w - padding
    pause_y = WINDOW_H - padding - btn_h
    glColor3f(0.2, 0.2, 0.2)
    glBegin(GL_QUADS)
    glVertex2f(pause_x, pause_y + btn_h)
    glVertex2f(pause_x + btn_w, pause_y + btn_h)
    glVertex2f(pause_x + btn_w, pause_y)
    glVertex2f(pause_x, pause_y)
    glEnd()
    draw_text(pause_x + 10, pause_y + 8, "Pause (P)")

    # Exit 
    exit_x = pause_x - btn_w - 10
    exit_y = pause_y
    glColor3f(0.2, 0.2, 0.2)
    glBegin(GL_QUADS)
    glVertex2f(exit_x, exit_y + btn_h)
    glVertex2f(exit_x + btn_w, exit_y + btn_h)
    glVertex2f(exit_x + btn_w, exit_y)
    glVertex2f(exit_x, exit_y)
    glEnd()
    draw_text(exit_x + 10, exit_y + 8, "Exit (X)")

    # Messages
    if game_over:
        draw_text(WINDOW_W/2 - 200, WINDOW_H/2 + 40, "GAME OVER - Press R to restart", GLUT_BITMAP_TIMES_ROMAN_24)
        draw_text(WINDOW_W/2 - 100, WINDOW_H/2 + 10, "Press ESC to exit", GLUT_BITMAP_HELVETICA_18)
    if current_level > max_levels:
        draw_text(WINDOW_W/2 - 300, WINDOW_H/2 + 40, "CONGRATULATIONS! YOU COMPLETED ALL LEVELS!", GLUT_BITMAP_TIMES_ROMAN_24)
        draw_text(WINDOW_W/2 - 100, WINDOW_H/2 + 10, "Press R to play again or ESC to exit", GLUT_BITMAP_HELVETICA_18)
    if not game_started:
        draw_text(WINDOW_W/2 - 200, WINDOW_H/2 + 40, "TREASURE DIVER 3D - Press SPACE to start", GLUT_BITMAP_TIMES_ROMAN_24)
        draw_text(WINDOW_W/2 - 200, WINDOW_H/2 + 10, "Controls: WASD to move, Q/E to ascend/descend", GLUT_BITMAP_9_BY_15)
        draw_text(WINDOW_W/2 - 200, WINDOW_H/2 - 10, "Arrow keys to rotate camera, Mouse to look around", GLUT_BITMAP_9_BY_15)
        draw_text(WINDOW_W/2 - 200, WINDOW_H/2 - 30, "Press ESC to exit game", GLUT_BITMAP_9_BY_15)
    if paused and not game_over and game_started:
        draw_text(WINDOW_W/2 - 50, WINDOW_H/2, "PAUSED", GLUT_BITMAP_TIMES_ROMAN_24)
    if was_depth:
        glEnable(GL_DEPTH_TEST)

def check_collisions():
    global score, lives, oxygen, player_invincible, invincibility_timer, speed_boost_timer, player_speed, game_over, current_challenge, challenge_active, challenge_failed

    player_radius = 15

    for treasure in treasures:
        if not treasure['collected']:
            dist = math.sqrt(sum((player_pos[i] - treasure['pos'][i]) ** 2 for i in range(3)))
            if dist < player_radius + 12:
                treasure['collected'] = True
                score += 10

    for enemy in enemies:
        dist = math.sqrt(sum((player_pos[i] - enemy['pos'][i]) ** 2 for i in range(3)))
        if enemy['type'] == 'shark':
            collision_radius = enemy['size'] * 1.2
        elif enemy['type'] == 'jellyfish':
            collision_radius = enemy['size'] * 1.5
        else:
            collision_radius = 35

        if dist < player_radius + collision_radius and not player_invincible:
            lives -= 1
            player_invincible = True
            invincibility_timer = time.time()
            
            if challenge_active and current_challenge and current_challenge['type'] == 'avoid' and enemy['type'] == 'shark':
                oxygen = max(0, oxygen - 15) 
                score -= 15 
                challenge_active = False
                current_challenge = None
                challenge_failed = True
                challenge_fail_timer = 2.0
                
            if lives <= 0:
                game_over = True

    for powerup in powerups:
        if powerup['active']:
            dist = math.sqrt(sum((player_pos[i] - powerup['pos'][i]) ** 2 for i in range(3)))
            if dist < player_radius + powerup.get('size', 15):
                powerup['active'] = False
                if powerup['type'] == 'oxygen':
                    oxygen = min(oxygen + 40, MAX_OXYGEN)
                    
                elif powerup['type'] == 'speed':
                    player_speed = 8.0
                    speed_boost_timer = time.time()
                    
                elif powerup['type'] == 'shield':
                    player_invincible = True
                    invincibility_timer = time.time()
                    

def spawn_dynamic_powerups():
    if random.random() < 0.002:
        level_z_min = -(current_level * level_depth)
        level_z_max = -((current_level - 1) * level_depth)
        powerups.append({
            'pos': [random.randint(-GRID_SIZE//2, GRID_SIZE//2),
                    random.randint(-GRID_SIZE//2, GRID_SIZE//2),
                    random.randint(level_z_min + 50, level_z_max - 50)],
            'type': random.choice(['oxygen', 'speed', 'shield']),
            'active': True,
            'size': 20
        })
def activate_magnet():
    global magnet_active, magnet_timer, completed_challenges
    magnet_active = True
    magnet_timer = time.time()
    completed_challenges = 0 

def update_challenges():
    global current_challenge, challenge_timer, score, challenge_active, challenge_failed, challenge_fail_timer, oxygen, lives, player_speed,completed_challenges
    
    if challenge_failed:
        challenge_fail_timer -= 0.016
        if challenge_fail_timer <= 0:
            challenge_failed = False
        return

    if not challenge_active and current_challenge is None and random.random() < 0.008:
        current_challenge = generate_challenge()
        if current_challenge:
            challenge_timer = current_challenge['time']
            challenge_active = True
            if current_challenge['type'] == 'collect':
                current_challenge['initial_score'] = score
            
        return

    if challenge_active and current_challenge:
        challenge_timer -= 0.016

        if current_challenge['type'] == 'collect':
            collected_count = (score - current_challenge.get('initial_score', 0)) // 10
            if collected_count >= current_challenge['required']:
                score += current_challenge['reward']
                current_challenge = None
                challenge_active = False
                completed_challenges += 1
                if completed_challenges >= 2:
                    activate_magnet()
        
                return
                
        elif current_challenge['type'] == 'avoid' and challenge_timer <= 0:
            score += current_challenge['reward']
            current_challenge = None
            challenge_active = False
            completed_challenges += 1
            if completed_challenges >= 2:
                activate_magnet()
    
            return
            
        
        
        # Check if challenge failed (time ran out)
        if challenge_timer <= 0:
            
            if current_challenge['type'] == 'collect':
                oxygen = max(0, oxygen - 15)  
            elif current_challenge['type'] == 'avoid':
                score = max(0, score - 20) 
            
            
            challenge_failed = True
            challenge_fail_timer = 2.0  
            current_challenge = None
            challenge_active = False

def update_game():
    global oxygen, player_invincible, invincibility_timer, speed_boost_timer, player_speed, lives, game_over, current_level, last_time, paused, magnet_active, magnet_timer

    if not game_started or game_over or paused:
        last_time = time.time()
        return

    current_time = time.time()
    time_diff = current_time - last_time
    last_time = current_time

    # Update oxygen
    level_scale = (current_level - 1) * 0.5
    oxygen_drain = OXYGEN_DRAIN_RATE * time_diff * (1 + level_scale)
    oxygen -= oxygen_drain
    oxygen = max(0.0, oxygen)

    if oxygen <= 0.0:
        lives -= 1
        oxygen = MAX_OXYGEN
        if lives <= 0:
            game_over = True

    if check_level_completion():
        return

    if player_invincible and (time.time() - invincibility_timer > INVINCIBILITY_DURATION):
        player_invincible = False

    if player_speed > 5.0 and (time.time() - speed_boost_timer > SPEED_BOOST_DURATION):
        player_speed = 5.0

    for treasure in treasures:
        if not treasure['collected']:
            treasure['bob_offset'] += 0.1
            treasure['rotation'] = (treasure['rotation'] + 1) % 360

    for enemy in enemies:
        if enemy['type'] == 'shark':
            enemy['pos'][0] += math.cos(enemy['direction']) * enemy['speed'] * 0.7
            enemy['pos'][1] += math.sin(enemy['direction']) * enemy['speed'] * 0.7
            if (abs(enemy['pos'][0]) > GRID_SIZE/2 - 100 or abs(enemy['pos'][1]) > GRID_SIZE/2 - 100):
                enemy['direction'] = (enemy['direction'] + math.pi/2 + random.random() * math.pi/2) % (2 * math.pi)
    
        elif enemy['type'] == 'jellyfish':
            enemy['pulse'] += 0.03 * enemy['pulse_dir']
            if enemy['pulse'] > 1 or enemy['pulse'] < -1:
                enemy['pulse_dir'] *= -1
            
            if 'dir' not in enemy:
                enemy['dir'] = random.random() * 2 * math.pi
            if 'speed' not in enemy:
                enemy['speed'] = random.uniform(0.3, 0.8)
            
            enemy['pos'][0] += math.cos(enemy['dir']) * enemy['speed']
            enemy['pos'][1] += math.sin(enemy['dir']) * enemy['speed']

            if abs(enemy['pos'][0]) > GRID_SIZE/2 - 50 or abs(enemy['pos'][1]) > GRID_SIZE/2 - 50:
                enemy['dir'] = random.random() * 2 * math.pi

    for powerup in powerups:
        if powerup['active']:
            powerup['pos'][2] += 0.3

    for bubble in bubbles:
        bubble['pos'][2] += bubble['speed']
        if bubble['pos'][2] > 0:
            bubble['pos'][0] = random.randint(-GRID_SIZE//2, GRID_SIZE//2)
            bubble['pos'][1] = random.randint(-GRID_SIZE//2, GRID_SIZE//2)
            bubble['pos'][2] = random.randint(-(current_level * level_depth), -((current_level - 1) * level_depth))
    if magnet_active:
        if time.time() - magnet_timer > MAGNET_DURATION:
            magnet_active = False
        else:
            # Pull nearby treasures toward player
            for treasure in treasures:
                if not treasure['collected']:
                    dx = player_pos[0] - treasure['pos'][0]
                    dy = player_pos[1] - treasure['pos'][1]
                    dz = player_pos[2] - treasure['pos'][2]
                    distance = math.sqrt(dx**2 + dy**2 + dz**2)
                    if distance < 300:
                        factor = 0.1  
                        treasure['pos'][0] += dx * factor
                        treasure['pos'][1] += dy * factor
                        treasure['pos'][2] += dz * factor
    check_collisions()
    spawn_dynamic_powerups()
    update_challenges()

def setup_camera():
    glMatrixMode(GL_PROJECTION)
    glLoadIdentity()
    gluPerspective(60, WINDOW_W / float(WINDOW_H), 1, 3000)
    glMatrixMode(GL_MODELVIEW)
    glLoadIdentity()

    if camera_mode == "follow":
        look_x = player_pos[0] + math.sin(math.radians(camera_angle_x))
        look_y = player_pos[1] + math.cos(math.radians(camera_angle_x))
        look_z = player_pos[2] + math.sin(math.radians(camera_angle_y))

        eye_x = player_pos[0] - math.sin(math.radians(camera_angle_x)) * 100
        eye_y = player_pos[1] - math.cos(math.radians(camera_angle_x)) * 100
        eye_z = player_pos[2] + 50 - math.sin(math.radians(camera_angle_y)) * 50

        gluLookAt(eye_x, eye_y, eye_z,
                  look_x, look_y, look_z,
                  0, 0, 1)
    else:
        gluLookAt(camera_pos[0], camera_pos[1], camera_pos[2],
                  player_pos[0], player_pos[1], player_pos[2],
                  0, 0, 1)

def show_screen():
    glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
    glLoadIdentity()

    setup_camera()

    draw_environment()
    draw_bubbles()

    glPushMatrix()
    glTranslatef(player_pos[0], player_pos[1], player_pos[2])
    draw_player()
    glPopMatrix()

    for treasure in treasures:
        if not treasure['collected']:
            glPushMatrix()
            glTranslatef(treasure['pos'][0],
                         treasure['pos'][1],
                         treasure['pos'][2] + math.sin(treasure['bob_offset']) * 5)
            draw_treasure(treasure['type'], treasure['rotation'])
            glPopMatrix()

    for enemy in enemies:
        glPushMatrix()
        glTranslatef(enemy['pos'][0], enemy['pos'][1], enemy['pos'][2])
        if enemy['type'] == 'shark':
            glRotatef(math.degrees(enemy['direction']) - 90, 0, 0, 1)
            draw_shark(enemy['size'])
        else:
            draw_jellyfish(enemy['size'], enemy['pulse'])
        glPopMatrix()

    for powerup in powerups:
        if powerup['active']:
            glPushMatrix()
            glTranslatef(powerup['pos'][0], powerup['pos'][1], powerup['pos'][2])
            draw_powerup(powerup['type'], powerup.get('size', 15))
            glPopMatrix()

    # Draw UI 
    glMatrixMode(GL_PROJECTION)
    glPushMatrix()
    glLoadIdentity()
    gluOrtho2D(0, WINDOW_W, 0, WINDOW_H)
    glMatrixMode(GL_MODELVIEW)
    glPushMatrix()
    glLoadIdentity()

    draw_ui()

    glPopMatrix()
    glMatrixMode(GL_PROJECTION)
    glPopMatrix()
    glMatrixMode(GL_MODELVIEW)

    glutSwapBuffers()

def keyboard_listener(key, x, y):
    global game_started, game_over, score, lives, oxygen, player_pos, camera_mode, current_level, paused, camera_pos

    key = key.decode('utf-8').lower()

    if not game_started and key == ' ':
        game_started = True
        init_game()
        return

    if (game_over or current_level > max_levels) and key == 'r':
        init_game()
        return

    if not game_started or game_over or current_level > max_levels:
        if key == 'p':
            paused = not paused
        return

    # Pause and Exit
    if key == 'p':
        paused = not paused
        return


    if key == 'x':
        glutLeaveMainLoop()


    if key == 'w':
        player_pos[0] += math.sin(math.radians(camera_angle_x)) * player_speed
        player_pos[1] += math.cos(math.radians(camera_angle_x)) * player_speed
    elif key == 's':
        player_pos[0] -= math.sin(math.radians(camera_angle_x)) * player_speed
        player_pos[1] -= math.cos(math.radians(camera_angle_x)) * player_speed
    elif key == 'a':
        player_pos[0] -= math.cos(math.radians(camera_angle_x)) * player_speed
        player_pos[1] += math.sin(math.radians(camera_angle_x)) * player_speed
    elif key == 'd':
        player_pos[0] += math.cos(math.radians(camera_angle_x)) * player_speed
        player_pos[1] -= math.sin(math.radians(camera_angle_x)) * player_speed
    elif key == 'q':
        player_pos[2] += player_speed
    elif key == 'e':
        player_pos[2] -= player_speed
    elif key == 'c':
        if camera_mode == "follow":
            camera_mode = "free"
            camera_pos[0] = player_pos[0]
            camera_pos[1] = player_pos[1] + 150
            camera_pos[2] = player_pos[2] + 50
        else:
            camera_mode = "follow"
    player_pos[0] = max(-GRID_SIZE/2 + 50, min(GRID_SIZE/2 - 50, player_pos[0]))
    player_pos[1] = max(-GRID_SIZE/2 + 50, min(GRID_SIZE/2 - 50, player_pos[1]))
    player_pos[2] = max(-(current_level * level_depth) + 50, min(-50, player_pos[2]))

    glutPostRedisplay()

def special_key_listener(key, x, y):
    global camera_angle_x, camera_angle_y, camera_pos

    if camera_mode == "follow":
        if key == GLUT_KEY_LEFT:
            camera_angle_x -= 5
        elif key == GLUT_KEY_RIGHT:
            camera_angle_x += 5
        elif key == GLUT_KEY_UP:
            camera_angle_y = min(camera_angle_y + 5, 90)
        elif key == GLUT_KEY_DOWN:
            camera_angle_y = max(camera_angle_y - 5, -90)
    else:
        if key == GLUT_KEY_LEFT:
            camera_pos[0] -= 10
        elif key == GLUT_KEY_RIGHT:
            camera_pos[0] += 10
        elif key == GLUT_KEY_UP:
            camera_pos[1] += 10
        elif key == GLUT_KEY_DOWN:
            camera_pos[1] -= 10

    glutPostRedisplay()

def idle():
    update_game()
    glutPostRedisplay()

def main():
    glutInit()
    glutInitDisplayMode(GLUT_DOUBLE | GLUT_RGB | GLUT_DEPTH)
    glutInitWindowSize(WINDOW_W, WINDOW_H)
    glutInitWindowPosition(0, 0)
    wind = glutCreateWindow(b"Treasure Diver 3D")

    glEnable(GL_DEPTH_TEST)

    glutDisplayFunc(show_screen)
    glutKeyboardFunc(keyboard_listener)
    glutSpecialFunc(special_key_listener)
    glutIdleFunc(idle)

    init_game()
    glutMainLoop()

if __name__ == "__main__":
    main()
