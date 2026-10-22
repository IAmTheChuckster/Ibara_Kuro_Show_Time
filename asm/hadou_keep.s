; Hadou gun (bomb button held): the game spends a bomb through its own copy of the bomb
; code (0x0C0737D0).  Like the normal bomb, with INFINITE nothing is spent: the small-bomb
; check there also goes through bomb_keep.s (bsr at 0x0C0737D0), and the store of the reduced
; full-bomb count (bsr at 0x0C0737DA -> stub 0x0C0737F4 -> here) is skipped.
; r1 = full - 1, r4 = &full bombs; r0 is free.  @ 0x0C05B660
STORE:
  mov.l @SET,r0
  mov.b @r0,r0
  cmp/eq #5,r0          ; INFINITE?
  bt SKIP
  mov.b r1,@r4
SKIP:
  rts
  nop
  .align 4
SET: .long 0x0C23DEA4
