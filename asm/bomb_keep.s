; Bomb with 40 small bombs: the game spends the small bombs instead of a full bomb.  With
; INFINITE, report 0 small bombs so the (never used up) full bomb is spent instead.
; bsr at 0x0C0736A8 -> stub 0x0C0737B4 -> here; delay slot did "add #2,r3" (r3 = &small bombs);
; returns r0 = small bombs (or 0) for the following "cmp/eq #40,r0".  @ 0x0C05B620
KEEP:
  mov.l r2,@-r15
  mov.l @SET,r2
  mov.b @r2,r2
  extu.b r2,r2
  mov #4,r0
  cmp/hi r0,r2          ; setting > 4 (INFINITE)?
  mov.b @r3,r0
  bf DONE
  mov #0,r0
DONE:
  rts
  mov.l @r15+,r2
  .align 4
SET: .long 0x0C23DEA4
