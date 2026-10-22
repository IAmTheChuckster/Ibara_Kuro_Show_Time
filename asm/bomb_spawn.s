; Spawn (game start and every respawn): after the game's normal +1 full bomb,
; full = max(full, setting + 1); FULL / INFINITE: 4 full bombs and 40 fragments.
; Called via bsr at 0x0C06D216 -> stub 0x0C06D3B4.  r2 = &full bombs, r3 = &fragments,
; r9 = new full count, r7 = fragments (the two stores the hook replaced).  @ 0x0C05B680
SPAWN:
  mov.b r9,@r2
  mov.b r7,@r3
  mov.l @SET,r1
  mov.b @r1,r0
  extu.b r0,r0          ; bomb counts setting: 0..3 = 1..4, 4 = FULL, 5 = INFINITE
  mov #4,r1
  cmp/hs r1,r0
  bt FULL
  add #1,r0
  mov.b @r2,r1
  extu.b r1,r1
  cmp/hs r0,r1
  bt DONE
  mov.b r0,@r2
DONE:
  rts
  nop
FULL:
  mov #4,r1
  mov.b r1,@r2
  mov #40,r1
  rts
  mov.b r1,@r3
  .align 4
SET: .long 0x0C23DEA4
