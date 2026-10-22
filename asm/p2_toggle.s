; Ship select: Start switches between Bond (Player 1) and Dyne (Player 2). @ 0x0C05B500
; P2 toggle + control swap.  Entered from the control reader (bra at 0x0C060E54 -> stub -> here),
; returns to 0x0C060E58 with r6 = start/coin byte, r4 = P1 port, r1 = P2 port.
INPUT:
  mov.l @PORTC,r2
  mov.b @r2,r6          ; start/coin byte (active low)
  mov.l @STATE,r13
  mov.b @r13,r0         ; r0 = Dyne mode flag
  extu.b r0,r0
  mov.l @SCENE,r10
  mov.b @r10,r3
  extu.b r3,r3
  mov #1,r5
  cmp/hi r5,r3          ; scene > 1 ?
  bt NOTITLE
  mov #1,r0             ; title / attract: treat Start as held (the press that starts
  mov.b r0,@(1,r13)     ; the game must be released before it can toggle)
  mov #0,r0             ; and Dyne mode off
  mov.b r0,@r13
NOTITLE:
  mov #2,r5
  cmp/eq r5,r3          ; ship select?
  bf PORTS
  mov.l @MASK,r11
  mov.b @r11,r12
  extu.b r12,r12
  mov r0,r5
  add #1,r5
  cmp/eq r5,r12         ; the only player is the one on the P1 controls?
  bf PORTS
  mov r6,r0
  tst #16,r0            ; physical P1 Start pressed (bit low)?
  movt r4
  mov.b @(1,r13),r0     ; previous state
  mov r0,r5
  mov r4,r0
  mov.b r0,@(1,r13)
  mov r6,r0
  or #16,r0             ; the game never sees this Start press
  mov r0,r6
  tst r4,r4
  bt RELOAD
  tst r5,r5
  bf RELOAD             ; still held from last frame
  mov.l @P1BASE,r2      ; --- toggle: swap the two player blocks ---
  mov.l @P2BASE,r3
  mov #84,r5
  add r5,r5             ; 168 longs = 0x2A0 bytes
LOOP:
  mov.l @r2,r4
  mov.l @r3,r8
  mov.l r8,@r2
  mov.l r4,@r3
  add #4,r2
  add #4,r3
  dt r5
  bf LOOP
  mov.l @P1BASE,r2      ; each side keeps its own pilot (Bond / Dyne)
  mov.b @(7,r2),r0
  and #0xF7,r0
  mov.b r0,@(7,r2)
  mov.l @P2BASE,r3
  mov.b @(7,r3),r0
  or #8,r0
  mov.b r0,@(7,r3)
  mov.b @r11,r0         ; active players 1 <-> 2
  xor #3,r0
  mov.b r0,@r11
  mov.b @r13,r0         ; Dyne mode flag
  xor #1,r0
  mov.b r0,@r13
RELOAD:
  mov.b @r13,r0
  extu.b r0,r0
PORTS:
  tst r0,r0
  bf DYNE
  mov.l @P1PORT,r4
  mov.l @P2PORT,r1
  bra OUT
  nop
DYNE:
  mov.l @P2PORT,r4      ; P1 controls drive the P2 side and vice versa
  mov.l @P1PORT,r1
  mov r6,r0             ; swap the two Start bits
  and #48,r0
  cmp/eq #0,r0
  bt OUT
  cmp/eq #48,r0
  bt OUT
  mov r6,r0
  xor #48,r0
  mov r0,r6
OUT:
  mov.l @RET,r0
  jmp @r0
  nop
  .align 4
PORTC: .long 0xA4000124
STATE: .long 0x0C05B4F0
SCENE: .long 0x0C2289ED
MASK: .long 0x0C239497
P1BASE: .long 0x0C29D1D8
P2BASE: .long 0x0C29D478
P1PORT: .long 0xA4000126
P2PORT: .long 0xA4000134
RET: .long 0x0C060E58
