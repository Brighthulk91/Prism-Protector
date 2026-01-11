from OpenGL.GL import *
from OpenGL.GLUT import *
from OpenGL.GLU import *
import math
import random
import time

# ==========================================
# 1. GLOBAL SYSTEM STATE & CONSTANTS
# ==========================================
screen_w, screen_h = 1000, 800
is_home_page_running = True
gameover = False
game_paused = False
level = 1
wave_timer = 0
boss_active = False

diamond_health = 100
pulse_charge = 100.0
score = 0
high_score = 0

# Mechanics
cheat_mode = False
cheat_vision = False
cam_zoom = 1300.0
cam_offset = [0, -1100, cam_zoom]
ARENA_LIMIT = 1200
PRISM_SHIELD_RAD = 350

# Drone State
drone_pos = [0.0, -300.0, 60.0]
drone_angle = 90.0
drone_speed = 12.0
last_shot_time = 0

# Visuals
grid_pulse = 0.0
shake_amount = 0.0
alert_flash = 0.0

# ==========================================
# 2. ENTITY CLASSES
# ==========================================

class Particle:
    def __init__(self, x, y, z, color, speed_mult=1.0):
        self.x, self.y, self.z = x, y, z
        self.vx = random.uniform(-6, 6) * speed_mult
        self.vy = random.uniform(-6, 6) * speed_mult
        self.vz = random.uniform(2, 10) * speed_mult
        self.life = 1.0
        self.color = color

    def update(self):
        self.x += self.vx
        self.y += self.vy
        self.z += self.vz
        self.life -= 0.015
        return self.life > 0

class Bullet:
    def __init__(self, x, y, z, angle, color=(1,1,0), is_enemy=False):
        self.x, self.y, self.z = x, y, z
        rad = math.radians(angle)
        self.speed = 28 if not is_enemy else 10
        self.vx = math.cos(rad) * self.speed
        self.vy = math.sin(rad) * self.speed
        self.active = True
        self.color = color
        self.is_enemy = is_enemy

    def update(self):
        self.x += self.vx
        self.y += self.vy
        if abs(self.x) > ARENA_LIMIT + 500 or abs(self.y) > ARENA_LIMIT + 500:
            self.active = False

class Thief:
    def __init__(self, is_heavy=False, is_boss=False):
        self.is_heavy = is_heavy
        self.is_boss = is_boss
        self.hp = 15 if is_boss else (4 if is_heavy else 1)
        self.size = 120 if is_boss else (45 if is_heavy else 25)
        self.reset()

    def reset(self):
        side = random.randint(0, 3)
        dist = ARENA_LIMIT + 100
        if side == 0: self.x, self.y = random.uniform(-ARENA_LIMIT, ARENA_LIMIT), dist
        elif side == 1: self.x, self.y = random.uniform(-ARENA_LIMIT, ARENA_LIMIT), -dist
        elif side == 2: self.x, self.y = dist, random.uniform(-ARENA_LIMIT, ARENA_LIMIT)
        else: self.x, self.y = -dist, random.uniform(-ARENA_LIMIT, ARENA_LIMIT)
        
        self.z = 60 if self.is_boss else 30
        self.speed = 0.2 if self.is_boss else (random.uniform(0.4, 0.8))
        self.angle = 0

    def move(self):
        dx, dy = 0 - self.x, 0 - self.y
        dist = math.sqrt(dx**2 + dy**2)
        self.angle = math.degrees(math.atan2(dy, dx))
        
        if dist > 50:
            self.x += (dx/dist) * self.speed
            self.y += (dy/dist) * self.speed
        else:
            global diamond_health, gameover, shake_amount
            dmg = 50 if self.is_boss else (20 if self.is_heavy else 10)
            diamond_health -= dmg
            shake_amount = 25.0
            if self.is_boss: 
                self.hp = 0 
            else:
                self.reset()
            if diamond_health <= 0: 
                diamond_health = 0
                gameover = True

# Containers
thieves = [Thief() for _ in range(5)]
bullets = []
particles = []
debris = [[random.uniform(-3000, 3000), random.uniform(-3000, 3000), random.uniform(-500, 500)] for _ in range(200)]

# ==========================================
# 3. VERTEX GEOMETRY ENGINES
# ==========================================

