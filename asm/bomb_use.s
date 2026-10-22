; Bomb: store the reduced full-bomb count unless the setting is INFINITE.
; Called via bsr at 0x0C0736B6 -> stub 0x0C073724.  r1 = full - 1, r4 = &full bombs.
; Also redoes the replaced "mov.w #0x2A0,r4".  @ 0x0C05B6C0
USE:
  mov.l @SET,r5
  mov.b @r5,r0
  extu.b r0,r0
  mov #5,r5
  cmp/hs r5,r0
  bt KEEP
  mov.b r1,@r4
KEEP:
  mov.w @SIZE,r4
  rts
  nop
SIZE: .word 0x02A0
  .word 0
SET: .long 0x0C23DEA4
