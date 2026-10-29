; Ship select: Start switches between Bond (Player 1) and Dyne (Player 2).  @ 0x0C05B500
; Entered from the control reader (bra at 0x0C060E54 -> stub 0x0C060DD4 -> here), returns to
; 0x0C060E58 with r6 = start/coin byte, r4 = P1 port address, r1 = P2 port address.
; State at 0x0C05B4F0: +0 Dyne mode flag, +1 Start held last frame, +2 "select active" frames
; (set to 3 every frame by the ship-select hook, see select_mark.s).
INPUT:
  mov.l @PORTC,r2
  mov.b @r2,r6          ; start/coin byte (active low)
  mov.l @STATE,r13
  mov.l @MODE,r2        ; in a game (play, continue, name entry: mode 6) or on the
  mov.b @r2,r0          ; ship select?
  cmp/eq #6,r0
  bt PLAYING
  mov.b @(2,r13),r0
  tst r0,r0
  bf PLAYING
  mov #0,r0             ; title, attract, test mode: normal controls (Dyne mode itself
  bra PORTS             ; is switched off when a new game starts, see new_game.s)
  nop
PLAYING:
  mov.b @(2,r13),r0     ; ship select active?
  extu.b r0,r0
  tst r0,r0
  bt PORTS0
  add #-1,r0
  mov.b r0,@(2,r13)
  mov.b @r13,r0         ; r0 = Dyne mode flag
  extu.b r0,r0
  mov.l @MASK,r11
  mov.b @r11,r12        ; players choosing a ship: 1 = P1 side, 2 = P2 side
  extu.b r12,r12
  mov r0,r5
  add #1,r5
  cmp/eq r5,r12         ; the only player is the one on the Player 1 controls?
  bf PORTS
  mov r6,r0
  tst #16,r0            ; physical P1 Start pressed (bit low)?
  movt r4
  mov.b @(1,r13),r0
  mov r0,r5             ; held last frame?
  mov r4,r0
  mov.b r0,@(1,r13)
  mov r6,r0
  or #16,r0             ; the game never sees this Start press
  mov r0,r6
  tst r4,r4
  bt RELOAD
  tst r5,r5
  bf RELOAD
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
  mov.b @r11,r0         ; choosing side 1 <-> 2
  xor #3,r0
  mov.b r0,@r11
  mov.b @r13,r0         ; Dyne mode flag
  xor #1,r0
  mov.b r0,@r13
RELOAD:
PORTS0:
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
  mov.b @(2,r13),r0     ; swap the Start bits only on the ship select, or when the P1
  tst r0,r0             ; side is empty and either the P2 side is playing or the game is
  bf STARTS             ; in its play mode (continue). Never on the title or the attract
  mov.l @P1BASE,r2      ; demo (both sides filled there), where the Start press would
  mov.l @r2,r0          ; otherwise start a game on the P2 side.
  tst r0,r0
  bf OUT
  mov.l @P2BASE,r2
  mov.l @r2,r0
  tst r0,r0
  bf STARTS
  mov.l @MODE,r2
  mov.b @r2,r0
  cmp/eq #6,r0
  bf OUT
STARTS:
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
MASK: .long 0x0C239497
P1BASE: .long 0x0C29D1D8
P2BASE: .long 0x0C29D478
P1PORT: .long 0xA4000126
P2PORT: .long 0xA4000134
RET: .long 0x0C060E58
MODE: .long 0x0C2A6D64
