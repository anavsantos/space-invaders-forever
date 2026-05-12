import streamlit as st
import streamlit.components.v1 as components

st.set_page_config(page_title="Space Invaders", layout="wide", initial_sidebar_state="collapsed")

st.markdown(
    """
    <style>
        body, .stApp { background-color: #000; }
        header, footer { visibility: hidden; }
        .block-container { padding: 0 !important; }
    </style>
    """,
    unsafe_allow_html=True,
)

GAME_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"/>
<style>
  * { margin:0; padding:0; box-sizing:border-box; }
  body { background:#000; display:flex; flex-direction:column; align-items:center; justify-content:center; height:100vh; font-family:'Courier New',monospace; color:#0f0; }
  canvas { border:2px solid #0f0; display:block; }
  #ui { width:600px; display:flex; justify-content:space-between; padding:4px 0; font-size:14px; }
  #overlay { position:absolute; top:50%; left:50%; transform:translate(-50%,-50%);
             text-align:center; color:#0f0; font-family:'Courier New',monospace; pointer-events:none; }
  #overlay h1 { font-size:36px; text-shadow:0 0 10px #0f0; }
  #overlay p  { font-size:16px; margin-top:8px; }
</style>
</head>
<body>
<div id="ui">
  <span>SCORE: <span id="scoreVal">0</span></span>
  <span>LEVEL: <span id="levelVal">1</span></span>
  <span>LIVES: <span id="livesVal">3</span></span>
  <span>HI-SCORE: <span id="hiVal">0</span></span>
</div>
<div style="position:relative">
  <canvas id="c" width="600" height="520"></canvas>
  <div id="overlay">
    <h1>SPACE INVADERS</h1>
    <p>← → to move &nbsp;|&nbsp; SPACE to shoot<br>Press SPACE or click to start</p>
  </div>
</div>

<script>
const canvas = document.getElementById('c');
const ctx    = canvas.getContext('2d');
const W = canvas.width, H = canvas.height;

// ── UI refs ──────────────────────────────────────────────────────────────────
const scoreEl = document.getElementById('scoreVal');
const levelEl = document.getElementById('levelVal');
const livesEl = document.getElementById('livesVal');
const hiEl    = document.getElementById('hiVal');
const overlay = document.getElementById('overlay');

// ── State ────────────────────────────────────────────────────────────────────
const COLS = 11, ROWS = 5;
const ALIEN_W = 32, ALIEN_H = 24, ALIEN_PAD_X = 12, ALIEN_PAD_Y = 14;
const PLAYER_W = 44, PLAYER_H = 20;
const BULLET_W = 3, BULLET_H = 10;
const SHIELD_ROWS = 4, SHIELD_COLS = 11;
const SHIELD_CELL = 5;

let state, score, hiScore = 0, lives, level;
let player, bullets, alienBullets, aliens, shields, ufo;
let alienDir, alienStep, alienDropPending, alienShootTimer;
let keys = {};
let frame = 0;

// ── Alien sprite data (3 rows of pixel art each 11×8) ───────────────────────
const SPRITE = {
  squid: [
    [0,0,0,1,1,1,1,0,0,0,0],
    [0,1,1,1,1,1,1,1,1,0,0],
    [1,1,0,1,1,1,1,0,1,1,0],
    [1,1,1,1,1,1,1,1,1,1,0],
    [0,0,1,1,0,0,1,1,0,0,0],
    [0,1,1,0,1,1,0,1,1,0,0],
    [1,1,0,0,0,0,0,0,1,1,0],
    [0,1,0,0,0,0,0,0,0,1,0],
  ],
  crab: [
    [0,0,1,0,0,0,0,0,1,0,0],
    [0,0,0,1,0,0,0,1,0,0,0],
    [0,0,1,1,1,1,1,1,1,0,0],
    [0,1,1,0,1,1,1,0,1,1,0],
    [1,1,1,1,1,1,1,1,1,1,1],
    [1,0,1,1,1,1,1,1,1,0,1],
    [1,0,1,0,0,0,0,0,1,0,1],
    [0,0,0,1,1,0,1,1,0,0,0],
  ],
  octopus: [
    [0,0,0,1,1,1,1,0,0,0,0],
    [0,1,1,1,1,1,1,1,1,0,0],
    [1,1,0,1,1,1,1,0,1,1,0],
    [1,1,1,1,1,1,1,1,1,1,0],
    [0,1,1,1,0,0,1,1,1,0,0],
    [0,0,0,1,0,0,0,1,0,0,0],
    [0,0,1,0,1,0,1,0,1,0,0],
    [0,1,0,1,0,0,0,1,0,1,0],
  ],
};
const ALT_SPRITE = {
  squid: SPRITE.squid.map((r,i)=> i===7 ? [1,0,0,0,0,0,0,0,0,0,1] : r),
  crab:  SPRITE.crab.map((r,i) => i===0 ? [0,1,0,0,0,0,0,0,0,1,0] : r),
  octopus: SPRITE.octopus.map((r,i)=> i===6 ? [0,1,0,0,1,0,1,0,0,1,0] : r),
};

function alienType(row) {
  if (row === 0) return 'squid';
  if (row <= 2)  return 'crab';
  return 'octopus';
}
function alienColor(row) {
  if (row === 0) return '#ff0';
  if (row <= 2)  return '#0ff';
  return '#f0f';
}
function alienPoints(row) {
  if (row === 0) return 30;
  if (row <= 2)  return 20;
  return 10;
}

// ── Shield builder ───────────────────────────────────────────────────────────
const SHIELD_MASK = [
  [0,0,1,1,1,1,1,1,1,0,0],
  [0,1,1,1,1,1,1,1,1,1,0],
  [1,1,1,1,1,1,1,1,1,1,1],
  [1,1,1,1,1,1,1,1,1,1,1],
  [1,1,1,1,1,1,1,1,1,1,1],
  [1,1,0,0,0,0,0,0,0,1,1],
  [1,1,0,0,0,0,0,0,0,1,1],
];

function buildShields() {
  const shields = [];
  const count = 4;
  const totalW = count * SHIELD_COLS * SHIELD_CELL + (count - 1) * 40;
  let sx = (W - totalW) / 2;
  for (let s = 0; s < count; s++) {
    const cells = [];
    for (let r = 0; r < SHIELD_MASK.length; r++) {
      for (let c = 0; c < SHIELD_COLS; c++) {
        if (SHIELD_MASK[r][c]) {
          cells.push({ x: sx + c * SHIELD_CELL, y: H - 90 + r * SHIELD_CELL, alive: true });
        }
      }
    }
    shields.push(cells);
    sx += SHIELD_COLS * SHIELD_CELL + 40;
  }
  return shields;
}

// ── Init ─────────────────────────────────────────────────────────────────────
function init(keepScore = false) {
  if (!keepScore) { score = 0; lives = 3; level = 1; }
  frame = 0;
  player = { x: W / 2 - PLAYER_W / 2, y: H - 40, cooldown: 0 };
  bullets = [];
  alienBullets = [];
  alienDir = 1;
  alienStep = 0;
  alienDropPending = false;
  alienShootTimer = 60;
  ufo = null;

  aliens = [];
  for (let row = 0; row < ROWS; row++) {
    for (let col = 0; col < COLS; col++) {
      aliens.push({
        row, col,
        x: 40 + col * (ALIEN_W + ALIEN_PAD_X),
        y: 60 + row * (ALIEN_H + ALIEN_PAD_Y),
        alive: true,
        anim: 0,
        type: alienType(row),
        color: alienColor(row),
        points: alienPoints(row),
      });
    }
  }
  shields = buildShields();
  updateUI();
}

function updateUI() {
  scoreEl.textContent = score;
  levelEl.textContent = level;
  livesEl.textContent = lives;
  hiEl.textContent    = hiScore;
}

// ── Drawing helpers ──────────────────────────────────────────────────────────
function drawSprite(sprite, x, y, scale, color) {
  ctx.fillStyle = color;
  for (let r = 0; r < sprite.length; r++) {
    for (let c = 0; c < sprite[r].length; c++) {
      if (sprite[r][c]) ctx.fillRect(x + c * scale, y + r * scale, scale, scale);
    }
  }
}

function drawPlayer() {
  ctx.fillStyle = '#0f0';
  // body
  ctx.fillRect(player.x + 14, player.y,     16, 4);
  ctx.fillRect(player.x + 6,  player.y + 4, 32, 8);
  ctx.fillRect(player.x,      player.y + 12, PLAYER_W, 8);
  // cannon
  ctx.fillRect(player.x + 20, player.y - 6, 4, 8);
}

function drawShields() {
  ctx.fillStyle = '#0f0';
  shields.forEach(s => s.forEach(cell => {
    if (cell.alive) ctx.fillRect(cell.x, cell.y, SHIELD_CELL, SHIELD_CELL);
  }));
}

function drawUFO() {
  if (!ufo) return;
  ctx.fillStyle = '#f00';
  ctx.fillRect(ufo.x + 10, ufo.y,      30, 6);
  ctx.fillRect(ufo.x + 4,  ufo.y + 6,  42, 8);
  ctx.fillRect(ufo.x,      ufo.y + 14, 50, 8);
  // windows
  ctx.fillStyle = '#fff';
  [8,20,32].forEach(ox => ctx.fillRect(ufo.x + ox, ufo.y + 6, 4, 6));
}

// ── Collision helpers ────────────────────────────────────────────────────────
function rectsOverlap(ax,ay,aw,ah, bx,by,bw,bh) {
  return ax < bx+bw && ax+aw > bx && ay < by+bh && ay+ah > by;
}

function bulletHitsShield(bx, by, bw, bh) {
  for (const s of shields) {
    for (const cell of s) {
      if (cell.alive && rectsOverlap(bx,by,bw,bh, cell.x,cell.y,SHIELD_CELL,SHIELD_CELL)) {
        cell.alive = false;
        return true;
      }
    }
  }
  return false;
}

// ── UFO ──────────────────────────────────────────────────────────────────────
function trySpawnUFO() {
  if (!ufo && Math.random() < 0.001) {
    ufo = { x: -50, y: 20, speed: 2 };
  }
}

// ── Explosion effect ─────────────────────────────────────────────────────────
let explosions = [];
function addExplosion(x, y, color) {
  explosions.push({ x, y, color, ttl: 20 });
}

// ── Main update ──────────────────────────────────────────────────────────────
let gameState = 'title'; // title | playing | dead | win | over

function update() {
  if (gameState !== 'playing') return;
  frame++;

  // Player movement
  if (keys['ArrowLeft']  || keys['a']) player.x = Math.max(0, player.x - 4);
  if (keys['ArrowRight'] || keys['d']) player.x = Math.min(W - PLAYER_W, player.x + 4);
  if (player.cooldown > 0) player.cooldown--;

  // Player shoot
  if ((keys[' '] || keys['ArrowUp']) && player.cooldown === 0 && bullets.filter(b=>b.owner==='player').length < 1) {
    bullets.push({ x: player.x + PLAYER_W/2 - BULLET_W/2, y: player.y - BULLET_H, dx:0, dy:-9, owner:'player' });
    player.cooldown = 15;
  }

  // UFO
  trySpawnUFO();
  if (ufo) {
    ufo.x += ufo.speed;
    if (ufo.x > W + 60) ufo = null;
  }

  // Alien movement — march every N frames based on alive count
  const aliveCount = aliens.filter(a => a.alive).length;
  const marchInterval = Math.max(4, Math.floor(60 - (COLS*ROWS - aliveCount) * 1.1));
  if (frame % marchInterval === 0) {
    let hitWall = false;
    aliens.forEach(a => {
      if (!a.alive) return;
      a.x += alienDir * (6 + level);
      a.anim ^= 1;
      if (a.x <= 0 || a.x + ALIEN_W >= W) hitWall = true;
    });
    if (hitWall) {
      alienDir *= -1;
      aliens.forEach(a => { if (a.alive) a.y += 14; });
    }
  }

  // Alien shoot
  alienShootTimer--;
  if (alienShootTimer <= 0) {
    alienShootTimer = Math.max(20, 60 - level * 5) + Math.random() * 30;
    const alive = aliens.filter(a => a.alive);
    if (alive.length) {
      const shooter = alive[Math.floor(Math.random() * alive.length)];
      alienBullets.push({ x: shooter.x + ALIEN_W/2 - 2, y: shooter.y + ALIEN_H, dx:0, dy: 4 + level*0.5, owner:'alien' });
    }
  }

  // Move bullets
  bullets = bullets.filter(b => {
    b.x += b.dx; b.y += b.dy;
    return b.y > -20 && b.y < H + 20;
  });
  alienBullets = alienBullets.filter(b => {
    b.x += b.dx; b.y += b.dy;
    return b.y < H + 20;
  });

  // Player bullets vs aliens
  bullets.forEach(b => {
    if (b.owner !== 'player') return;
    // vs UFO
    if (ufo && rectsOverlap(b.x, b.y, BULLET_W, BULLET_H, ufo.x, ufo.y, 50, 22)) {
      const pts = [50,100,150,200,300][Math.floor(Math.random()*5)];
      score += pts;
      addExplosion(ufo.x + 25, ufo.y + 11, '#f00');
      ufo = null;
      b.y = -999;
      updateUI();
      return;
    }
    // vs aliens
    for (const a of aliens) {
      if (!a.alive) continue;
      if (rectsOverlap(b.x, b.y, BULLET_W, BULLET_H, a.x, a.y, ALIEN_W, ALIEN_H)) {
        a.alive = false;
        score += a.points;
        if (score > hiScore) hiScore = score;
        addExplosion(a.x + ALIEN_W/2, a.y + ALIEN_H/2, a.color);
        b.y = -999;
        updateUI();
        break;
      }
    }
    // vs shields
    if (b.y > -999) bulletHitsShield(b.x, b.y, BULLET_W, BULLET_H);
  });

  // Alien bullets vs player & shields
  alienBullets.forEach(b => {
    if (bulletHitsShield(b.x, b.y, 4, BULLET_H)) { b.y = H + 999; return; }
    if (rectsOverlap(b.x, b.y, 4, BULLET_H, player.x, player.y, PLAYER_W, PLAYER_H)) {
      addExplosion(player.x + PLAYER_W/2, player.y + PLAYER_H/2, '#0f0');
      b.y = H + 999;
      lives--;
      updateUI();
      if (lives <= 0) { gameState = 'over'; showOverlay('GAME OVER', 'Press SPACE to restart'); return; }
      gameState = 'dead';
      setTimeout(() => { gameState = 'playing'; }, 1200);
    }
  });

  // Aliens reach bottom?
  for (const a of aliens) {
    if (a.alive && a.y + ALIEN_H >= H - 50) {
      gameState = 'over';
      showOverlay('GAME OVER', 'The invaders won!\nPress SPACE to restart');
      return;
    }
  }

  // All aliens dead → next level
  if (aliens.every(a => !a.alive)) {
    level++;
    updateUI();
    init(true);
  }

  // Explosions
  explosions = explosions.filter(e => { e.ttl--; return e.ttl > 0; });
}

// ── Draw ─────────────────────────────────────────────────────────────────────
function draw() {
  ctx.clearRect(0, 0, W, H);
  ctx.fillStyle = '#000';
  ctx.fillRect(0, 0, W, H);

  // Ground line
  ctx.fillStyle = '#0f0';
  ctx.fillRect(0, H - 30, W, 2);

  if (gameState === 'title') return;

  drawPlayer();
  drawShields();
  drawUFO();

  // Aliens
  aliens.forEach(a => {
    if (!a.alive) return;
    const sp = (a.anim === 0 ? SPRITE : ALT_SPRITE)[a.type];
    drawSprite(sp, a.x, a.y, 3, a.color);
  });

  // Player bullets
  ctx.fillStyle = '#fff';
  bullets.forEach(b => ctx.fillRect(b.x, b.y, BULLET_W, BULLET_H));

  // Alien bullets (zigzag shape)
  ctx.fillStyle = '#f88';
  alienBullets.forEach(b => {
    ctx.fillRect(b.x,   b.y,     3, 4);
    ctx.fillRect(b.x+3, b.y+4,   3, 4);
    ctx.fillRect(b.x,   b.y+8,   3, 4);
  });

  // Explosions
  explosions.forEach(e => {
    const r = (20 - e.ttl) * 1.5;
    ctx.strokeStyle = e.color;
    ctx.lineWidth = 2;
    ctx.beginPath();
    ctx.arc(e.x, e.y, r, 0, Math.PI*2);
    ctx.stroke();
    // star lines
    for (let i = 0; i < 6; i++) {
      const ang = (i / 6) * Math.PI * 2;
      ctx.beginPath();
      ctx.moveTo(e.x, e.y);
      ctx.lineTo(e.x + Math.cos(ang)*r*1.4, e.y + Math.sin(ang)*r*1.4);
      ctx.stroke();
    }
  });

  // UFO score label
  if (ufo) {
    ctx.fillStyle = '#f00';
    ctx.font = 'bold 12px Courier New';
    ctx.fillText('? ? ?', ufo.x + 12, ufo.y - 4);
  }
}

// ── Overlay helper ───────────────────────────────────────────────────────────
function showOverlay(title, sub) {
  overlay.innerHTML = `<h1>${title}</h1><p>${sub}</p>`;
  overlay.style.display = 'block';
}
function hideOverlay() { overlay.style.display = 'none'; }

// ── Input ─────────────────────────────────────────────────────────────────────
document.addEventListener('keydown', e => {
  keys[e.key] = true;
  if (e.key === ' ') {
    e.preventDefault();
    if (gameState === 'title') { hideOverlay(); init(); gameState = 'playing'; }
    else if (gameState === 'over') { hideOverlay(); init(); gameState = 'playing'; }
  }
});
document.addEventListener('keyup', e => { keys[e.key] = false; });
canvas.addEventListener('click', () => {
  if (gameState === 'title') { hideOverlay(); init(); gameState = 'playing'; }
  else if (gameState === 'over') { hideOverlay(); init(); gameState = 'playing'; }
});

// ── Loop ─────────────────────────────────────────────────────────────────────
function loop() {
  update();
  draw();
  requestAnimationFrame(loop);
}

init();
loop();
</script>
</body>
</html>
"""

components.html(GAME_HTML, height=620, scrolling=False)
