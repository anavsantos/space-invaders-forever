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
  body {
    background:#000;
    display:flex; flex-direction:column; align-items:center; justify-content:center;
    height:100vh; font-family:'Courier New',monospace; color:#0f0;
    user-select:none;
  }
  canvas { border:2px solid #0f0; display:block; outline:none; }
  #ui {
    width:600px; display:flex; justify-content:space-between;
    padding:4px 0; font-size:14px;
  }
  #gameWrap { position:relative; }

  /* ── Overlay ── */
  #overlay {
    position:absolute; inset:0;
    display:flex; flex-direction:column; align-items:center; justify-content:center;
    background:rgba(0,0,0,0.82);
    z-index:10;
  }
  #overlay h1  { font-size:38px; text-shadow:0 0 12px #0f0; letter-spacing:4px; }
  #overlay p   { font-size:15px; margin-top:10px; text-align:center; line-height:1.7; }
  #overlay .sub { font-size:13px; color:#0a0; margin-top:6px; }
  #startBtn {
    margin-top:22px; padding:12px 36px;
    background:#0f0; color:#000;
    border:none; font-family:'Courier New',monospace;
    font-size:17px; font-weight:bold;
    cursor:pointer; border-radius:4px;
    box-shadow:0 0 14px #0f0;
  }
  #startBtn:hover { background:#3f3; }

  /* ── On-screen controls (touch / mouse) ── */
  #controls {
    width:600px; display:flex; justify-content:space-between;
    align-items:center; padding:6px 0;
  }
  .ctrl-btn {
    padding:8px 22px; background:#111; color:#0f0;
    border:1px solid #0f0; font-family:'Courier New',monospace;
    font-size:18px; cursor:pointer; border-radius:4px;
    touch-action:none; -webkit-tap-highlight-color:transparent;
  }
  .ctrl-btn:active { background:#030; }
  #fireBtn { background:#050; border-color:#0f0; font-size:14px; padding:8px 16px; }
</style>
</head>
<body>

<div id="ui">
  <span>SCORE: <span id="scoreVal">0</span></span>
  <span>LEVEL: <span id="levelVal">1</span></span>
  <span>LIVES: <span id="livesVal">3</span></span>
  <span>HI-SCORE: <span id="hiVal">0</span></span>
</div>

<div id="gameWrap">
  <canvas id="c" width="600" height="520" tabindex="0"></canvas>

  <div id="overlay">
    <h1>SPACE INVADERS</h1>
    <p>← → to move &nbsp;|&nbsp; SPACE / ↑ to shoot</p>
    <p class="sub">or use the buttons below</p>
    <button id="startBtn">&#9654; START GAME</button>
  </div>
</div>

<div id="controls">
  <button class="ctrl-btn" id="btnLeft">&#9664; LEFT</button>
  <button class="ctrl-btn" id="fireBtn">&#128165; FIRE</button>
  <button class="ctrl-btn" id="btnRight">RIGHT &#9654;</button>
</div>

<script>
// ── Canvas / ctx ──────────────────────────────────────────────────────────────
const canvas  = document.getElementById('c');
const ctx     = canvas.getContext('2d');
const W = canvas.width, H = canvas.height;

// ── UI refs ───────────────────────────────────────────────────────────────────
const scoreEl   = document.getElementById('scoreVal');
const levelEl   = document.getElementById('levelVal');
const livesEl   = document.getElementById('livesVal');
const hiEl      = document.getElementById('hiVal');
const overlay   = document.getElementById('overlay');
const startBtn  = document.getElementById('startBtn');
const overlayH1 = overlay.querySelector('h1');
const overlayP  = overlay.querySelector('p');

// ── Constants ─────────────────────────────────────────────────────────────────
const COLS=11, ROWS=5;
const ALIEN_W=32, ALIEN_H=24, ALIEN_PAD_X=12, ALIEN_PAD_Y=14;
const PLAYER_W=44, PLAYER_H=20;
const BULLET_W=3,  BULLET_H=10;
const SHIELD_COLS=11, SHIELD_CELL=5;

// ── Input state ───────────────────────────────────────────────────────────────
const keys = {};
let touchLeft=false, touchRight=false, touchFire=false;

// ── Pixel-art sprites (11×8) ──────────────────────────────────────────────────
const SPRITES = {
  squid:[
    [0,0,0,1,1,1,1,0,0,0,0],[0,1,1,1,1,1,1,1,1,0,0],
    [1,1,0,1,1,1,1,0,1,1,0],[1,1,1,1,1,1,1,1,1,1,0],
    [0,0,1,1,0,0,1,1,0,0,0],[0,1,1,0,1,1,0,1,1,0,0],
    [1,1,0,0,0,0,0,0,1,1,0],[0,1,0,0,0,0,0,0,0,1,0],
  ],
  crab:[
    [0,0,1,0,0,0,0,0,1,0,0],[0,0,0,1,0,0,0,1,0,0,0],
    [0,0,1,1,1,1,1,1,1,0,0],[0,1,1,0,1,1,1,0,1,1,0],
    [1,1,1,1,1,1,1,1,1,1,1],[1,0,1,1,1,1,1,1,1,0,1],
    [1,0,1,0,0,0,0,0,1,0,1],[0,0,0,1,1,0,1,1,0,0,0],
  ],
  octopus:[
    [0,0,0,1,1,1,1,0,0,0,0],[0,1,1,1,1,1,1,1,1,0,0],
    [1,1,0,1,1,1,1,0,1,1,0],[1,1,1,1,1,1,1,1,1,1,0],
    [0,1,1,1,0,0,1,1,1,0,0],[0,0,0,1,0,0,0,1,0,0,0],
    [0,0,1,0,1,0,1,0,1,0,0],[0,1,0,1,0,0,0,1,0,1,0],
  ],
};
const SPRITES_ALT = {
  squid:   SPRITES.squid.map((r,i)   => i===7 ? [1,0,0,0,0,0,0,0,0,0,1] : r),
  crab:    SPRITES.crab.map((r,i)    => i===0 ? [0,1,0,0,0,0,0,0,0,1,0] : r),
  octopus: SPRITES.octopus.map((r,i) => i===6 ? [0,1,0,0,1,0,1,0,0,1,0] : r),
};

const SHIELD_MASK=[
  [0,0,1,1,1,1,1,1,1,0,0],[0,1,1,1,1,1,1,1,1,1,0],
  [1,1,1,1,1,1,1,1,1,1,1],[1,1,1,1,1,1,1,1,1,1,1],
  [1,1,1,1,1,1,1,1,1,1,1],[1,1,0,0,0,0,0,0,0,1,1],
  [1,1,0,0,0,0,0,0,0,1,1],
];

// ── Game state ────────────────────────────────────────────────────────────────
let gameState='title';
let score, hiScore=0, lives, level;
let player, bullets, alienBullets, aliens, shields, ufo;
let alienDir, alienShootTimer, explosions, frame;

function alienType(r)  { return r===0?'squid': r<=2?'crab':'octopus'; }
function alienColor(r) { return r===0?'#ff0' : r<=2?'#0ff':'#f0f'; }
function alienPts(r)   { return r===0?30      : r<=2?20   :10; }

function buildShields() {
  const out=[], count=4;
  const totalW = count*SHIELD_COLS*SHIELD_CELL + (count-1)*40;
  let sx = (W-totalW)/2;
  for(let s=0;s<count;s++){
    const cells=[];
    for(let r=0;r<SHIELD_MASK.length;r++)
      for(let c=0;c<SHIELD_COLS;c++)
        if(SHIELD_MASK[r][c]) cells.push({x:sx+c*SHIELD_CELL, y:H-90+r*SHIELD_CELL, alive:true});
    out.push(cells);
    sx += SHIELD_COLS*SHIELD_CELL+40;
  }
  return out;
}

function init(keepScore=false){
  if(!keepScore){ score=0; lives=3; level=1; }
  frame=0; explosions=[];
  player={x:W/2-PLAYER_W/2, y:H-40, cooldown:0};
  bullets=[]; alienBullets=[];
  alienDir=1; alienShootTimer=60; ufo=null;
  aliens=[];
  for(let row=0;row<ROWS;row++)
    for(let col=0;col<COLS;col++)
      aliens.push({row,col,
        x:40+col*(ALIEN_W+ALIEN_PAD_X), y:60+row*(ALIEN_H+ALIEN_PAD_Y),
        alive:true, anim:0,
        type:alienType(row), color:alienColor(row), points:alienPts(row)});
  shields=buildShields();
  updateUI();
}

function updateUI(){
  scoreEl.textContent=score; levelEl.textContent=level;
  livesEl.textContent=lives; hiEl.textContent=hiScore;
}

// ── Helpers ───────────────────────────────────────────────────────────────────
function overlap(ax,ay,aw,ah, bx,by,bw,bh){
  return ax<bx+bw && ax+aw>bx && ay<by+bh && ay+ah>by;
}
function hitShield(bx,by,bw,bh){
  for(const s of shields) for(const c of s)
    if(c.alive && overlap(bx,by,bw,bh, c.x,c.y,SHIELD_CELL,SHIELD_CELL)){
      c.alive=false; return true;
    }
  return false;
}
function boom(x,y,color){ explosions.push({x,y,color,ttl:20}); }

// ── Drawing ───────────────────────────────────────────────────────────────────
function drawSprite(sp,x,y,sc,color){
  ctx.fillStyle=color;
  for(let r=0;r<sp.length;r++) for(let c=0;c<sp[r].length;c++)
    if(sp[r][c]) ctx.fillRect(x+c*sc, y+r*sc, sc, sc);
}
function drawPlayer(){
  ctx.fillStyle='#0f0';
  ctx.fillRect(player.x+14, player.y,    16,4);
  ctx.fillRect(player.x+6,  player.y+4,  32,8);
  ctx.fillRect(player.x,    player.y+12, PLAYER_W,8);
  ctx.fillRect(player.x+20, player.y-6,  4,8);
}
function drawShields(){
  ctx.fillStyle='#0f0';
  shields.forEach(s=>s.forEach(c=>{ if(c.alive) ctx.fillRect(c.x,c.y,SHIELD_CELL,SHIELD_CELL); }));
}
function drawUFO(){
  if(!ufo) return;
  ctx.fillStyle='#f00';
  ctx.fillRect(ufo.x+10,ufo.y,   30,6);
  ctx.fillRect(ufo.x+4, ufo.y+6, 42,8);
  ctx.fillRect(ufo.x,   ufo.y+14,50,8);
  ctx.fillStyle='#fff';
  [8,20,32].forEach(ox=>ctx.fillRect(ufo.x+ox,ufo.y+6,4,6));
  ctx.fillStyle='#f00';
  ctx.font='bold 11px Courier New';
  ctx.fillText('???', ufo.x+14, ufo.y-4);
}

// ── Update ────────────────────────────────────────────────────────────────────
function update(){
  if(gameState!=='playing') return;
  frame++;

  // movement
  const goLeft  = keys['ArrowLeft']  || keys['a'] || touchLeft;
  const goRight = keys['ArrowRight'] || keys['d'] || touchRight;
  const shoot   = keys[' '] || keys['ArrowUp'] || keys['w'] || touchFire;
  if(goLeft)  player.x = Math.max(0, player.x-4);
  if(goRight) player.x = Math.min(W-PLAYER_W, player.x+4);
  if(player.cooldown>0) player.cooldown--;

  // shoot
  if(shoot && player.cooldown===0 && bullets.filter(b=>b.owner==='player').length<1){
    bullets.push({x:player.x+PLAYER_W/2-BULLET_W/2, y:player.y-BULLET_H, dy:-9, owner:'player'});
    player.cooldown=15;
    touchFire=false;
  }

  // UFO
  if(!ufo && Math.random()<0.001) ufo={x:-55,y:20,speed:2};
  if(ufo){ ufo.x+=ufo.speed; if(ufo.x>W+60) ufo=null; }

  // aliens march
  const alive=aliens.filter(a=>a.alive);
  const interval=Math.max(4, Math.floor(60-alive.length*1.1));
  if(frame%interval===0){
    let wall=false;
    alive.forEach(a=>{ a.x+=alienDir*(6+level); a.anim^=1; if(a.x<=0||a.x+ALIEN_W>=W) wall=true; });
    if(wall){ alienDir*=-1; alive.forEach(a=>a.y+=14); }
  }

  // alien shoot
  if(--alienShootTimer<=0){
    alienShootTimer=Math.max(20,60-level*5)+Math.random()*30;
    if(alive.length){
      const s=alive[Math.floor(Math.random()*alive.length)];
      alienBullets.push({x:s.x+ALIEN_W/2-2, y:s.y+ALIEN_H, dy:4+level*0.5, owner:'alien'});
    }
  }

  // move bullets
  bullets=bullets.filter(b=>{ b.y+=b.dy; return b.y>-20&&b.y<H+20; });
  alienBullets=alienBullets.filter(b=>{ b.y+=b.dy; return b.y<H+20; });

  // player bullets hit
  bullets.forEach(b=>{
    if(b.owner!=='player') return;
    if(ufo && overlap(b.x,b.y,BULLET_W,BULLET_H, ufo.x,ufo.y,50,22)){
      score+=[50,100,150,200,300][Math.floor(Math.random()*5)];
      if(score>hiScore) hiScore=score;
      boom(ufo.x+25,ufo.y+11,'#f00'); ufo=null; b.y=-999; updateUI(); return;
    }
    for(const a of aliens){
      if(!a.alive) continue;
      if(overlap(b.x,b.y,BULLET_W,BULLET_H, a.x,a.y,ALIEN_W,ALIEN_H)){
        a.alive=false; score+=a.points;
        if(score>hiScore) hiScore=score;
        boom(a.x+ALIEN_W/2,a.y+ALIEN_H/2,a.color);
        b.y=-999; updateUI(); break;
      }
    }
    if(b.y>-999) hitShield(b.x,b.y,BULLET_W,BULLET_H);
  });

  // alien bullets hit
  alienBullets.forEach(b=>{
    if(hitShield(b.x,b.y,4,BULLET_H)){ b.y=H+999; return; }
    if(overlap(b.x,b.y,4,BULLET_H, player.x,player.y,PLAYER_W,PLAYER_H)){
      boom(player.x+PLAYER_W/2,player.y+PLAYER_H/2,'#0f0');
      b.y=H+999; lives--; updateUI();
      if(lives<=0){ gameState='over'; showOverlay('GAME OVER','The invaders won — try again!'); return; }
      gameState='dead';
      setTimeout(()=>{ if(gameState==='dead') gameState='playing'; },1200);
    }
  });

  // aliens reach ground?
  for(const a of aliens)
    if(a.alive && a.y+ALIEN_H>=H-50){ gameState='over'; showOverlay('GAME OVER','They landed… try again!'); return; }

  // all dead → next level
  if(aliens.every(a=>!a.alive)){ level++; updateUI(); init(true); }

  // explosions
  explosions=explosions.filter(e=>{ e.ttl--; return e.ttl>0; });
}

// ── Draw ──────────────────────────────────────────────────────────────────────
function draw(){
  ctx.fillStyle='#000';
  ctx.fillRect(0,0,W,H);
  ctx.fillStyle='#0f0';
  ctx.fillRect(0,H-30,W,2);   // ground line

  if(gameState==='title') return;

  drawPlayer();
  drawShields();
  drawUFO();

  aliens.forEach(a=>{
    if(!a.alive) return;
    const sp=(a.anim===0?SPRITES:SPRITES_ALT)[a.type];
    drawSprite(sp,a.x,a.y,3,a.color);
  });

  ctx.fillStyle='#fff';
  bullets.forEach(b=>ctx.fillRect(b.x,b.y,BULLET_W,BULLET_H));

  ctx.fillStyle='#f88';
  alienBullets.forEach(b=>{
    ctx.fillRect(b.x,  b.y,   3,4);
    ctx.fillRect(b.x+3,b.y+4, 3,4);
    ctx.fillRect(b.x,  b.y+8, 3,4);
  });

  explosions.forEach(e=>{
    const r=(20-e.ttl)*1.5;
    ctx.strokeStyle=e.color; ctx.lineWidth=2;
    ctx.beginPath(); ctx.arc(e.x,e.y,r,0,Math.PI*2); ctx.stroke();
    for(let i=0;i<6;i++){
      const a=(i/6)*Math.PI*2;
      ctx.beginPath(); ctx.moveTo(e.x,e.y);
      ctx.lineTo(e.x+Math.cos(a)*r*1.5, e.y+Math.sin(a)*r*1.5); ctx.stroke();
    }
  });
}

// ── Overlay ───────────────────────────────────────────────────────────────────
function showOverlay(title, sub){
  overlayH1.textContent = title;
  overlayP.textContent  = sub;
  startBtn.textContent  = gameState==='title' ? '▶ START GAME' : '▶ PLAY AGAIN';
  overlay.style.display = 'flex';
}
function hideOverlay(){ overlay.style.display='none'; }

function startGame(){
  hideOverlay();
  init(false);
  gameState='playing';
  canvas.focus();
}

// ── Input wiring (NO inline onclick) ─────────────────────────────────────────
startBtn.addEventListener('click', startGame);
startBtn.addEventListener('touchend', function(e){ e.preventDefault(); startGame(); });

document.addEventListener('keydown', e=>{
  keys[e.key]=true;
  if(e.key===' '||e.key==='Enter'){
    e.preventDefault();
    if(gameState==='title'||gameState==='over') startGame();
  }
  if(['ArrowLeft','ArrowRight','ArrowUp',' '].includes(e.key)) e.preventDefault();
});
document.addEventListener('keyup', e=>{ keys[e.key]=false; });

// On-screen buttons (mousedown/up + touch)
function holdBtn(flagSetter, val){
  return function(e){ e.preventDefault(); flagSetter(val); };
}
const btnLeft  = document.getElementById('btnLeft');
const btnRight = document.getElementById('btnRight');
const fireBtn  = document.getElementById('fireBtn');

['mousedown','touchstart'].forEach(ev=>{
  btnLeft.addEventListener( ev, e=>{ e.preventDefault(); touchLeft=true;  });
  btnRight.addEventListener(ev, e=>{ e.preventDefault(); touchRight=true; });
  fireBtn.addEventListener( ev, e=>{ e.preventDefault(); touchFire=true;  });
});
['mouseup','touchend','mouseleave','touchcancel'].forEach(ev=>{
  btnLeft.addEventListener( ev, e=>{ e.preventDefault(); touchLeft=false;  });
  btnRight.addEventListener(ev, e=>{ e.preventDefault(); touchRight=false; });
  fireBtn.addEventListener( ev, e=>{ e.preventDefault(); touchFire=false;  if(gameState==='playing') touchFire=true; touchFire=false; });
});

// Click anywhere on canvas keeps keyboard focus
canvas.addEventListener('click', ()=>canvas.focus());

// Auto-focus so keyboard works right away
setTimeout(()=>canvas.focus(), 400);

// ── Game loop ─────────────────────────────────────────────────────────────────
init();
function loop(){ update(); draw(); requestAnimationFrame(loop); }
loop();
</script>
</body>
</html>
"""

components.html(GAME_HTML, height=680, scrolling=False)