def draw_prism_boundary():
    intruder_count = sum(1 for t in thieves if math.sqrt(t.x**2 + t.y**2) < PRISM_SHIELD_RAD)
    glBegin(GL_LINE_STRIP)
    for i in range(0, 360, 5):
        rad = math.radians(i)
        if intruder_count > 1: glColor3f(1.0, 0.0, 0.0)
        else: glColor3f(0, 1, 1)
        glVertex3f(math.cos(rad)*PRISM_SHIELD_RAD, math.sin(rad)*PRISM_SHIELD_RAD, 2)
    rad = math.radians(0)
    glVertex3f(math.cos(rad)*PRISM_SHIELD_RAD, math.sin(rad)*PRISM_SHIELD_RAD, 2)
    glEnd()

    if pulse_charge < 100:
        glBegin(GL_LINE_STRIP)
        r_pulse = (pulse_charge / 100.0) * PRISM_SHIELD_RAD
        glColor3f(0.8, 0.2, 1.0)
        for i in range(0, 360, 10):
            rad = math.radians(i)
            glVertex3f(math.cos(rad)*r_pulse, math.sin(rad)*r_pulse, 5)
        rad = math.radians(0)
        glVertex3f(math.cos(rad)*r_pulse, math.sin(rad)*r_pulse, 5)
        glEnd()

def draw_complex_cube(s):
    glBegin(GL_LINES)
    # Top
    glVertex3f(-s,-s,s); glVertex3f(s,-s,s)
    glVertex3f(s,-s,s); glVertex3f(s,s,s)
    glVertex3f(s,s,s); glVertex3f(-s,s,s)
    glVertex3f(-s,s,s); glVertex3f(-s,-s,s)
    # Bottom
    glVertex3f(-s,-s,-s); glVertex3f(s,-s,-s)
    glVertex3f(s,-s,-s); glVertex3f(s,s,-s)
    glVertex3f(s,s,-s); glVertex3f(-s,s,-s)
    glVertex3f(-s,s,-s); glVertex3f(-s,-s,-s)
    # Verticals
    glVertex3f(-s,-s,-s); glVertex3f(-s,-s,s)
    glVertex3f(s,-s,-s); glVertex3f(s,-s,s)
    glVertex3f(s,s,-s); glVertex3f(s,s,s)
    glVertex3f(-s,s,-s); glVertex3f(-s,s,s)
    glEnd()

def draw_boss_geometry(size):
    glPushMatrix()
    glRotatef(time.time()*100,0,1,0)
    glColor3f(1,0,0.5)
    draw_complex_cube(size)
    glRotatef(45,1,1,0)
    glColor3f(1,1,1)
    draw_complex_cube(size*0.7)
    glPopMatrix()

def draw_starfield():
    glBegin(GL_POINTS)
    for p in debris:
        dist = math.sqrt(p[0]**2 + p[1]**2)
        c = 1.0 - (dist/4000.0)
        glColor3f(c,c,c+0.2)
        glVertex3f(p[0], p[1], p[2])
    glEnd()

# ==========================================
# 4. UI & TEXT RENDERING
# ==========================================

def draw_text_stat(x,y,text,color=(1,1,1)):
    glColor3f(*color)
    glMatrixMode(GL_PROJECTION)
    glPushMatrix()
    glLoadIdentity()
    gluOrtho2D(0,1000,0,800)
    glMatrixMode(GL_MODELVIEW)
    glPushMatrix()
    glLoadIdentity()
    glRasterPos2f(x,y)
    for char in text: glutBitmapCharacter(GLUT_BITMAP_HELVETICA_18, ord(char))
    glPopMatrix()
    glMatrixMode(GL_PROJECTION)
    glPopMatrix()
    glMatrixMode(GL_MODELVIEW)

def draw_hud():
    global alert_flash
    alert_flash += 0.1
    glColor3f(0.1,0.1,0.1)
    glBegin(GL_QUADS)
    glVertex2f(20,750); glVertex2f(220,750); glVertex2f(220,770); glVertex2f(20,770)
    glEnd()
    col = (0,1,0.2) if diamond_health>40 else (1,0,0)
    glColor3f(*col)
    glBegin(GL_QUADS)
    w=(diamond_health/100.0)*200
    glVertex2f(20,750); glVertex2f(20+w,750); glVertex2f(20+w,770); glVertex2f(20,770)
    glEnd()
    draw_text_stat(20,775,f"CORE INTEGRITY: {int(diamond_health)}%")
    draw_text_stat(20,720,f"PULSE: {int(pulse_charge)}%",(0,0.8,1))
    draw_text_stat(800,760,f"SCORE: {score}",(1,1,0))
    draw_text_stat(800,730,f"LEVEL: {level}")
    intruders=[t for t in thieves if math.sqrt(t.x**2+t.y**2)<PRISM_SHIELD_RAD]
    if len(intruders)>1:
        flash_val=(math.sin(alert_flash*2)+1)/2
        draw_text_stat(380,680,"!!! PROXIMITY ALERT: MULTIPLE INTRUDERS !!!",(1,flash_val,0))
        draw_text_stat(420,650,f"BREACH COUNT: {len(intruders)}",(1,0,0))
    if cheat_mode: draw_text_stat(400,760,"TARGETING OVERRIDE: ACTIVE",(0,1,0))

