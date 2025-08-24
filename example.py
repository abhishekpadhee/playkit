# First Space Game (simple & kid-friendly)
# Arrows = move   Space = shoot

import playkit, random

def setup():
    global player, bullets, rocks, score, timer
    player = playkit.sprite(x=300, y=430, width=40, height=40, color=(0,200,255))
    playkit.control_arrows(player, speed=220, bounds=(0,0,640,480))

    bullets = []   # all player bullets
    rocks   = []   # all falling rocks
    score   = 0
    timer   = 0.0  # spawns a rock every 1 second

playkit.on_game_start(setup)

def shoot():
    b = playkit.projectile_from(player, 0, -450, width=6, height=14,
                                color=(255,255,0), lifetime=2)
    bullets.append(b)

playkit.when_key('space', shoot)

def step(dt):
    global timer, score
    # spawn new rock every 1 second
    timer += dt
    if timer >= 1.0:
        timer = 0.0
        r = playkit.sprite(x=random.randint(0, 620), y=-30, width=26, height=26,
                           color=(180,180,180), speed=(0,170), lifetime=6)
        rocks.append(r)

    # collisions (no None checks, just skip dead ones)
    for r in rocks:
        if not r.alive: 
            continue
        if r.rect.colliderect(player.rect):
            playkit.game_over("You Lose!")
        for b in bullets:
            if not b.alive:
                continue
            if b.rect.colliderect(r.rect):
                score += 1
                r.destroy()
                b.destroy()
                break

    playkit.write(f"Score: {score}", 10, 10, size=24)

playkit.on_game_update(step)
playkit.start(640, 480, "First Space Game")