# ==========================================
# 5. CORE LOOP
# ==========================================

def spawn_particles(x,y,z,color,count=20,s=1.0):
    for _ in range(count): particles.append(Particle(x,y,z,color,s))

def update_game():
    global score,pulse_charge,level,wave_timer,boss_active,last_shot_time,drone_angle
    if is_home_page_running or gameover or game_paused: return
    wave_timer+=1
    if wave_timer%1500==0:
        level+=1
        thieves.append(Thief(is_heavy=True))
    if level%3==0 and not boss_active:
        thieves.append(Thief(is_boss=True))
        boss_active=True
    if pulse_charge<100: pulse_charge+=0.12
    if cheat_mode and time.time()-last_shot_time>0.25:
        if thieves:
            target=min(thieves,key=lambda e: math.sqrt((e.x-drone_pos[0])**2+(e.y-drone_pos[1])**2))
            drone_angle=math.degrees(math.atan2(target.y-drone_pos[1],target.x-drone_pos[0]))
            bullets.append(Bullet(drone_pos[0],drone_pos[1],drone_pos[2],drone_angle))
            last_shot_time=time.time()
    for t in thieves: t.move()
    for b in bullets:
        b.update()
        for t in thieves:
            if math.sqrt((b.x-t.x)**2+(b.y-t.y)**2)<t.size:
                t.hp-=1
                b.active=False
                spawn_particles(b.x,b.y,b.z,(1,0.8,0),5)
                if t.hp<=0:
                    score+=100 if t.is_boss else (40 if t.is_heavy else 10)
                    spawn_particles(t.x,t.y,t.z,(1,0,0),30,2.0)
                    if t.is_boss: boss_active=False
                    thieves.remove(t)
                    if len(thieves)<4: thieves.append(Thief())
    bullets[:] = [b for b in bullets if b.active]
    particles[:] = [p for p in particles if p.update()]

def keyboardListener(key,x,y):
    global drone_angle,cheat_mode,cheat_vision,gameover,diamond_health,score,game_paused,pulse_charge
    try:k=key.decode().lower()
    except:return
    if k=='p': game_paused=not game_paused
    if k=='c': cheat_mode=not cheat_mode
    if k=='v': cheat_vision=not cheat_vision
    if not gameover and not game_paused:
        rad=math.radians(drone_angle)
        if k=='w': drone_pos[0]+=math.cos(rad)*drone_speed; drone_pos[1]+=math.sin(rad)*drone_speed
        if k=='s': drone_pos[0]-=math.cos(rad)*drone_speed; drone_pos[1]-=math.sin(rad)*drone_speed
        if k=='a': drone_angle+=8
        if k=='d': drone_angle-=8
        if k==' ' and pulse_charge>=100:
            spawn_particles(0,0,0,(0,1,1),100,4.0)
            for t in thieves[:]:
                if math.sqrt(t.x**2+t.y**2)<PRISM_SHIELD_RAD+200:
                    if not t.is_boss: thieves.remove(t); score+=5; thieves.append(Thief())
                    else: t.hp-=5
            pulse_charge=0
    if k=='r' and gameover:
        diamond_health,score,gameover,level=100,0,False,1
        bullets.clear()
        thieves[:]=[Thief() for _ in range(5)]

def specialKeyListener(key,x,y):
    global cam_offset
    if key==GLUT_KEY_UP: cam_offset[1]+=50
    if key==GLUT_KEY_DOWN: cam_offset[1]-=50
    if key==GLUT_KEY_LEFT: cam_offset[0]-=50
    if key==GLUT_KEY_RIGHT: cam_offset[0]+=50

def mouseListener(button,state,x,y):
    global is_home_page_running,cam_zoom
    if button==3: cam_zoom-=60
    if button==4: cam_zoom+=60
    if button==GLUT_LEFT_BUTTON and state==GLUT_DOWN:
        if is_home_page_running: is_home_page_running=False
        elif not gameover: bullets.append(Bullet(drone_pos[0],drone_pos[1],drone_pos[2],drone_angle))

def draw_diamond_core():
    t=time.time()
    glPushMatrix()
    glTranslatef(0,0,70+math.sin(t*3)*15)
    glRotatef(t*90,0,0,1)
    size=50
    glBegin(GL_LINES)
    for i in range(8):
        a1=i*(math.pi/4)
        glColor3f(0,1,1)
        glVertex3f(0,0,size); glVertex3f(math.cos(a1)*size,math.sin(a1)*size,0)
        glColor3f(0,0.5,1)
        glVertex3f(0,0,-size); glVertex3f(math.cos(a1)*size,math.sin(a1)*size,0)
    glEnd()
    glPopMatrix()

def showScreen():
    glClear(GL_COLOR_BUFFER_BIT|GL_DEPTH_BUFFER_BIT)
    glLoadIdentity()
    if cheat_vision:
        rad=math.radians(drone_angle)
        gluLookAt(drone_pos[0],drone_pos[1],drone_pos[2]+20,
                  drone_pos[0]+math.cos(rad)*100,drone_pos[1]+math.sin(rad)*100,40,
                  0,0,1)
    else:
        global shake_amount
        sx,sy=random.uniform(-shake_amount,shake_amount),random.uniform(-shake_amount,shake_amount)
        if shake_amount>0: shake_amount*=0.85
        gluLookAt(cam_offset[0]+sx,cam_offset[1]+sy,cam_zoom,0,0,0,0,0,1)
    draw_starfield()
    if is_home_page_running:
        draw_text_stat(350,450,"PRISM PROTECTOR: ULTRA",(0,1,1))
        draw_text_stat(380,410,"CLICK TO START SYSTEM",(1,1,1))
    else:
        glBegin(GL_LINES)
        glColor3f(0,0.1,0.3)
        for i in range(-ARENA_LIMIT,ARENA_LIMIT+1,100):
            glVertex3f(i,-ARENA_LIMIT,0); glVertex3f(i,ARENA_LIMIT,0)
            glVertex3f(-ARENA_LIMIT,i,0); glVertex3f(ARENA_LIMIT,i,0)
        glEnd()
        draw_prism_boundary()
        draw_diamond_core()
        glPushMatrix()
        glTranslatef(*drone_pos)
        glRotatef(drone_angle,0,0,1)
        glColor3f(0.5,0.5,0.6)
        draw_complex_cube(20)
        glColor3f(1,1,0)
        glBegin(GL_LINES); glVertex3f(0,0,0); glVertex3f(40,0,0); glEnd()
        glPopMatrix()
        for t in thieves:
            glPushMatrix()
            glTranslatef(t.x,t.y,t.z)
            if t.is_boss: draw_boss_geometry(t.size)
            elif t.is_heavy: glColor3f(0.7,0,1); draw_complex_cube(t.size)
            else: glColor3f(1,0.2,0.2); draw_complex_cube(t.size)
            glPopMatrix()
        glBegin(GL_POINTS)
        for p in particles: glColor3f(p.color[0],p.color[1],p.color[2]); glVertex3f(p.x,p.y,p.z)
        glEnd()
        glBegin(GL_LINES)
        for b in bullets:
            glColor3f(*b.color)
            glVertex3f(b.x,b.y,b.z)
            glVertex3f(b.x-b.vx*1.5,b.y-b.vy*1.5,b.z)
        glEnd()
    draw_hud()
    if gameover:
        draw_text_stat(420,400,"MISSION FAILED",(1,0,0))
        draw_text_stat(410,370,"PRESS R TO REBOOT",(1,1,0))
    glutSwapBuffers()

def main():
    glutInit()
    glutInitDisplayMode(GLUT_DOUBLE|GLUT_RGB|GLUT_DEPTH)
    glutInitWindowSize(screen_w,screen_h)
    glutCreateWindow(b"Prism Protector Ultra")
    glEnable(GL_DEPTH_TEST)
    glMatrixMode(GL_PROJECTION)
    gluPerspective(45,screen_w/screen_h,10,10000)
    glMatrixMode(GL_MODELVIEW)
    glutDisplayFunc(showScreen)
    glutIdleFunc(animate)
    glutKeyboardFunc(keyboardListener)
    glutSpecialFunc(specialKeyListener)
    glutMouseFunc(mouseListener)
    glutMainLoop()

def animate():
    update_game()
    glutPostRedisplay()

if __name__=="__main__":
    main()
